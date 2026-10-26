import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
import pywt
from scipy.signal import welch

# ---------------------------------------------------------
# Path setup & imports
# ---------------------------------------------------------
# Assumes this script is inside tests/ (project root = parent of that folder)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from reference.adapter import Recording
    from reference.sleep_edf import SleepEDFTrack
except ImportError:
    from sleepedf.reference.adapter import Recording
    from sleepedf.reference.sleep_edf import SleepEDFTrack

DATA_DIR = PROJECT_ROOT / "sleep_edf_data" / "physionet-sleep-data"

EPS = 1e-12


# ---------------------------------------------------------
# Feature extractor
# ---------------------------------------------------------
@dataclass
class AdvancedSleepFeatures:
    """Extracts 7 additional features per 30 s epoch.

    Input: Recording whose .epochs["eeg"] and .epochs["emg"] are 2D arrays
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
    wavelet_level: int = 2              # we only need D2
    min_emg_fs_for_spectrum: float = 50.0
    # Set True if your Recording upsampled a 1 Hz EMG envelope to 100 Hz:
    emg_is_envelope: bool = False

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

        n_epochs, n_eeg = eeg.shape
        eeg_fs = float(getattr(recording, "fs", None) or n_eeg / self.epoch_sec)
        emg_fs = eeg_fs if emg.shape[1] == n_eeg else emg.shape[1] / self.epoch_sec
        feats: Dict[str, np.ndarray] = {}

        # ---- 1. EEG spectral features (one Welch call) ----
        freqs, psd = self._psd(eeg, eeg_fs)
        band = self._band_mask(freqs, *self.eeg_band, include_hi=True)
        f_b, p_b = freqs[band], psd[:, band]
        total = p_b.sum(axis=-1) + EPS

        d = self._band_mask(f_b, *self.delta_band)
        s = self._band_mask(f_b, *self.sigma_band)
        feats["eeg_rel_delta"] = p_b[:, d].sum(axis=-1) / total
        feats["eeg_rel_sigma"] = p_b[:, s].sum(axis=-1) / total

        cum = np.cumsum(p_b, axis=-1)
        edge_idx = np.argmax(cum >= self.sef_threshold * total[:, None], axis=-1)
        feats["eeg_sef_95"] = f_b[edge_idx]

        # ---- 2. EEG zero-crossing rate ----
        x = eeg - eeg.mean(axis=-1, keepdims=True)
        crossings = (x[:, :-1] * x[:, 1:]) < 0
        feats["eeg_zcr"] = crossings.sum(axis=-1) / (n_eeg - 1)

        # ---- 3. EEG wavelet detail-2 relative energy ----
        coeffs = pywt.wavedec(eeg, self.wavelet, level=self.wavelet_level, axis=-1)
        # coeffs = [cA2, cD2, cD1]
        cD2 = coeffs[1]
        wav_total = sum(np.sum(c ** 2, axis=-1) for c in coeffs) + EPS
        feats["eeg_dwt_d2_energy"] = np.sum(cD2 ** 2, axis=-1) / wav_total

        # ---- 4. EMG waveform length ----
        feats["emg_wl"] = np.sum(np.abs(np.diff(emg, axis=-1)), axis=-1)

        # ---- 5. EMG median frequency (only if EMG is a real wide-band signal) ----
        if self.emg_is_envelope or emg_fs < self.min_emg_fs_for_spectrum:
            warnings.warn(
                f"EMG looks like a low-rate envelope (inferred fs={emg_fs:.1f} Hz, "
                f"emg_is_envelope={self.emg_is_envelope}); skipping emg_median_freq."
            )
        else:
            e_freqs, e_psd = self._psd(emg, emg_fs)
            hi = min(self.emg_band[1], 0.9 * emg_fs / 2)
            eb = self._band_mask(e_freqs, self.emg_band[0], hi, include_hi=True)
            ef_b, ep_b = e_freqs[eb], e_psd[:, eb]
            e_total = ep_b.sum(axis=-1) + EPS
            e_cum = np.cumsum(ep_b, axis=-1)
            med_idx = np.argmax(e_cum >= 0.5 * e_total[:, None], axis=-1)
            feats["emg_median_freq"] = ef_b[med_idx]

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
    assert np.isclose(manual, feats["eeg_rel_delta"][epoch_idx], rtol=1e-6), "Mismatch"
    print(f"Checks passed (n_epochs={n_epochs}, eeg_fs={fs:.1f} Hz, "
          f"manual rel_delta={manual:.4f}).")


# ---------------------------------------------------------
# Execution / test block
# ---------------------------------------------------------
if __name__ == "__main__":
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Data directory not found at: {DATA_DIR}")

    psg_path = sorted(DATA_DIR.glob("*PSG.edf"))[0]
    print(f"Loading {psg_path.name}")

    track = SleepEDFTrack()
    recordings = track.load(str(DATA_DIR), psg_paths=[psg_path])
    # If this raises a type error about psg_paths, try psg_paths=[str(psg_path)]
    print(f"Loaded {len(recordings)} recording(s).")

    rec = recordings[0]
    print("Subject:", rec.group, "| fs:", rec.fs, "| channels:", list(rec.epochs.keys()))
    print("EEG:", np.asarray(rec.epochs["eeg"]).shape, "| EMG:", np.asarray(rec.epochs["emg"]).shape)

    extractor = AdvancedSleepFeatures()
    feats = extractor.extract(rec)
    check_features(rec, feats)

    for name, arr in feats.items():
        print(f"  • {name:20s} | Shape: {arr.shape} | Mean: {arr.mean():.4f} | Std: {arr.std():.4f}")

    # Is the EMG a real wide-band signal or an upsampled envelope?
    f, p = welch(np.asarray(rec.epochs["emg"]), fs=rec.fs, nperseg=int(2 * rec.fs), axis=-1)
    low_share = p[:, f < 2].sum(-1) / p.sum(-1)
    print(f"\nEMG power below 2 Hz: median {np.median(low_share):.0%}")

    import pandas as pd
    df = pd.DataFrame(feats)
    df["stage"] = np.asarray(rec.labels)
    print("\nMean feature value per stage:")
    print(df.groupby("stage").mean().round(4))