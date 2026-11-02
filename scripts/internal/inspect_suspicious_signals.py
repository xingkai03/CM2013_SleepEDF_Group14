
"""Visual inspection of suspicious EEG plateaus in Sleep-EDF."""

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sleepedf import SleepEDFTrack


def longest_plateau(signal):
    """Return start index, end index (exclusive), and plateau length."""
    x = np.asarray(signal)
    repeated = np.diff(x) == 0

    if not repeated.any():
        return None

    edges = np.diff(
        np.concatenate(([False], repeated, [False])).astype(int)
    )
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)

    lengths = ends - starts + 1
    idx = int(np.argmax(lengths))

    return int(starts[idx]), int(ends[idx] + 1), int(lengths[idx])


def plot_epoch(rec, record, epoch_index, output_dir):
    fs = rec.fs
    channels = ("eeg", "eog", "emg")

    eeg = np.asarray(rec.epochs["eeg"][epoch_index])
    plateau = longest_plateau(eeg)

    if plateau is None:
        return

    start, end, length = plateau
    plateau_start_s = start / fs
    plateau_end_s = end / fs

    fig, axes = plt.subplots(
        4, 1, figsize=(15, 11), constrained_layout=True
    )

    for ax, channel in zip(axes[:3], channels):
        signal = np.asarray(rec.epochs[channel][epoch_index])
        time = np.arange(len(signal)) / fs

        # Convert volts to microvolts for readability.
        ax.plot(time, signal * 1e6, linewidth=0.7)
        ax.axvspan(
            plateau_start_s,
            plateau_end_s,
            color="red",
            alpha=0.2,
        )
        ax.set_ylabel(f"{channel.upper()} (µV)")
        ax.grid(alpha=0.2)

    axes[2].set_xlabel("Time within epoch (s)")

    # Zoom around the longest EEG plateau.
    margin = int(round(0.3 * fs))
    left = max(0, start - margin)
    right = min(len(eeg), end + margin)

    time_zoom = np.arange(left, right) / fs

    axes[3].plot(
        time_zoom,
        eeg[left:right] * 1e6,
        marker=".",
        markersize=3,
        linewidth=0.8,
    )
    axes[3].axvspan(
        plateau_start_s,
        plateau_end_s,
        color="red",
        alpha=0.2,
    )
    axes[3].set_title(
        f"EEG plateau zoom: {length} samples "
        f"({1000 * length / fs:.0f} ms)"
    )
    axes[3].set_xlabel("Time within epoch (s)")
    axes[3].set_ylabel("EEG (µV)")
    axes[3].grid(alpha=0.2)

    stage = rec.labels[epoch_index]

    fig.suptitle(
        f"{record} | epoch {epoch_index} | stage {stage}",
        fontsize=14,
    )

    output = output_dir / f"{record}_epoch_{epoch_index}.png"
    fig.savefig(output, dpi=160)
    plt.close(fig)

    print(f"Saved: {output}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument(
        "--audit-csv",
        type=Path,
        default=ROOT / "results" / "multichannel_audit_68"
        / "eeg_long_plateau_epochs.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "multichannel_audit_68"
        / "signal_inspection",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.audit_csv)

    selected_records = [
        "SC4372F0",
        "SC4201E0",
        "SC4592G0",
    ]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    track = SleepEDFTrack()

    for record in selected_records:
        candidates = df[df["record"] == record].copy()

        if candidates.empty:
            print(f"No suspicious epochs for {record}")
            continue

        # Select the three longest plateaus per recording.
        candidates = candidates.sort_values(
            "longest_plateau_samples", ascending=False
        ).head(3)

        psg_path = args.cache_dir / f"{record}-PSG.edf"

        if not psg_path.is_file():
            raise FileNotFoundError(psg_path)

        recs = track.load(
            str(args.cache_dir),
            psg_paths=[psg_path],
        )

        if len(recs) != 1:
            raise RuntimeError(f"Could not load {record}")

        rec = recs[0]

        for _, row in candidates.iterrows():
            epoch_index = int(row["epoch_index"])

            if not 0 <= epoch_index < len(rec.labels):
                raise IndexError(
                    f"Invalid epoch index {epoch_index} for {record}"
                )

            plot_epoch(
                rec,
                record,
                epoch_index,
                args.output_dir,
            )

    print("\nInspection figures generated.")


if __name__ == "__main__":
    main()
