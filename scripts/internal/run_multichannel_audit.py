import numpy as np
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sleepedf import SleepEDFTrack

def channel_metrics(epochs):
    x = np.asarray(epochs, dtype=np.float64)

    finite = np.isfinite(x)
    valid = finite.all(axis=1)

    std = np.full(x.shape[0], np.nan)
    ptp = np.full(x.shape[0], np.nan)
    max_step = np.full(x.shape[0], np.nan)

    if valid.any():
        xv = x[valid]
        std[valid] = np.std(xv, axis=1)
        ptp[valid] = np.ptp(xv, axis=1)
        max_step[valid] = np.max(
            np.abs(np.diff(xv, axis=1)), axis=1
        )

    return {
        "finite": valid,
        "std_v": std,
        "ptp_v": ptp,
        "max_step_v": max_step,
    }

def plateau_metrics(epochs, min_samples=3):
    """Detect consecutive identical samples within each epoch."""
    x = np.asarray(epochs, dtype=np.float64)

    n_epochs = x.shape[0]
    longest = np.zeros(n_epochs, dtype=int)

    for i, signal in enumerate(x):
        if not np.all(np.isfinite(signal)):
            continue

        repeated = np.diff(signal) == 0

        if not repeated.any():
            continue

        edges = np.diff(
            np.concatenate(([False], repeated, [False])).astype(int)
        )

        starts = np.flatnonzero(edges == 1)
        ends = np.flatnonzero(edges == -1)

        longest[i] = max(ends - starts) + 1

    return {
        "longest_plateau_samples": longest,
        "plateau_detected": longest >= min_samples,
    }

def main():
    parser = argparse.ArgumentParser(
        description="Multichannel EEG/EOG/EMG audit on Sleep-EDF development data"
    )
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "multichannel_audit_68",
    )
    args = parser.parse_args()

    if not args.cache_dir.is_dir():
        parser.error(f"Cache directory not found: {args.cache_dir}")

    # Same holdout exclusion as run_quality_control.py.
    holdout = {f"SC{x:03d}" for x in range(408, 481, 8)}

    psgs = sorted(args.cache_dir.rglob("SC*-PSG.edf"))
    psgs = [p for p in psgs if p.name[:5] not in holdout]

    subjects = {p.name[:5] for p in psgs}

    print(f"Development subjects: {len(subjects)}")
    print(f"Recordings: {len(psgs)}")

    # Safety checks for the expected full development dataset.
    if len(subjects) != 68 or len(psgs) != 133:
        parser.error(
            f"Expected 68 subjects and 133 recordings; "
            f"found {len(subjects)} subjects and {len(psgs)} recordings."
        )

    if args.output_dir.exists():
        parser.error(f"Output directory already exists: {args.output_dir}")

    args.output_dir.mkdir(parents=True)

    columns = [
        "subject",
        "record",
        "epoch_index",
        "stage",
        "channel",
        "finite",
        "std_v",
        "ptp_v",
        "max_step_v",
        "longest_plateau_samples",
        "plateau_detected",
    ]

    track = SleepEDFTrack()
    total_epochs = 0

    with (args.output_dir / "epoch_metrics.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for i, psg in enumerate(psgs, start=1):
            recs = track.load(str(args.cache_dir), psg_paths=[psg])

            if len(recs) != 1:
                raise ValueError(f"Unexpected number of recordings: {psg}")

            rec = recs[0]
            expected_record = psg.name.removesuffix("-PSG.edf")

            if rec.meta.get("record") != expected_record:
                raise ValueError(f"Recording mismatch: {psg}")

            n_epochs = len(rec.labels)
            total_epochs += n_epochs

            for channel in ("eeg", "eog", "emg"):
                epochs = np.asarray(rec.epochs[channel])

                if epochs.shape[0] != n_epochs:
                    raise ValueError(
                        f"Epoch alignment error: {expected_record}, {channel}"
                    )

                metrics = channel_metrics(epochs)
                plateaus = plateau_metrics(epochs)

                for j in range(n_epochs):
                    writer.writerow({
                        "subject": rec.group,
                        "record": rec.meta["record"],
                        "epoch_index": j,
                        "stage": str(rec.labels[j]),
                        "channel": channel,
                        "finite": bool(metrics["finite"][j]),
                        "std_v": float(metrics["std_v"][j]),
                        "ptp_v": float(metrics["ptp_v"][j]),
                        "max_step_v": float(metrics["max_step_v"][j]),
                        "longest_plateau_samples": int(
                            plateaus["longest_plateau_samples"][j]
                        ),
                        "plateau_detected": bool(
                            plateaus["plateau_detected"][j]
                        ),
                    })

            print(
                f"[{i}/{len(psgs)}] {expected_record}: "
                f"{n_epochs} epochs processed",
                flush=True,
            )

            del rec, recs

    print(f"\nTotal epochs: {total_epochs}")
    print(f"Saved to: {args.output_dir / 'epoch_metrics.csv'}")


if __name__ == "__main__":
    main()