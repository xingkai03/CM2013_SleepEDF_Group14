
"""Compare P2 mother wavelets using the existing Sleep-EDF LOSO protocol.

CM2013 - Sleep-EDF - Group 14

Compare db4, sym4, coif1 and coif3 using:
- Same three subjects and six nights
- Same 11 features
- Same Random Forest classifier
- Same LOSO evaluation
"""

from pathlib import Path
import json

import numpy as np
import pandas as pd

import internal._bootstrap

from internal import run_baseline as baseline_runner

from sleepedf import SleepEDFTrack
from sleepedf.machine_learning import make_model, evaluate_loso
from sleepedf.reference.adapter import TrackAdapter


# ============================================================
# EXPERIMENT CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

CACHE_DIR = ROOT / "sleep_edf_data"

OUTPUT_DIR = ROOT / "results" / "wavelet_comparison" / "loso"

WAVELETS = ["db4", "sym4", "coif1", "coif3"]

SUBJECTS = [0, 1, 2]
NIGHTS = [1, 2]

MODEL_NAME = "random_forest"
SEED = 0

BASE_CONFIG = {
    "seed": SEED,
    "preprocess": "wavelet",
    "spectral_method": "welch",
    "select": "none",
    "loso_max_groups": len(SUBJECTS),
}


# ============================================================
# CUSTOM TRACK FOR WAVELET COMPARISON
# ============================================================

from sleepedf.preprocessing.experiments import WaveletDenoising


class WaveletComparisonTrack(SleepEDFTrack):
    """SleepEDFTrack with configurable P2 mother wavelet."""

    def preprocess(self, rec, cfg=None):

        cfg = self._cfg(cfg)

        if cfg["preprocess"] == "wavelet":

            denoiser = WaveletDenoising(
                wavelet=cfg.get("wavelet", "db4"),
                level=None,
                threshold_mode="soft",
            )

            return denoiser.transform(rec)

        return super().preprocess(rec, cfg)


# ============================================================
# LOAD THE LOSO COHORT
# ============================================================

def load_loso_recordings():
    """Load the same subjects and nights as the original LOSO experiment."""

    # Find locally cached PSG recordings
    psgs = sorted(CACHE_DIR.rglob("*-PSG.edf"))

    if not psgs:
        raise FileNotFoundError(
            f"No PSG recordings found in {CACHE_DIR}"
        )

    # Reuse the original cohort-selection function
    selected_psgs = baseline_runner.select_psgs(
        psgs,
        subjects=SUBJECTS,
        nights=NIGHTS,
    )

    print(f"Selected {len(selected_psgs)} PSG recordings")

    # Load EEG and corresponding hypnograms
    track = WaveletComparisonTrack()
    # Enable the wavelet configuration key for this experiment
    track.declare_cfg_keys("wavelet")
    if type(track).features is not TrackAdapter.features:
        raise RuntimeError(
            "Legacy features() override detected: "
            "preprocessing path must be checked."
        )

    recordings = track.load(
        str(CACHE_DIR),
        psg_paths=selected_psgs,
    )

    # Verify that every selected recording was loaded
    expected = {
        psg.name.removesuffix("-PSG.edf")
        for psg in selected_psgs
    }

    loaded = {
        rec.meta["record"]
        for rec in recordings
    }

    if loaded != expected or len(recordings) != len(selected_psgs):
        raise ValueError(
            "Loaded recordings do not match the selected cohort."
        )

    # Display and verify the cohort
    total_epochs = 0

    for rec in recordings:

        n_epochs = len(rec.labels)
        total_epochs += n_epochs

        print(
            f"  {rec.meta['record']}: "
            f"subject={rec.group}, "
            f"epochs={n_epochs}"
        )

        if rec.fs != 100:
            raise ValueError("Unexpected sampling frequency.")

        if any(
            signal.shape != (n_epochs, 3000)
            for signal in rec.epochs.values()
        ):
            raise ValueError(
                f"Unexpected epoch shape: {rec.meta['record']}"
            )

    unique_subjects = sorted({
        rec.group for rec in recordings
    })

    if len(recordings) != 6:
        raise ValueError(
            f"Expected 6 recordings, got {len(recordings)}"
        )

    if len(unique_subjects) != 3:
        raise ValueError(
            f"Expected 3 subjects, got {len(unique_subjects)}"
        )

    print(f"\nTotal epochs: {total_epochs}")
    print(f"LOSO subjects: {unique_subjects}")

    return track, recordings


# ============================================================
# EXTRACT FEATURES FOR EACH WAVELET
# ============================================================

def extract_wavelet_features(track, recordings, wavelet_name):
    """Extract the same 11 features using a selected P2 wavelet."""

    cfg = BASE_CONFIG.copy()
    cfg["wavelet"] = wavelet_name

    print(f"\nExtracting features for {wavelet_name}...")

    X, y, groups = track.build_dataset(
        recordings,
        cfg
    )

    # Validate feature dimensions
    if X.shape != (len(y), 11):
        raise ValueError(
            f"Unexpected feature shape for {wavelet_name}: {X.shape}"
        )

    if len(groups) != len(y):
        raise ValueError("Feature/subject alignment mismatch.")

    if not np.isfinite(X).all():
        raise ValueError(
            f"Non-finite features detected for {wavelet_name}"
        )

    if len(y) != 16688:
        raise ValueError(
            f"Unexpected epoch count for {wavelet_name}: {len(y)}"
        )

    print(f"  Feature matrix: {X.shape}")
    print(f"  Labels: {len(y)}")
    print(f"  Subjects: {len(np.unique(groups))}")

    return X, y, groups, cfg


