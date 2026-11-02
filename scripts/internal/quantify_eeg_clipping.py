
"""Quantify EEG saturation plateaus in Sleep-EDF development data."""

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sleepedf import SleepEDFTrack


def find_plateaus(signal, min_samples=10):
    """Return (start, end) pairs; end is exclusive."""
    x = np.asarray(signal)
    repeated = np.diff(x) == 0

    if not repeated.any():
        return []

    edges = np.diff(
        np.concatenate(([False], repeated, [False])).astype(int)
    )
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)

    return [
        (int(start), int(end + 1))
        for start, end in zip(starts, ends)
        if end - start + 1 >= min_samples
    ]


def analyze_recording(rec):
    eeg = np.asarray(rec.epochs["eeg"])
    fs = rec.fs

    # Extrema across the complete loaded recording.
    recording_min = float(np.min(eeg))
    recording_max = float(np.max(eeg))

    rows = []

    for epoch_index, signal in enumerate(eeg):
        plateaus = find_plateaus(signal, min_samples=10)

        positive_samples = 0
        negative_samples = 0
        longest = 0

        for start, end in plateaus:
            value = signal[start]
            length = end - start

            if value == recording_max:
                positive_samples += length
                longest = max(longest, length)

            elif value == recording_min:
                negative_samples += length
                longest = max(longest, length)

        total = positive_samples + negative_samples

        rows.append({
            "subject": rec.group,
            "record": rec.meta["record"],
            "epoch_index": epoch_index,
            "stage": rec.labels[epoch_index],
            "positive_samples": positive_samples,
            "negative_samples": negative_samples,
            "clipped_samples": total,
            "clipped_pct": 100 * total / len(signal),
            "longest_clipping_ms": 1000 * longest / fs,
            "suspected_clipping": int(total > 0),
        })

    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "eeg_clipping_68",
    )
    args = parser.parse_args()

    holdout = {
        f"SC{x:03d}" for x in range(408, 481, 8)
    }

    psgs = sorted(args.cache_dir.rglob("SC*-PSG.edf"))
    psgs = [
        p for p in psgs
        if p.name[:5] not in holdout
    ]

    subjects = {p.name[:5] for p in psgs}

    if len(subjects) != 68 or len(psgs) != 133:
        raise RuntimeError(
            f"Expected 68 subjects / 133 recordings, "
            f"found {len(subjects)} / {len(psgs)}"
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)

    track = SleepEDFTrack()
    output = args.output_dir / "clipping_epochs.csv"

    total_epochs = 0
    flagged_epochs = 0

    with output.open("w", newline="", encoding="utf-8") as f:
        writer = None

        for i, psg in enumerate(psgs, 1):
            recs = track.load(
                str(args.cache_dir),
                psg_paths=[psg],
            )

            if len(recs) != 1:
                raise RuntimeError(f"Cannot load {psg.name}")

            rows = analyze_recording(recs[0])

            if writer is None:
                writer = csv.DictWriter(
                    f, fieldnames=list(rows[0])
                )
                writer.writeheader()

            writer.writerows(rows)

            total_epochs += len(rows)
            flagged_epochs += sum(
                row["suspected_clipping"] for row in rows
            )

            print(
                f"[{i}/{len(psgs)}] {psg.stem}: "
                f"{sum(r['suspected_clipping'] for r in rows)} "
                f"flagged epochs"
            )

    print("\n=== EEG CLIPPING SUMMARY ===")
    print("Total epochs:", total_epochs)
    print("Flagged epochs:", flagged_epochs)
    print(
        "Flagged percentage:",
        round(100 * flagged_epochs / total_epochs, 4),
    )
    print("Saved:", output)


if __name__ == "__main__":
    main()
