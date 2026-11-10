"""Compare observed EEG extrema with EDF physical limits.

Development subjects only. No signal modification.
"""

from pathlib import Path
import sys
import csv

import numpy as np
import mne

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sleepedf import SleepEDFTrack

CACHE = Path(
    r"G:\My Drive\CM2013\data_cache\sleep_edf\physionet-sleep-data"
)

OUTPUT = ROOT / "results" / "eeg_clipping_68" / "edf_limits_check.csv"

HOLDOUT = {f"SC{x:03d}" for x in range(408, 481, 8)}


def read_eeg_limits(psg_path):
    """Read EEG physical and digital limits from EDF header."""
    with open(psg_path, "rb") as f:
        header = f.read(256)
        ns = int(header[252:256].decode("ascii").strip())
        channel_header = f.read(ns * 256)

    def field(offset, width):
        start = offset * ns
        return [
            channel_header[start + i * width:start + (i + 1) * width]
            .decode("ascii").strip()
            for i in range(ns)
        ]

    labels = field(0, 16)
    idx = labels.index("EEG Fpz-Cz")

    return {
        "physical_min": float(field(104, 8)[idx]),
        "physical_max": float(field(112, 8)[idx]),
        "digital_min": int(field(120, 8)[idx]),
        "digital_max": int(field(128, 8)[idx]),
    }


def main():
    psgs = sorted(CACHE.rglob("SC*-PSG.edf"))
    psgs = [p for p in psgs if p.name[:5] not in HOLDOUT]

    subjects = {p.name[:5] for p in psgs}

    if len(subjects) != 68 or len(psgs) != 133:
        raise RuntimeError(
            f"Expected 68 subjects / 133 recordings; "
            f"found {len(subjects)} / {len(psgs)}"
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    track = SleepEDFTrack()
    rows = []

    for i, psg in enumerate(psgs, start=1):
        record = psg.name.replace("-PSG.edf", "")

        limits = read_eeg_limits(psg)

        rec = track.load(
            str(CACHE),
            psg_paths=[psg],
        )[0]

        eeg = np.asarray(rec.epochs["eeg"])

        observed_min = float(eeg.min() * 1e6)
        observed_max = float(eeg.max() * 1e6)

        # Allow only a very small floating-point conversion tolerance.
        atol = 1e-5

        min_matches = bool(np.isclose(
            observed_min, limits["physical_min"],
            atol=atol, rtol=0,
        ))
        max_matches = bool(np.isclose(
            observed_max, limits["physical_max"],
            atol=atol, rtol=0,
        ))

        rows.append({
            "record": record,
            "subject": rec.group,
            **limits,
            "observed_min_uv": observed_min,
            "observed_max_uv": observed_max,
            "min_matches": min_matches,
            "max_matches": max_matches,
            "samples_at_observed_min": int(
                np.count_nonzero(eeg == eeg.min())
            ),
            "samples_at_observed_max": int(
                np.count_nonzero(eeg == eeg.max())
            ),
        })

        print(
            f"[{i}/{len(psgs)}] {record}: "
            f"min={min_matches}, max={max_matches}",
            flush=True,
        )

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved: {OUTPUT}")
    print(f"Records reaching physical min: {sum(r['min_matches'] for r in rows)}")
    print(f"Records reaching physical max: {sum(r['max_matches'] for r in rows)}")
    print(
        "Records reaching both limits:",
        sum(r["min_matches"] and r["max_matches"] for r in rows),
    )


if __name__ == "__main__":
    main()