import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import pywt
from scipy.signal import welch
import json
from datetime import datetime

# ---------------------------------------------------------
# Path setup & imports
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Updated imports to pull SleepEDFTrack directly from sleepedf
try:
    from sleepedf import SleepEDFTrack
    from sleepedf.reference.adapter import Recording
except ImportError:
    try:
        from reference.sleep_edf import SleepEDFTrack
        from reference.adapter import Recording
    except ImportError:
        from sleepedf import SleepEDFTrack, Recording

DATA_DIR = Path(r"G:\My Drive\CM2013\data_cache\sleep_edf\physionet-sleep-data")

FEATURE_NAMES = (
    "eeg_rel_delta", "eeg_rel_sigma", "eeg_sef_95", "eeg_zcr",
    "eeg_dwt_d2_energy", "emg_wl", "emg_median_freq",
)
# Recordings to analyse. None = every *PSG.edf file in DATA_DIR.
# To restrict the run, give a list of file prefixes, e.g. ["SC4001", "SC4002"].
SUBJECTS =  None
#SUBJECTS = ["SC4001E0"]
HOLDOUT_SUBJECTS = {
    "SC408", "SC416", "SC424", "SC432", "SC440",
    "SC448", "SC456", "SC464", "SC472", "SC480",
}

PREPROCESSING_CFG = {
    "preprocess": "bandpass",
    "quality_control": True,
}

