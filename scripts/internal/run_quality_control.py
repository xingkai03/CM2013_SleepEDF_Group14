"""Sleep-EDF P3/P5 quality-control audit; no classifier training or epoch exclusion.

Run from the repository root:
    uv run --locked python scripts/internal/run_quality_control.py --cache-dir "G:\\My Drive\\CM2013\\data_cache\\sleep_edf\\physionet-sleep-data" --n-subjects 5
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sleepedf import SleepEDFTrack  # noqa: E402
from sleepedf.preprocessing import BrokenSegmentHandling, TargetedDenoising  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results" / "quality_control")
    parser.add_argument("--n-subjects", type=int, default=None, help="First N sorted development subjects; omit for all")
    args = parser.parse_args()

    if args.n_subjects is not None and args.n_subjects < 1:
        parser.error("--n-subjects must be positive")
    if not args.cache_dir.is_dir():
        parser.error(f"Cache directory not found: {args.cache_dir}")
    psgs = sorted(args.cache_dir.rglob("SC*-PSG.edf"))
    # Holdout subjects must never be accessed for development QC.
    holdout = {f"SC{x:03d}" for x in range(408, 481, 8)}
    psgs = [p for p in psgs if p.name[:5] not in holdout]
    subjects = sorted({p.name[:5] for p in psgs})
    if args.n_subjects is not None:
        if args.n_subjects > len(subjects):
            parser.error(f"Only {len(subjects)} development subjects found")
        selected = set(subjects[:args.n_subjects])
        psgs = [p for p in psgs if p.name[:5] in selected]
    if not psgs:
        parser.error("No development PSG recordings found")

    track = SleepEDFTrack()
    p3 = BrokenSegmentHandling(action="flag")
    p5 = TargetedDenoising(noise_type="clipping", min_plateau_samples=3)
    rows = []
    total = dict(epochs=0, p3=0, p5=0, both=0, either=0)
    for i, psg in enumerate(psgs, 1):
        recs = track.load(str(args.cache_dir), psg_paths=[psg])
        if len(recs) != 1:
            raise ValueError(f"Expected one recording for {psg}, got {len(recs)}")
        rec = recs[0]
        if rec.meta.get("record") != psg.name.removesuffix("-PSG.edf"):
            raise ValueError(f"Recording mismatch: {psg}")
        # Detect on raw signals; these are quality flags, not labels or transformations.
        broken = np.asarray(p3.detect(rec), dtype=bool)
        clipping = np.asarray(p5.detect(rec), dtype=bool)
        n = len(rec.labels)
        if broken.shape != (n,) or clipping.shape != (n,):
            raise ValueError(f"QC mask/label alignment failure for {psg.name}")
        both = broken & clipping
        either = broken | clipping
        row = {
            "record": rec.meta["record"], "subject": str(rec.group), "n_epochs": n,
            "p3_broken": int(broken.sum()), "p5_suspected_clipping": int(clipping.sum()),
            "both": int(both.sum()), "either": int(either.sum()),
            "p3_indices": np.flatnonzero(broken).tolist(),
            "p5_indices": np.flatnonzero(clipping).tolist(),
            "both_indices": np.flatnonzero(both).tolist(),
        }
        rows.append(row)
        for key, value in (("epochs", n), ("p3", row["p3_broken"]),
                           ("p5", row["p5_suspected_clipping"]),
                           ("both", row["both"]), ("either", row["either"])):
            total[key] += value
        print(f"[{i}/{len(psgs)}] {row['record']}: {n} epochs, P3={row['p3_broken']}, P5={row['p5_suspected_clipping']}", flush=True)
        del rec, recs

    output = args.output_dir.resolve()
    if output.exists():
        parser.error(f"Output directory exists: {output}. Choose a fresh --output-dir")
    output.mkdir(parents=True)
    columns = ["record", "subject", "n_epochs", "p3_broken", "p5_suspected_clipping", "both", "either"]
    with (output / "recordings.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows({k: row[k] for k in columns} for row in rows)
    (output / "flagged_epochs.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": "Sleep-EDF development subjects only",
        "subjects": len({r["subject"] for r in rows}),
        "recordings": len(rows),
        "counts": total,
        "percent_epochs_p3": 100 * total["p3"] / total["epochs"],
        "percent_epochs_p5": 100 * total["p5"] / total["epochs"],
        "percent_epochs_either": 100 * total["either"] / total["epochs"],
        "methods": {
            "p3": {"method": "near_flat_eeg_eog", "action": "flag", "eeg_std_threshold_v": p3.eeg_std_threshold, "eog_std_threshold_v": p3.eog_std_threshold},
            "p5": {"method": "recording_extrema_plateau", "action": "flag_only", "min_plateau_samples": p5.min_plateau_samples, "confirmed_clipping": False},
        },
        "note": "Raw-signal QC flags only. No epoch exclusion, signal reconstruction, feature extraction, or model fitting. P3/P5 are indicators, not validated artifact ground truth.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nSUMMARY:", json.dumps(summary, indent=2))
    print("\nSaved to:", output)


if __name__ == "__main__":
    main()
