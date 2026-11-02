
"""Exploratory EMG spectral analysis on Sleep-EDF development subjects."""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import welch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sleepedf import SleepEDFTrack


BANDS = {
    "very_low": (0.1, 1.0),
    "low": (1.0, 5.0),
    "mid": (5.0, 15.0),
    "high": (15.0, 40.0),
}


def spectral_features(signal, fs):
    x = np.asarray(signal, dtype=float)
    x = x - np.mean(x)

    freqs, psd = welch(
        x,
        fs=fs,
        nperseg=min(len(x), int(4 * fs)),
    )

    powers = {}

    for name, (low, high) in BANDS.items():
        mask = (freqs >= low) & (freqs < high)

        powers[name] = float(
            np.trapezoid(psd[mask], freqs[mask])
        )

    total = sum(powers.values())

    result = {
        f"{name}_power": value
        for name, value in powers.items()
    }

    for name, value in powers.items():
        result[f"{name}_relative"] = (
            value / total if total > 0 else np.nan
        )

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "emg_spectrum_68",
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

    if len(psgs) != 133 or len({p.name[:5] for p in psgs}) != 68:
        raise RuntimeError("Unexpected development dataset size")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    track = SleepEDFTrack()
    rows = []

    for i, psg in enumerate(psgs, 1):
        recs = track.load(
            str(args.cache_dir),
            psg_paths=[psg],
        )

        if len(recs) != 1:
            raise RuntimeError(f"Cannot load {psg.name}")

        rec = recs[0]
        emg = rec.epochs["emg"]

        # Sample up to 30 epochs per stage per recording.
        for stage in np.unique(rec.labels):
            indices = np.flatnonzero(rec.labels == stage)

            if len(indices) > 30:
                positions = np.linspace(
                    0, len(indices) - 1, 30,
                    dtype=int,
                )
                indices = indices[positions]

            for idx in indices:
                features = spectral_features(
                    emg[idx], rec.fs
                )

                rows.append({
                    "subject": rec.group,
                    "record": rec.meta["record"],
                    "epoch_index": int(idx),
                    "stage": stage,
                    **features,
                })

        print(f"[{i}/{len(psgs)}] {psg.stem}")

    df = pd.DataFrame(rows)

    output = args.output_dir / "emg_spectral_features.csv"
    df.to_csv(output, index=False)

    columns = [
        f"{name}_relative" for name in BANDS
    ]

    print("\n=== EMG RELATIVE POWER BY STAGE ===")
    print(
        df.groupby("stage")[columns]
        .median()
        .to_string()
    )

    print("\nSaved:", output)


if __name__ == "__main__":
    main()