# ---------------------------------------------------------
# Feature extractor
# ---------------------------------------------------------
@dataclass
class AdvancedSleepFeatures:
    """Extracts 7 additional features per 30 s epoch.

    Input: Preprocessed Recording whose .epochs["eeg"] and .epochs["emg"] are 2D arrays
    of shape (n_epochs, n_samples). Everything is vectorized over epochs.

    Features
    --------
    eeg_rel_delta      relative power 0.5-4 Hz  (within 0.5-30 Hz)
    eeg_rel_sigma      relative power 11-16 Hz  (within 0.5-30 Hz)
    eeg_sef_95         spectral edge frequency (95 % of power, 0.5-30 Hz)
    eeg_zcr            zero-crossing rate of the mean-removed EEG
    eeg_dwt_d2_energy  relative wavelet energy of detail level 2 (~12.5-25 Hz at 100 Hz)
    emg_wl             waveform length (sum of absolute sample-to-sample changes)
    emg_median_freq    median frequency of the EMG spectrum (10-45 Hz)
                       -> skipped automatically if the EMG is a low-rate envelope
    """

    epoch_sec: float = 30.0
    eeg_band: tuple = (0.5, 30.0)       # band used as "total power" for EEG
    delta_band: tuple = (0.5, 4.0)
    sigma_band: tuple = (11.0, 16.0)
    sef_threshold: float = 0.95
    emg_band: tuple = (10.0, 45.0)      # band used for EMG median frequency
    wavelet: str = "db4"
    wavelet_level: int = 2              # D2 level
    min_emg_fs_for_spectrum: float = 50.0
    # Set True if your Recording upsampled a 1 Hz EMG envelope to 100 Hz:
    emg_is_envelope: bool = False
    # Supply the ORIGINAL EDF rate; recording.fs may describe a resampled array.
    emg_native_fs: float | None = None

    # ---------- helpers ----------
    @staticmethod
    def _band_mask(freqs: np.ndarray, lo: float, hi: float, include_hi: bool = False):
        return (freqs >= lo) & ((freqs <= hi) if include_hi else (freqs < hi))

    @staticmethod
    def _psd(x: np.ndarray, fs: float):
        nperseg = int(min(2 * fs, x.shape[-1]))  # 2 s windows -> 0.5 Hz resolution
        return welch(x, fs=fs, window="hann", nperseg=nperseg, axis=-1)

    # ---------- main ----------
    def extract(self, recording: Recording) -> Dict[str, np.ndarray]:
        eeg = np.asarray(recording.epochs["eeg"], dtype=np.float64)
        emg = np.asarray(recording.epochs["emg"], dtype=np.float64)

        if eeg.ndim != 2 or emg.ndim != 2:
            raise ValueError("Expected EEG and EMG as 2D arrays (n_epochs, n_samples).")
        if eeg.shape[0] != emg.shape[0]:
            raise ValueError("EEG and EMG have a different number of epochs.")
        if eeg.shape[1] < 2 or emg.shape[1] < 2:
            raise ValueError("Each epoch needs at least two samples per channel.")
        if not np.isfinite(eeg).all() or not np.isfinite(emg).all():
            raise ValueError("EEG and EMG samples must be finite.")

        n_epochs, n_eeg = eeg.shape
        eeg_fs = float(getattr(recording, "fs", None) or n_eeg / self.epoch_sec)
        emg_fs = eeg_fs if emg.shape[1] == n_eeg else emg.shape[1] / self.epoch_sec
        native_emg_fs = emg_fs if self.emg_native_fs is None else self.emg_native_fs
        if not np.isfinite(eeg_fs) or eeg_fs <= 0 or not np.isfinite(native_emg_fs) or native_emg_fs <= 0:
            raise ValueError("Sampling rates must be finite and positive.")
        skip_emg_spectrum = self.emg_is_envelope or native_emg_fs < self.min_emg_fs_for_spectrum
        if skip_emg_spectrum:
            warnings.warn(
                f"EMG is a low-rate envelope (native/inferred fs={native_emg_fs:.1f} Hz, "
                f"emg_is_envelope={self.emg_is_envelope}); skipping emg_median_freq."
            )
        if n_epochs == 0:
            names = FEATURE_NAMES[:-1] if skip_emg_spectrum else FEATURE_NAMES
            return {name: np.empty(0) for name in names}
        feats: Dict[str, np.ndarray] = {}

        # ---- 1. EEG spectral features (one Welch call) ----
        freqs, psd = self._psd(eeg, eeg_fs)
        band = self._band_mask(freqs, *self.eeg_band, include_hi=True)
        f_b, p_b = freqs[band], psd[:, band]
        total = p_b.sum(axis=-1)

        d = self._band_mask(f_b, *self.delta_band)
        s = self._band_mask(f_b, *self.sigma_band)
        feats["eeg_rel_delta"] = np.divide(p_b[:, d].sum(axis=-1), total,
                                           out=np.zeros(n_epochs), where=total > 0)
        feats["eeg_rel_sigma"] = np.divide(p_b[:, s].sum(axis=-1), total,
                                           out=np.zeros(n_epochs), where=total > 0)

        cum = np.cumsum(p_b, axis=-1)
        edge_idx = np.argmax(cum >= self.sef_threshold * total[:, None], axis=-1)
        feats["eeg_sef_95"] = np.where(total > 0, f_b[edge_idx], 0.0)

        # ---- 2. EEG zero-crossing rate ----
        x = eeg - eeg.mean(axis=-1, keepdims=True)
        # Carry the last nonzero sign through exact zeros, counting each true
        # sign change once even for quantised signals with zero-valued samples.
        signs = np.sign(x)
        indices = np.maximum.accumulate(np.where(signs != 0, np.arange(n_eeg), 0), axis=-1)
        signs = np.take_along_axis(signs, indices, axis=-1)
        crossings = (signs[:, :-1] * signs[:, 1:]) < 0
        feats["eeg_zcr"] = crossings.sum(axis=-1) / (n_eeg - 1)

        # ---- 3. EEG wavelet detail-2 relative energy ----
        coeffs = pywt.wavedec(eeg, self.wavelet, level=self.wavelet_level, axis=-1)
        # coeffs = [cA2, cD2, cD1]
        cD2 = coeffs[-2]
        wav_total = sum(np.sum(c ** 2, axis=-1) for c in coeffs)
        feats["eeg_dwt_d2_energy"] = np.divide(np.sum(cD2 ** 2, axis=-1), wav_total,
                                               out=np.zeros(n_epochs), where=wav_total > 0)

        # ---- 4. EMG waveform length ----
        feats["emg_wl"] = np.sum(np.abs(np.diff(emg, axis=-1)), axis=-1)

        # ---- 5. EMG median frequency (only if EMG is a real wide-band signal) ----
        if not skip_emg_spectrum:
            e_freqs, e_psd = self._psd(emg, emg_fs)
            hi = min(self.emg_band[1], 0.9 * emg_fs / 2)
            eb = self._band_mask(e_freqs, self.emg_band[0], hi, include_hi=True)
            ef_b, ep_b = e_freqs[eb], e_psd[:, eb]
            e_total = ep_b.sum(axis=-1)
            e_cum = np.cumsum(ep_b, axis=-1)
            med_idx = np.argmax(e_cum >= 0.5 * e_total[:, None], axis=-1)
            feats["emg_median_freq"] = np.where(e_total > 0, ef_b[med_idx], 0.0)

        return feats

    @staticmethod
    def to_matrix(feats: Dict[str, np.ndarray], order: List[str] = None) -> np.ndarray:
        """Stack features into (n_epochs, n_features) in a fixed, explicit order."""
        names = order or list(feats.keys())
        return np.column_stack([feats[n] for n in names])


