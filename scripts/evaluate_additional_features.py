"""Check experimental features on real EDFs and compare paired subject-wise LOSO.

Defaults: subjects 0/1/2, both nights, P1, 200-tree balanced random forest.
The experimental extractor remains outside the production pipeline.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import importlib.util
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import warnings

import internal._bootstrap
from internal import run_baseline as runner

import mne
import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score, cohen_kappa_score, f1_score

from sleepedf import SleepEDFTrack
from sleepedf.feature_extraction import BaselineFeatureExtractor
from sleepedf.machine_learning import default_baseline, evaluate_loso

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("experimental_extra_features", ROOT / "tests/test_features2.py")
prototype = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prototype
spec.loader.exec_module(prototype)
METRICS = ("cohens_kappa", "macro_f1", "balanced_accuracy", "accuracy")


def write_json(path, value):
    path.write_text(json.dumps(runner.json_ready(value), indent=2, allow_nan=False) + "\n")


def write_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def precise_metrics(y, pred):
    return {
        "cohens_kappa": float(cohen_kappa_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, average="macro", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "accuracy": float(accuracy_score(y, pred)),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "sleep_edf_data")
    parser.add_argument("--subjects", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--nights", type=int, nargs="+", choices=[1, 2], default=[1, 2])
    parser.add_argument("--preprocess", choices=["none", "bandpass"], default="bandpass")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.output_dir.resolve()
    if (output / "provenance.json").exists():
        parser.error("Choose a new output directory; prior runs are never overwritten.")
    forbidden = set(args.subjects) & set(range(8, 81, 8))
    if forbidden:
        parser.error(f"Holdout subjects cannot be used: {sorted(forbidden)}")
    track = SleepEDFTrack()
    psgs = runner.select_psgs(args.cache_dir.rglob("*-PSG.edf"),
                              subjects=args.subjects, nights=args.nights)
    if {p.name[:5] for p in psgs} & set(track.meta.holdout_ids):
        parser.error("Selection includes an instructor holdout subject.")
    output.mkdir(parents=True, exist_ok=True)
    cfg = {"seed": 0, "preprocess": args.preprocess, "spectral_method": "welch", "select": "none"}
    started = datetime.now(timezone.utc).isoformat()
    manifest, records, base_parts, extra_parts, ys, gs, ids = [], [], [], [], [], [], []
    extra_names = None
    for i, psg in enumerate(psgs, 1):
        print(f"[{i}/{len(psgs)}] Loading {psg.name}", flush=True)
        hypnograms = sorted(psg.parent.glob(f"{psg.name[:6]}*Hypnogram.edf"))
        if len(hypnograms) != 1:
            raise ValueError(f"Expected one hypnogram for {psg.name}")
        for path in [psg, hypnograms[0]]:
            manifest.append({"path": str(path.resolve()), "sha256": runner.sha256(path)})
        # Reading only EMG prevents the EEG rate from concealing its native rate.
        with mne.io.read_raw_edf(psg, include=["EMG submental"], preload=False, verbose="ERROR") as native:
            native_emg_fs = float(native.info["sfreq"])
        loaded = track.load(str(args.cache_dir), psg_paths=[psg])
        if len(loaded) != 1 or loaded[0].meta["record"] != psg.name.removesuffix("-PSG.edf"):
            raise ValueError(f"Loader did not return exactly {psg.name}")
        rec = track.preprocess(loaded[0], cfg)
        base, y, group = BaselineFeatureExtractor().transform(rec, cfg)
        extractor = prototype.AdvancedSleepFeatures(emg_native_fs=native_emg_fs)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            features = extractor.extract(rec)
        if extra_names is None:
            extra_names = list(features)
        if list(features) != extra_names:
            raise ValueError("Recordings have different eligible feature sets")
        extra = extractor.to_matrix(features, extra_names)
        if base.shape != (len(y), 11) or extra.shape != (len(y), len(extra_names)):
            raise ValueError("Feature/label shape mismatch")
        if not np.isfinite(base).all() or not np.isfinite(extra).all():
            raise ValueError("Non-finite features")
        for name in ("eeg_rel_delta", "eeg_rel_sigma", "eeg_dwt_d2_energy"):
            if np.any(features[name] < 0) or np.any(features[name] > 1 + 1e-12):
                raise ValueError(f"Invalid relative feature: {name}")
        records.append({"record": rec.meta["record"], "subject": group, "epochs": len(y),
                        "native_emg_fs": native_emg_fs, "array_fs": rec.fs,
                        "warnings": [str(w.message) for w in caught]})
        base_parts.append(base)
        extra_parts.append(extra)
        ys.append(y)
        gs.append(np.repeat(group, len(y)))
        ids.append(np.repeat(rec.meta["record"], len(y)))
        print(f"  {len(y)} epochs; native EMG={native_emg_fs:g} Hz; {extra.shape[1]} eligible extra features", flush=True)
        del loaded, rec

    base, extra = np.vstack(base_parts), np.vstack(extra_parts)
    y, groups, recording_ids = np.concatenate(ys), np.concatenate(gs), np.concatenate(ids)
    del base_parts, extra_parts
    provenance = {
        "started_utc": started, "selection": {"subjects": args.subjects, "nights": args.nights},
        "config": cfg, "cropping": "none", "records": records, "input_files": manifest,
        "baseline_features": track.feature_names(), "eligible_extra_features": extra_names,
        "excluded_feature": "emg_median_freq: original EMG sampling rate below 50 Hz" if "emg_median_freq" not in extra_names else None,
        "epochs": len(y), "subjects": sorted(set(groups)), "validation": "paired leave-one-subject-out; both nights stay together",
        "classifier": {"trees": 200, "class_weight": "balanced", "seed": 0, "n_jobs": min(4, os.cpu_count() or 1)},
        "packages": {p: version(p) for p in ("numpy", "scipy", "PyWavelets", "mne", "scikit-learn")},
        "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": {str(p.relative_to(ROOT)): runner.sha256(p) for p in
                          sorted(list((ROOT / "src").rglob("*.py")) +
                                 [Path(__file__), ROOT / "tests/test_features2.py", ROOT / "tests/test_additional_features.py"])},
        "limitations": "Exploratory three-subject comparison by default; no tuning or final holdout scoring. Individual additions are not independent causal estimates.",
    }
    write_json(output / "provenance.json", provenance)
    np.savez_compressed(output / "feature_matrices.npz", baseline=base, additional=extra,
                        y=y, groups=groups, records=recording_ids, additional_names=extra_names)
    stats, means = [], []
    for j, name in enumerate(extra_names):
        values = extra[:, j]
        stats.append({"feature": name, "n": len(values), "nonfinite": int(np.sum(~np.isfinite(values))),
                      "min": float(values.min()), "mean": float(values.mean()), "std": float(values.std()),
                      "median": float(np.median(values)), "max": float(values.max()),
                      "unique_values": len(np.unique(values))})
        for stage in track.meta.classes:
            v = values[y == stage]
            means.append({"feature": name, "stage": stage, "n": len(v), "mean": float(v.mean()), "median": float(np.median(v))})
    write_csv(output / "feature_statistics.csv", stats)
    write_csv(output / "feature_by_stage.csv", means)
    variants = [("baseline_11", base, track.feature_names()),
                (f"combined_{11 + len(extra_names)}", np.column_stack([base, extra]), track.feature_names() + extra_names),
                (f"additional_only_{len(extra_names)}", extra, extra_names)]
    variants.extend((f"baseline_plus_{name}", np.column_stack([base, extra[:, j]]), track.feature_names() + [name])
                    for j, name in enumerate(extra_names))
    summary, per_subject = [], []
    reference_groups = reference_true = None
    for name, X, names in variants:
        begin = time.monotonic()
        print(f"Evaluating {name}: {X.shape}, {len(set(groups))} LOSO folds", flush=True)
        model = default_baseline(seed=0, n_estimators=200, imbalance="balanced")
        model.set_params(clf__n_jobs=provenance["classifier"]["n_jobs"])
        report = evaluate_loso(track, X, y, groups, clf=model, cfg=cfg)
        if reference_groups is None:
            reference_groups, reference_true = report["y_group"], report["y_true"]
        np.testing.assert_array_equal(report["y_group"], reference_groups)
        np.testing.assert_array_equal(report["y_true"], reference_true)
        row = {"variant": name, "n_features": X.shape[1], **precise_metrics(report["y_true"], report["y_pred"])}
        kappas = []
        for group in np.unique(report["y_group"]):
            mask = np.asarray(report["y_group"]) == group
            metrics = precise_metrics(np.asarray(report["y_true"])[mask], np.asarray(report["y_pred"])[mask])
            per_subject.append({"variant": name, "subject": group, "n_epochs": int(mask.sum()), **metrics})
            kappas.append(metrics["cohens_kappa"])
        row.update(mean_subject_kappa=float(np.mean(kappas)), sd_subject_kappa=float(np.std(kappas, ddof=1)),
                   elapsed_seconds=time.monotonic() - begin)
        summary.append(row)
        report["experimental_feature_names"] = names
        report["precise_pooled_metrics"] = {key: row[key] for key in METRICS}
        write_json(output / f"{name}_report.json", report)
        write_csv(output / "summary.csv", summary)
        write_csv(output / "per_subject.csv", per_subject)
        print(f"  kappa={row['cohens_kappa']:.6f}, macro-F1={row['macro_f1']:.6f}, {row['elapsed_seconds']:.1f}s", flush=True)

    provenance["finished_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(output / "provenance.json", provenance)
    print(f"Saved complete comparison to {output}", flush=True)
    return output


if __name__ == "__main__":
    main()
