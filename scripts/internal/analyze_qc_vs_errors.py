"""Compare raw-signal P3/P5 QC flags with P1 out-of-fold errors.

Uses existing checkpoints; no EDF loading or model fitting.
Run from repository root with uv run --locked python scripts/internal/analyze_qc_vs_errors.py ...
"""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def read_json(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_csv(path, rows, columns):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def rate(mask, error):
    n = int(mask.sum())
    wrong = int(np.count_nonzero(error & mask))
    return {"n_epochs": n, "n_errors": wrong,
            "error_rate_percent": 100 * wrong / n if n else None}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--p1-run", type=Path, required=True)
    p.add_argument("--qc-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    if a.output_dir.exists():
        p.error(f"Output already exists: {a.output_dir}")
    provenance = read_json(a.p1_run / "provenance.json")
    manifest = read_json(a.p1_run / "checkpoint_manifest.json")
    qc = read_json(a.qc_dir / "flagged_epochs.json")
    qc_summary = read_json(a.qc_dir / "summary.json")
    records = provenance["recordings"]
    if provenance["config"].get("preprocess") != "bandpass":
        raise ValueError("Expected a P1 bandpass run")
    if provenance.get("cropping") != "none":
        raise ValueError("Cannot align epochs when cropping is active")
    n = sum(int(r["epochs"]) for r in records)
    if n != int(manifest["n_epochs"]) or n != int(qc_summary["counts"]["epochs"]):
        raise ValueError("Epoch counts disagree across provenance, checkpoint manifest and QC")
    if len(records) != len(qc) or len({r["record"] for r in records}) != len(records):
        raise ValueError("Recording lists are missing entries or contain duplicates")
    qc_by_record = {r["record"]: r for r in qc}
    if len(qc_by_record) != len(qc) or set(qc_by_record) != {r["record"] for r in records}:
        raise ValueError("QC and P1 recording IDs differ")
    p3 = np.zeros(n, dtype=bool)
    p5 = np.zeros(n, dtype=bool)
    expected_group = np.empty(n, dtype="U32")
    expected_record = np.empty(n, dtype="U32")
    offset = 0
    for r in records:
        q = qc_by_record[r["record"]]
        count = int(r["epochs"])
        if int(q["n_epochs"]) != count or q["subject"] != r["subject"]:
            raise ValueError(f"QC/P1 count or subject mismatch for {r['record']}")
        expected_group[offset:offset+count] = r["subject"]
        expected_record[offset:offset+count] = r["record"]
        for key, mask, count_key in (("p3_indices", p3, "p3_broken"),
                                     ("p5_indices", p5, "p5_suspected_clipping")):
            local = np.asarray(q[key], dtype=np.int64)
            if np.any((local < 0) | (local >= count)) or len(np.unique(local)) != len(local):
                raise ValueError(f"Invalid {key} in {r['record']}")
            if len(local) != int(q[count_key]):
                raise ValueError(f"QC count mismatch in {r['record']}")
            mask[offset+local] = True
        offset += count
    if (int(p3.sum()) != int(qc_summary["counts"]["p3"]) or
        int(p5.sum()) != int(qc_summary["counts"]["p5"]) or
        int((p3 & p5).sum()) != int(qc_summary["counts"]["both"])):
        raise ValueError("QC reconstructed counts disagree with summary")

    true = np.empty(n, dtype="U16")
    pred = np.empty(n, dtype="U16")
    seen = np.zeros(n, dtype=bool)
    checkpoints = sorted((a.p1_run / "checkpoints").glob("fold_*.npz"))
    if len(checkpoints) != len(manifest["fold_plan"]):
        raise ValueError("Checkpoint count does not match fold plan")
    for file in checkpoints:
        with np.load(file, allow_pickle=False) as d:
            if str(d["signature"].item()) != manifest["signature"]:
                raise ValueError(f"Checkpoint signature mismatch: {file}")
            idx = np.asarray(d["test_indices"], dtype=np.int64)
            yt, yp, groups = d["y_true"], d["y_pred"], d["groups"]
            if not (len(idx) == len(yt) == len(yp) == len(groups)):
                raise ValueError(f"Checkpoint length mismatch: {file}")
            if np.any((idx < 0) | (idx >= n)) or len(np.unique(idx)) != len(idx) or np.any(seen[idx]):
                raise ValueError(f"Invalid or duplicate indices in {file}")
            if not np.array_equal(groups, expected_group[idx]):
                raise ValueError(f"Subject mismatch for {file}")
            fold_number = int(file.stem.split("_")[-1]) - 1
            plan = next((f for f in manifest["fold_plan"] if int(f["fold"]) == fold_number), None)
            if plan is None or set(np.unique(groups)) != set(plan["test_subjects"]):
                raise ValueError(f"Fold subject plan mismatch for {file}")
            seen[idx] = True
            true[idx] = yt
            pred[idx] = yp
    if not seen.all():
        raise ValueError(f"Missing out-of-fold predictions for {int((~seen).sum())} epochs")
    if set(np.unique(true)) - {"W", "N1", "N2", "N3", "REM"}:
        raise ValueError("Unexpected sleep stage label")
    errors = true != pred
    either = p3 | p5
    categories = {
        "all": np.ones(n, dtype=bool),
        "p3_flagged": p3,
        "p5_flagged": p5,
        "both_flagged": p3 & p5,
        "either_flagged": either,
        "unflagged": ~either,
    }
    overall = [{"category": name, **rate(mask, errors)} for name, mask in categories.items()]
    stages = [
        {"stage": stage, "category": name, **rate(mask & (true == stage), errors)}
        for stage in ("W", "N1", "N2", "N3", "REM")
        for name, mask in categories.items()
    ]
    per_record = []
    for r in records:
        mask = expected_record == r["record"]
        row = {"record": r["record"], "subject": r["subject"],
               "n_epochs": int(mask.sum()), "n_errors": int((mask & errors).sum()),
               "p3_flagged": int((mask & p3).sum()), "p5_flagged": int((mask & p5).sum()),
               "either_flagged": int((mask & either).sum()),
               "flagged_errors": int((mask & either & errors).sum())}
        per_record.append(row)
    a.output_dir.mkdir(parents=True)
    save_csv(a.output_dir / "overall.csv", overall,
             ["category", "n_epochs", "n_errors", "error_rate_percent"])
    save_csv(a.output_dir / "by_stage.csv", stages,
             ["stage", "category", "n_epochs", "n_errors", "error_rate_percent"])
    save_csv(a.output_dir / "by_recording.csv", per_record,
             ["record", "subject", "n_epochs", "n_errors", "p3_flagged", "p5_flagged", "either_flagged", "flagged_errors"])
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(),
               "p1_run": str(a.p1_run), "qc_dir": str(a.qc_dir),
               "epochs": n, "oof_predictions_complete": True,
               "checkpoint_signature": manifest["signature"],
               "results": overall,
               "caveat": "Associations only, not causal. QC flags are heuristic and not artifact ground truth. No stage adjustment in overall rates."}
    (a.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Validated {len(checkpoints)} folds, {len(records)} recordings, {n} aligned epochs")
    for row in overall:
        value = row["error_rate_percent"]
        print(f"{row['category']:17s} n={row['n_epochs']:7d} errors={row['n_errors']:7d} rate={value:.3f}%" if value is not None else f"{row['category']:17s} n=0 rate=N/A")
    print(f"Saved to: {a.output_dir.resolve()}")


if __name__ == "__main__":
    main()