# ---------------------------------------------------------
# Verification helper
# ---------------------------------------------------------
def check_features(rec: Recording, feats: Dict[str, np.ndarray], epoch_idx: int = 100):
    """Sanity checks: shapes, finite values, and a manual recomputation."""
    eeg = np.asarray(rec.epochs["eeg"], dtype=np.float64)
    n_epochs, n_samples = eeg.shape
    fs = n_samples / 30.0

    assert all(v.shape == (n_epochs,) for v in feats.values()), "Wrong feature shape"
    assert all(np.isfinite(v).all() for v in feats.values()), "NaN/Inf in features"

    # Manual recomputation of eeg_rel_delta for one epoch
    f, p = welch(eeg[epoch_idx], fs=fs, window="hann", nperseg=int(2 * fs))
    m = (f >= 0.5) & (f <= 30.0)
    manual = p[m][(f[m] >= 0.5) & (f[m] < 4.0)].sum() / p[m].sum()
    assert np.isclose(manual, feats["eeg_rel_delta"][epoch_idx], rtol=1e-3, atol=1e-4), (
        f"Mismatch: manual={manual:.6f}, extracted={feats['eeg_rel_delta'][epoch_idx]:.6f}"
    )
    print(f"Checks passed (n_epochs={n_epochs}, eeg_fs={fs:.1f} Hz, "
          f"manual rel_delta={manual:.4f}).")


