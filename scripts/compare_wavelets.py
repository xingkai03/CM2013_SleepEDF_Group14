
"""Compare wavelet families for P2 sleep-spindle preservation.

CM2013 - Sleep-EDF - Group 14

Wavelets: db4, sym4, coif1, coif3.
Same EEG recording, N2 epochs, thresholding and detection method.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import sys

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR / "internal"))

import _bootstrap  # Make src/ importable

import detect_spindle_candidates as detector
import evaluate_spindle_redetection as redetection

from sleepedf.preprocessing.experiments import WaveletDenoising


# ============================================================
# 1. CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = ROOT / "results" / "wavelet_comparison"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WAVELETS = ["db4", "sym4", "coif1", "coif3"]

EPOCH_INDICES = detector.EPOCH_INDICES

THRESHOLD_MODE = "soft"
DECOMPOSITION_LEVEL = None

IOU_THRESHOLD = redetection.IOU_THRESHOLD


# ============================================================
# 2. APPLY WAVELET DENOISING
# ============================================================

def apply_wavelets(recording):
    """Apply the same P2 denoising method with different wavelets."""

    processed_recordings = {}

    for wavelet_name in WAVELETS:

        print(f"Applying wavelet: {wavelet_name}")

        pipeline = WaveletDenoising(
            wavelet=wavelet_name,
            level=DECOMPOSITION_LEVEL,
            threshold_mode=THRESHOLD_MODE,
        )

        processed_recordings[wavelet_name] = (
            pipeline.transform(recording)
        )

    return processed_recordings


# ============================================================
# 3. EVALUATE SPINDLE PRESERVATION
# ============================================================

def evaluate_preservation(recording_raw, processed_recordings):
    """Evaluate wavelet preservation on raw-defined spindle candidates."""

    fs = float(recording_raw.fs)
    rows = []

    for epoch_idx in EPOCH_INDICES:

        raw_signal = np.asarray(
            recording_raw.epochs["eeg"][epoch_idx],
            dtype=float
        )

        # Reference spindle candidates: detected from Raw EEG only
        _, raw_envelope = detector.spindle_band_analysis(
            raw_signal, fs
        )

        candidates, _ = detector.detect_candidates(
            raw_envelope, fs
        )

        print(
            f"\nEpoch {epoch_idx}: "
            f"{len(candidates)} raw spindle candidates"
        )

        for wavelet_name, recording in processed_recordings.items():

            processed_signal = np.asarray(
                recording.epochs["eeg"][epoch_idx],
                dtype=float
            )

            _, processed_envelope = detector.spindle_band_analysis(
                processed_signal, fs
            )

            for candidate_id, candidate in enumerate(
                candidates, start=1
            ):

                start = candidate["start_idx"]
                end = candidate["end_idx"]

                # 1. Hilbert envelope retention
                raw_mean_envelope = np.mean(
                    raw_envelope[start:end]
                )

                processed_mean_envelope = np.mean(
                    processed_envelope[start:end]
                )

                envelope_retention = (
                    100 * processed_mean_envelope / raw_mean_envelope
                    if raw_mean_envelope > 0 else np.nan
                )

                # 2. Sigma-band power retention
                # Same 2-s Welch window as previous evaluation
                raw_spectral = detector.spectral_specificity(
                    raw_signal, fs, start, end
                )

                processed_spectral = detector.spectral_specificity(
                    processed_signal, fs, start, end
                )

                raw_sigma = raw_spectral["sigma_power_uv2"]
                processed_sigma = processed_spectral["sigma_power_uv2"]

                sigma_retention = (
                    100 * processed_sigma / raw_sigma
                    if raw_sigma > 0 else np.nan
                )

                rows.append({
                    "epoch": epoch_idx,
                    "candidate_id": candidate_id,
                    "wavelet": wavelet_name,
                    "sigma_power_retention_pct": sigma_retention,
                    "envelope_retention_pct": envelope_retention,
                    "raw_sigma_power_uv2": raw_sigma,
                    "processed_sigma_power_uv2": processed_sigma,
                })

    return pd.DataFrame(rows)


# ============================================================
# 4. SAVE AND SUMMARIZE RESULTS
# ============================================================

def summarize_preservation(df):

    # Save candidate-level results
    df.to_csv(
        OUTPUT_DIR / "wavelet_preservation_candidates.csv",
        index=False
    )

    summary = (
        df.groupby("wavelet", sort=False)
        .agg(
            n_candidates=("candidate_id", "size"),
            sigma_mean_pct=("sigma_power_retention_pct", "mean"),
            sigma_std_pct=("sigma_power_retention_pct", "std"),
            envelope_mean_pct=("envelope_retention_pct", "mean"),
            envelope_std_pct=("envelope_retention_pct", "std"),
        )
        .reset_index()
    )

    summary.to_csv(
        OUTPUT_DIR / "wavelet_preservation_summary.csv",
        index=False
    )

    print("\n" + "=" * 65)
    print("WAVELET PRESERVATION SUMMARY")
    print("=" * 65)

    print(summary.round(2).to_string(index=False))

    print("\nResults saved in:", OUTPUT_DIR)

    return summary


# ============================================================
# 5. EVALUATE SPINDLE RE-DETECTION
# ============================================================

def evaluate_redetection(recording_raw, processed_recordings):
    """Compare independently detected candidates against Raw EEG."""

    fs = float(recording_raw.fs)

    event_rows = []
    summary_rows = []

    for epoch_idx in EPOCH_INDICES:

        raw_signal = np.asarray(
            recording_raw.epochs["eeg"][epoch_idx],
            dtype=float
        )

        # Detect reference candidates from Raw EEG
        _, raw_envelope = detector.spindle_band_analysis(
            raw_signal, fs
        )

        raw_candidates, _ = detector.detect_candidates(
            raw_envelope, fs
        )

        print(f"\nEpoch {epoch_idx}")
        print(f"Raw candidates: {len(raw_candidates)}")

        for wavelet_name, recording in processed_recordings.items():

            processed_signal = np.asarray(
                recording.epochs["eeg"][epoch_idx],
                dtype=float
            )

            # Independent detection after preprocessing
            _, processed_envelope = detector.spindle_band_analysis(
                processed_signal, fs
            )

            processed_candidates, _ = detector.detect_candidates(
                processed_envelope, fs
            )

            # Same one-to-one temporal matching as previous analysis
            matches, missed, new = redetection.match_candidates(
                raw_candidates,
                processed_candidates
            )

            matched_by_ref = {
                i: (j, iou)
                for i, j, iou in matches
            }

            # Candidate-level results
            for i, raw_candidate in enumerate(raw_candidates):

                match = matched_by_ref.get(i)

                if match is None:
                    matched_id = np.nan
                    temporal_iou = np.nan
                    redetected = 0
                else:
                    j, temporal_iou = match
                    matched_id = j + 1
                    redetected = 1

                event_rows.append({
                    "epoch": epoch_idx,
                    "wavelet": wavelet_name,
                    "raw_candidate_id": i + 1,
                    "raw_start_s": raw_candidate["start_s"],
                    "raw_end_s": raw_candidate["end_s"],
                    "redetected": redetected,
                    "matched_candidate_id": matched_id,
                    "temporal_iou": temporal_iou,
                })

            # Epoch-level summary
            n_raw = len(raw_candidates)
            n_matched = len(matches)

            summary_rows.append({
                "epoch": epoch_idx,
                "wavelet": wavelet_name,
                "n_raw": n_raw,
                "n_detected": len(processed_candidates),
                "n_matched": n_matched,
                "n_missed": len(missed),
                "n_unmatched_processed": len(new),
                "redetection_rate_pct": (
                    100 * n_matched / n_raw
                    if n_raw > 0 else np.nan
                ),
                "mean_matched_iou": (
                    np.mean([m[2] for m in matches])
                    if matches else np.nan
                ),
            })

            print(
                f"  {wavelet_name}: "
                f"{n_matched}/{n_raw} matched, "
                f"{len(missed)} missed, "
                f"{len(new)} unmatched processed"
            )

    return (
        pd.DataFrame(event_rows),
        pd.DataFrame(summary_rows)
    )


# ============================================================
# 6. SAVE AND SUMMARIZE RE-DETECTION
# ============================================================

def summarize_redetection(events_df, summary_df):

    events_df.to_csv(
        OUTPUT_DIR / "wavelet_redetection_events.csv",
        index=False
    )

    summary_df.to_csv(
        OUTPUT_DIR / "wavelet_redetection_by_epoch.csv",
        index=False
    )

    # Aggregate counts across the two N2 epochs
    overall = (
        summary_df.groupby("wavelet", sort=False)
        .agg(
            n_raw=("n_raw", "sum"),
            n_detected=("n_detected", "sum"),
            n_matched=("n_matched", "sum"),
            n_missed=("n_missed", "sum"),
            n_unmatched_processed=("n_unmatched_processed", "sum"),
        )
        .reset_index()
    )

    overall["redetection_rate_pct"] = (
        100 * overall["n_matched"] / overall["n_raw"]
    )

    # Calculate mean IoU across matched events
    mean_iou = (
        events_df.groupby("wavelet", sort=False)["temporal_iou"]
        .mean()
        .rename("mean_matched_iou")
        .reset_index()
    )

    overall = overall.merge(
        mean_iou,
        on="wavelet",
        how="left"
    )

    overall.to_csv(
        OUTPUT_DIR / "wavelet_redetection_summary.csv",
        index=False
    )

    print("\n" + "=" * 75)
    print("WAVELET RE-DETECTION SUMMARY")
    print("=" * 75)

    print(overall.round(3).to_string(index=False))

    return overall


def main():

    print("=" * 60)
    print("CM2013 - WAVELET COMPARISON")
    print("=" * 60)

    # Load the same SC400 recording as previous experiments
    recording_raw = detector.load_recording()

    print(f"Recording loaded: {recording_raw.group}")
    print(f"Sampling frequency: {recording_raw.fs} Hz")

    # Apply the four wavelet configurations
    processed_recordings = apply_wavelets(recording_raw)

    # Check the selected N2 epochs
    for epoch_idx in EPOCH_INDICES:

        print(f"\nEpoch {epoch_idx}")

        if recording_raw.labels[epoch_idx] != "N2":
            raise ValueError(
                f"Epoch {epoch_idx} is not labelled N2."
            )

        raw_signal = recording_raw.epochs["eeg"][epoch_idx]

        print(f"  Raw samples: {len(raw_signal)}")

        for wavelet_name, recording in processed_recordings.items():

            processed_signal = recording.epochs["eeg"][epoch_idx]

            print(
                f"  {wavelet_name}: "
                f"{len(processed_signal)} samples"
            )

            if len(processed_signal) != len(raw_signal):
                raise ValueError(
                    f"Signal length mismatch for {wavelet_name}"
                )

    print("\nWavelet preprocessing completed successfully.")
    # Evaluate spindle preservation
    preservation_df = evaluate_preservation(
        recording_raw,
        processed_recordings
    )

    # Save and summarize results
    summarize_preservation(preservation_df)
    # Evaluate independent spindle re-detection
    redetection_events, redetection_by_epoch = evaluate_redetection(
        recording_raw,
        processed_recordings
    )

    summarize_redetection(
        redetection_events,
        redetection_by_epoch
    )

if __name__ == "__main__":
    main()