# ============================================================
# VERIFY ORIGINAL P2 BASELINE
# ============================================================

def verify_db4_baseline(recordings, custom_X, custom_y, custom_groups):

    print("\nVerifying db4 against the original P2 pipeline...")

    original_track = SleepEDFTrack()

    original_cfg = BASE_CONFIG.copy()

    X_original, y_original, groups_original = (
        original_track.build_dataset(
            recordings,
            original_cfg
        )
    )

    if not np.array_equal(y_original, custom_y):
        raise ValueError("db4 labels differ from original P2.")

    if not np.array_equal(groups_original, custom_groups):
        raise ValueError("db4 groups differ from original P2.")

    if not np.array_equal(X_original, custom_X):
        max_diff = np.max(np.abs(X_original - custom_X))

        raise ValueError(
            f"Custom db4 differs from original P2: {max_diff}"
        )

    print("  Custom db4 exactly reproduces original P2.")


# ============================================================
# LOSO CLASSIFICATION
# ============================================================

def evaluate_wavelet_loso(track, X, y, groups, cfg, wavelet_name):
    """Evaluate one wavelet with the existing LOSO protocol."""

    print(f"\nRunning LOSO classification for {wavelet_name}...")

    # Create a fresh classifier for this wavelet
    clf = make_model(
        MODEL_NAME,
        seed=SEED
    )

    # Reuse the project's LOSO evaluation function
    report = evaluate_loso(
        track,
        X,
        y,
        groups,
        clf=clf,
        cfg=cfg
    )

    print(f"  LOSO completed for {wavelet_name}")

    return report

def to_json_compatible(obj):
    """Convert NumPy objects to JSON-compatible values."""

    if isinstance(obj, np.ndarray):
        return obj.tolist()

    if isinstance(obj, np.integer):
        return int(obj)

    if isinstance(obj, np.floating):
        return float(obj)

    if isinstance(obj, np.bool_):
        return bool(obj)

    if isinstance(obj, dict):
        return {
            str(key): to_json_compatible(value)
            for key, value in obj.items()
        }

    if isinstance(obj, (list, tuple)):
        return [to_json_compatible(value) for value in obj]

    return obj

# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("CM2013 - WAVELET LOSO COMPARISON")
    print("=" * 60)

    # 1. Load the six recordings (three subjects, two nights each)
    track, recordings = load_loso_recordings()

    print("\nCohort loading completed successfully.")

    # 2. Store the db4 results as reference
    reference_X = None
    reference_y = None
    reference_groups = None
    summary_rows = []
    all_reports = {}

    # 3. Extract features for each wavelet
    for wavelet_name in WAVELETS:

        X, y, groups, cfg = extract_wavelet_features(
            track,
            recordings,
            wavelet_name
        )

        # 4. Check that labels and LOSO groups remain identical
        if reference_y is None:

            reference_X = X.copy()
            reference_y = y.copy()
            reference_groups = groups.copy()
            verify_db4_baseline(
                recordings,
                reference_X,
                reference_y,
                reference_groups
            )

        else:

            if not np.array_equal(y, reference_y):
                raise ValueError(
                    f"Labels differ for {wavelet_name}"
                )

            if not np.array_equal(groups, reference_groups):
                raise ValueError(
                    f"LOSO groups differ for {wavelet_name}"
                )

            # 5. Compare features with the db4 reference
            max_difference = np.max(
                np.abs(X - reference_X)
            )

            print(
                f"  Maximum feature difference vs db4: "
                f"{max_difference:.6g}"
            )

            if max_difference == 0:
                raise ValueError(
                    f"{wavelet_name} produced identical features to db4."
                )

        print(f"  {wavelet_name}: validation OK")
        report = evaluate_wavelet_loso(
            track,
            X,
            y,
            groups,
            cfg,
            wavelet_name
        )
        summary_rows.append({
            "wavelet": wavelet_name,
            "accuracy": report["accuracy"],
            "cohens_kappa": report["cohens_kappa"],
            "macro_f1": report["macro_f1"],
            "balanced_accuracy": report["balanced_accuracy"],
        })

        all_reports[wavelet_name] = report

        print(
            f"  Kappa: {report['cohens_kappa']:.4f} | "
            f"Macro-F1: {report['macro_f1']:.4f} | "
            f"Balanced accuracy: {report['balanced_accuracy']:.4f}"
        )
        print("  Report keys:", list(report.keys()))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary_df = pd.DataFrame(summary_rows)
    summary_path = OUTPUT_DIR / "wavelet_loso_summary.csv"
    summary_df.to_csv(summary_path, index=False)

    print("\nLOSO SUMMARY")
    print(summary_df.to_string(index=False))

    print(f"\nSummary saved to: {summary_path}")
    print("\nAll wavelet feature matrices validated.")
    reports_path = OUTPUT_DIR / "wavelet_loso_reports.json"

    with open(reports_path, "w", encoding="utf-8") as f:
        json.dump(
            to_json_compatible(all_reports),
            f,
            indent=2
        )

    print(f"Full reports saved to: {reports_path}")


if __name__ == "__main__":
    main()