# ---------------------------------------------------------
# Per-recording pipeline
# ---------------------------------------------------------
def process_recording(track, extractor: AdvancedSleepFeatures, psg_path: Path, subject: str) -> pd.DataFrame:
    """Load, preprocess, extract features and return one DataFrame row per epoch."""
    print(f"\n{'=' * 60}\nLoading {psg_path.name}\n{'=' * 60}")

    recordings = track.load(str(DATA_DIR), psg_paths=[psg_path])
    print(f"Loaded {len(recordings)} recording(s).")

    if not recordings:
        raise RuntimeError(
            f"No recording returned for {psg_path.name}"
        )

    raw_rec = recordings[0]
    print("Subject:", raw_rec.group, "| fs:", raw_rec.fs, "| channels:", list(raw_rec.epochs.keys()))
    print("Raw EEG shape:", np.asarray(raw_rec.epochs["eeg"]).shape,
          "| Raw EMG shape:", np.asarray(raw_rec.epochs["emg"]).shape)

    # 1. Configure and run preprocessing (P1 Bandpass + P3/P5 Quality Control)
    cfg = {
        "preprocess": "bandpass",
        "quality_control": True,
    }
    print("\nApplying track.preprocess(rec, cfg)...")
    rec_processed = track.preprocess(raw_rec, cfg=PREPROCESSING_CFG)

    # 2. Inspect Quality Control flag masks (P3 & P5)
    n_labels = len(rec_processed.labels)
    broken_mask = rec_processed.meta.get("broken_epoch_mask", np.zeros(n_labels, dtype=bool))
    clipping_mask = rec_processed.meta.get("suspected_clipping_mask", np.zeros(n_labels, dtype=bool))
    print(f"[QC P3] Broken / flat epochs flagged: {np.sum(broken_mask)} / {len(broken_mask)}")
    print(f"[QC P5] Suspected clipping epochs flagged: {np.sum(clipping_mask)} / {len(clipping_mask)}")

    # 3. Extract features from preprocessed recording
    feats = extractor.extract(rec_processed)
    check_features(rec_processed, feats)

    print("\nFeature Summary:")
    for name, arr in feats.items():
        print(f"  - {name:20s} | Shape: {arr.shape} | Mean: {arr.mean():.4e} | Std: {arr.std():.4e}")

    # Inspect EMG power distribution post-preprocessing
    f, p = welch(np.asarray(rec_processed.epochs["emg"]), fs=rec_processed.fs,
                 nperseg=int(2 * rec_processed.fs), axis=-1)
    total_power = p.sum(axis=-1)

    low_share = np.divide(
        p[:, f < 2].sum(axis=-1),
        total_power,
        out=np.zeros_like(total_power),
        where=total_power > 0
    )
    print(f"\nEMG power below 2 Hz: median {np.median(low_share):.0%}")

    df = pd.DataFrame(feats)
    df["stage"] = np.asarray(rec_processed.labels)
    df["flag_broken"] = broken_mask
    df["flag_clipping"] = clipping_mask
    df["recording"] = subject
    df["subject"] = subject[:5]
    df["epoch"] = np.arange(len(df))

    print(f"\nMean feature value per sleep stage ({subject}):")
    print(df.groupby("stage")[list(feats.keys())].mean())
    return df


# ---------------------------------------------------------
# Execution / test block
# ---------------------------------------------------------
if __name__ == "__main__":
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Data directory not found at: {DATA_DIR}")

    pd.set_option("display.float_format", lambda v: f"{v:.4g}")
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 50)

    track = SleepEDFTrack()
    #extractor = AdvancedSleepFeatures()
    extractor = AdvancedSleepFeatures(
        emg_is_envelope=True,
        emg_native_fs=1.0
    )

    # Collect the PSG files to process
    if SUBJECTS is None:
        psg_files = sorted(DATA_DIR.glob("*PSG.edf"))
    else:
        psg_files = []
        for prefix in SUBJECTS:
            matches = sorted(DATA_DIR.glob(f"{prefix}*PSG.edf"))
            if not matches:
                print(f"\n[WARNING] No PSG file found for {prefix} in {DATA_DIR}, skipping.")
            psg_files.extend(matches)
    psg_files = [
        p for p in psg_files
        if p.name[:5] not in HOLDOUT_SUBJECTS
    ]
    all_psg_files = sorted(DATA_DIR.glob("*PSG.edf"))

    excluded_files = [
        p for p in all_psg_files
        if p.name[:5] in HOLDOUT_SUBJECTS
    ]

    print(f"Total PSG files: {len(all_psg_files)}")
    print(f"Holdout PSG files excluded: {len(excluded_files)}")
    print(f"Development PSG files: {len(psg_files)}")
    print(f"Development subjects: {len({p.name[:5] for p in psg_files})}")

    if SUBJECTS is None:
        assert len(psg_files) + len(excluded_files) == len(all_psg_files)
    assert not any(p.name[:5] in HOLDOUT_SUBJECTS for p in psg_files)

    if not psg_files:
        raise FileNotFoundError(f"No *PSG.edf files found in {DATA_DIR}")
    print(f"Found {len(psg_files)} PSG file(s): {[p.name for p in psg_files]}")

    # Beware of hold-out subjects
    print("Selected recordings:", len(psg_files))

    assert all(
        p.name[:5] not in HOLDOUT_SUBJECTS
        for p in psg_files
    ), "ERROR: Holdout subject detected!"

    frames = []
    for psg_path in psg_files:
        subject = psg_path.name[:6]  # e.g. "SC4001" from "SC4001E0-PSG.edf"
        try:
            frames.append(process_recording(track, extractor, psg_path, subject))
        except Exception as exc:  # keep going if one recording fails
            print(f"\n[ERROR] {psg_path.name} failed: {type(exc).__name__}: {exc}")

    if not frames:
        raise RuntimeError("No recordings could be processed.")

    # Save extracted features to CSV
    if frames:
        combined_df = pd.concat(frames, ignore_index=True)

        output_dir = Path("results")
        output_dir.mkdir(parents=True, exist_ok=True)

        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        csv_path = output_dir / f"sleepedf_features_{run_id}.csv"
        json_path = output_dir / f"sleepedf_features_{run_id}.json"

        # Save features
        combined_df.to_csv(csv_path, index=False)

        # Define feature columns
        non_feature_columns = {
            "stage",
            "subject",
            "recording",
            "epoch",
            "flag_broken",
            "flag_clipping",
        }

        feature_columns = [
            col for col in combined_df.columns
            if col not in non_feature_columns
        ]

        # Run metadata
        metadata = {
            "run_id": run_id,
            "dataset": "Sleep-EDF",
            "split": "development",
            "split_unit": "subject",
            "preprocessing": PREPROCESSING_CFG,
            "n_recordings": int(combined_df["recording"].nunique()),
            "n_subjects": int(combined_df["subject"].nunique()),
            "n_epochs": int(len(combined_df)),
            "n_features": len(feature_columns),
            "features": feature_columns,
            "stage_distribution": {
                str(stage): int(count)
                for stage, count in combined_df["stage"].value_counts().items()
            },
            "quality_control": {
                "broken_epochs_flagged": int(combined_df["flag_broken"].sum()),
                "clipping_epochs_flagged": int(combined_df["flag_clipping"].sum()),
            },
            "output_csv": csv_path.name,
        }

        # Save metadata
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)

        print(f"\nFeatures saved to: {csv_path}")
        print(f"Metadata saved to: {json_path}")
        print(f"Total epochs: {len(combined_df)}")
        print(f"Total recordings: {metadata['n_recordings']}")
        print(f"Total subjects: {metadata['n_subjects']}")
        print(f"Columns: {combined_df.columns.tolist()}")
    # ---------- Combined results across all recordings ----------
    df_all = pd.concat(frames, ignore_index=True)
    feat_cols = [c for c in df_all.columns
             if c not in ("stage", "flag_broken", "flag_clipping",
                          "subject", "recording", "epoch")]

    print(f"\n{'=' * 60}\nCOMBINED RESULTS ({df_all['subject'].nunique()} recordings, "
          f"{len(df_all)} epochs)\n{'=' * 60}")

    print("\nMean feature value per sleep stage (all recordings pooled):")
    print(df_all.groupby("stage")[feat_cols].mean())

    print("\nStd per sleep stage (all recordings pooled):")
    print(df_all.groupby("stage")[feat_cols].std())

    # Does the stage pattern hold in every subject? One block per feature.
    print("\nMean per stage, per subject (rows = stage, columns = subject):")
    for col in feat_cols:
        print(f"\n{col}")
        print(df_all.pivot_table(index="stage", columns="subject", values=col, aggfunc="mean"))
