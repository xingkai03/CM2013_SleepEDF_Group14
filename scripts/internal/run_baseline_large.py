"""Evaluate the supplied baseline on local EDFs, without downloading or tuning.

Run: uv run --locked python -B scripts/internal/run_baseline.py --cache-dir sleep_edf_data
Subset: uv run --locked python -B scripts/internal/run_baseline.py --n-subjects 3 --nights 1 2
Outputs: a timestamped results directory with report.json and provenance.json.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import re
import subprocess
import time

from sklearn.base import clone
from sklearn.model_selection import GroupKFold

if __package__:
    from ._bootstrap import ROOT
else:
    # Direct invocation (and file-based import) needs scripts/ on the import path.
    import sys
    scripts_dir = str(Path(__file__).resolve().parents[1])
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from internal._bootstrap import ROOT

import numpy as np

from sleepedf.machine_learning import default_baseline
from sleepedf import SleepEDFTrack
from sleepedf.preprocessing.experiments import TargetedDenoising


def json_ready(value):
    """Convert NumPy values and undefined metrics to portable JSON values."""
    if isinstance(value, np.ndarray):
        return json_ready(value.tolist())
    if isinstance(value, np.generic):
        return json_ready(value.item())
    if isinstance(value, dict):
        return {str(k): json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def subject_id(value):
    subject = int(value)
    if not 0 <= subject <= 82:
        raise argparse.ArgumentTypeError("subject IDs must be between 0 and 82")
    return subject


def subject_count(value):
    count = int(value)
    if count < 5:
        raise argparse.ArgumentTypeError("5-fold GroupKFold requires at least 5 subjects")
    return count


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "sleep_edf_data")
    parser.add_argument("--output-dir", type=Path,
                        help="New output directory; existing directories are never overwritten.")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--n-subjects", type=subject_count, metavar="N",
        help="Use the first N cached Sleep-Cassette subjects in ascending ID order (N >= 2).",
    )
    selection.add_argument(
        "--subjects", type=subject_id, nargs="+", metavar="ID",
        help="Use these Sleep-Cassette subject IDs, e.g. 0 1 2 (default: all cached subjects).",
    )
    parser.add_argument(
        "--nights", type=int, nargs="+", choices=[1, 2],
        help="Use these night indices, e.g. 1 or 1 2 (default: all available nights).",
    )
    parser.add_argument(
        "--preprocess",
        choices=["none","bandpass", "wavelet","broken_segments","denoise_clipping"],
        default="none",
        help="Preprocessing experiment: none=P0, bandpass=P1 EEG 0.5-40Hz, wavelet=P2 EEG wavelet denoising, broken_segments=P3 exclude objectively identified near-flat epochs (EEG+EOG), denoise_clipping=P5 flag suspected EEG clipping.",
    )
    parser.add_argument("--resume", type=Path, metavar="RESULT_DIR",
                        help="Resume a run using an existing results directory with checkpoints.")
    return parser


def select_psgs(psgs, *, subjects=None, n_subjects=None, nights=None):
    """Select Sleep-Cassette files before loading, requiring requested pairs."""
    psgs = sorted(psgs)
    if subjects is None and n_subjects is None and nights is None:
        return psgs

    indexed = []
    for psg in psgs:
        match = re.fullmatch(r"SC4(\d{2})([12]).*-PSG\.edf", psg.name)
        if match:
            indexed.append((psg, int(match[1]), int(match[2])))
    available = sorted({subject for _, subject, _ in indexed})
    if not available:
        raise ValueError("No Sleep-Cassette PSG files found for subject/night selection.")
    if n_subjects is not None:
        if n_subjects < 5:
            raise ValueError("5-fold GroupKFold requires at least five different subjects.")
        if n_subjects > len(available):
            raise ValueError(
                f"Requested {n_subjects} subjects, but only {len(available)} are cached."
            )
        requested = set(available[:n_subjects])
    elif subjects is not None:
        requested = set(subjects)
        missing = sorted(requested - set(available))
        if missing:
            raise ValueError(f"Requested subject IDs are not cached: {missing}")
    else:
        requested = set(available)

    if nights is not None:
        pairs = {(subject, night) for _, subject, night in indexed}
        missing = sorted((subject, night) for subject in requested for night in set(nights)
                         if (subject, night) not in pairs)
        if missing:
            details = ", ".join(f"subject {subject}, night {night}" for subject, night in missing)
            raise ValueError(f"Requested recordings are not cached: {details}")
    selected = [psg for psg, subject, night in indexed
                if subject in requested and (nights is None or night in nights)]
    if len({psg.name[:5] for psg in selected}) < 5:
        raise ValueError("5-fold GroupKFold requires at least five different subjects.")
    return selected


def _stable_json(value):
    return json.dumps(json_ready(value), sort_keys=True, separators=(",", ":"), default=str)


def _digest(value):
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def fixed_subject_folds(groups, n_splits=5):
    """Use GroupKFold on one row per subject, not on epoch counts.

    This ensures identical subject partitions for P0/P1/P2 even if epoch
    counts change between preprocessing experiments.
    """
    unique = np.unique(np.asarray(groups).astype(str))
    if len(unique) < n_splits:
        raise ValueError(f"Need at least {n_splits} subjects, got {len(unique)}")
    cv = GroupKFold(n_splits=n_splits)
    for fold, (_, test_subject_idx) in enumerate(cv.split(unique, groups=unique)):
        test_subjects = unique[test_subject_idx].tolist()
        mask = np.isin(groups, test_subjects)
        tr, te = np.flatnonzero(~mask), np.flatnonzero(mask)
        if not len(tr) or not len(te):
            raise ValueError(f"Empty train/test fold {fold}")
        yield fold, tr, te, test_subjects


def evaluate_groupkfold_with_checkpoints(track, X, y, groups, clf, cfg, output,
                                         manifest, n_splits=5, resume=False):
    """Fixed subject folds, atomic checkpoints and verified resume."""
    X, y, groups = np.asarray(X), np.asarray(y), np.asarray(groups)
    folds = list(fixed_subject_folds(groups, n_splits))
    plan = [{"fold": k, "test_subjects": subjects} for k, _, _, subjects in folds]
    # Feature bytes are hashed so an old checkpoint cannot be reused if feature
    # extraction changes, even when the same EDF files are selected.
    features_hash = hashlib.sha256(np.ascontiguousarray(X).tobytes()).hexdigest()
    labels_hash = hashlib.sha256(np.ascontiguousarray(y.astype('U')).tobytes()).hexdigest()
    groups_hash = hashlib.sha256(np.ascontiguousarray(groups.astype('U')).tobytes()).hexdigest()
    signature = _digest({"protocol": "subject-fixed-groupkfold-v1",
                         "cfg": cfg, "classifier": clf.get_params(deep=True),
                         "files": manifest, "features_sha256": features_hash,
                         "labels_sha256": labels_hash, "groups_sha256": groups_hash,
                         "fold_plan": plan})
    meta_path = output / "checkpoint_manifest.json"
    checkpoint_dir = output / "checkpoints"
    if resume:
        if not meta_path.is_file():
            raise ValueError(f"Cannot resume: missing {meta_path}")
        old = json.loads(meta_path.read_text(encoding="utf-8"))
        if old.get("signature") != signature or old.get("fold_plan") != plan:
            raise ValueError("Resume refused: dataset, features, model, config or folds changed.")
    else:
        if output.exists():
            raise ValueError(f"New run directory already exists: {output}")
        output.mkdir(parents=True, exist_ok=False)
        meta_path.write_text(json.dumps({"signature": signature, "fold_plan": plan,
                                         "n_subjects": len(np.unique(groups)),
                                         "n_epochs": len(y)}, indent=2) + "\n",
                             encoding="utf-8")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    yt, yp, gg, ff = [], [], [], []
    for k, tr, te, test_subjects in folds:
        checkpoint = checkpoint_dir / f"fold_{k + 1:02d}.npz"
        print(f"\nFold {k+1}/{n_splits}: train={len(tr)} epochs, "
              f"test={len(te)} epochs ({len(test_subjects)} subjects)", flush=True)
        if checkpoint.exists():
            with np.load(checkpoint, allow_pickle=False) as saved:
                if (str(saved["signature"].item()) != signature
                    or not np.array_equal(saved["test_indices"], te)
                    or not np.array_equal(saved["y_true"].astype(str), y[te].astype(str))
                    or not np.array_equal(saved["groups"].astype(str), groups[te].astype(str))
                    or len(saved["y_pred"]) != len(te)):
                    raise ValueError(f"Checkpoint mismatch: {checkpoint}")
                preds = saved["y_pred"].copy()
            print(f"  Resumed from {checkpoint.name}; training skipped", flush=True)
        else:
            start = time.perf_counter()
            if set(groups[tr].tolist()) & set(groups[te].tolist()):
                raise ValueError(f"Subject leakage in fold {k+1}")
            selector = track.select_features(X[tr], y[tr], cfg)
            # select='none' is the current P0/P1/P2 protocol.
            if selector is None:
                Xtr, Xte = X[tr], X[te]
            else:
                Xtr, Xte = selector.transform(X[tr]), selector.transform(X[te])
            model = clone(clf)
            model.fit(Xtr, y[tr])
            preds = np.asarray(model.predict(Xte))
            temp = checkpoint.with_suffix(".tmp")
            try:
                with temp.open("wb") as stream:
                    np.savez_compressed(stream, signature=np.array(signature),
                                        test_indices=te, y_true=y[te].astype(str),
                                        y_pred=preds.astype(str), groups=groups[te].astype(str))
                temp.replace(checkpoint)
            finally:
                if temp.exists():
                    temp.unlink()
            print(f"  Completed in {time.perf_counter()-start:.1f}s; "
                  f"saved {checkpoint.name}", flush=True)
        yt.extend(y[te].tolist())
        yp.extend(preds.tolist())
        gg.extend(groups[te].tolist())
        ff.extend([k] * len(te))
    return track._make_report(yt, yp, groups=gg, folds=ff,
                              n_groups=len(np.unique(groups)))


def run(args, parser, *, clf=None, classifier_info=None, seed=0,
        output_tag=None, extra_packages=()):
    """Run the shared EDF selection, evaluation and reporting workflow.

    Experiment entry points can supply a fresh classifier and its provenance.
    The baseline entry point keeps its supplied model and output names.
    """
    cache = args.cache_dir.resolve()
    psgs = sorted(cache.rglob("*-PSG.edf"))
    if not psgs:
        parser.error(f"No PSG EDF files found under {cache}")
    try:
        psgs = select_psgs(psgs, subjects=args.subjects, n_subjects=args.n_subjects,
                          nights=args.nights)
    except ValueError as error:
        parser.error(str(error))
    holdout_ids = {8, 16, 24, 32, 40, 48, 56, 64, 72, 80}

    selected_ids = {
        int(psg.name[3:5])
        for psg in psgs
    }

    forbidden = sorted(selected_ids & holdout_ids)

    if forbidden:
        parser.error(
            f"Holdout subjects cannot be used for development: {forbidden}"
        )

    # Match subject AND night, allowing the scorer suffix to differ (E0 vs EC/EH).
    input_files = []
    for psg in psgs:
        matches = sorted(psg.parent.glob(f"{psg.name[:6]}*Hypnogram.edf"))
        if len(matches) != 1:
            parser.error(f"Expected exactly one hypnogram for {psg.name}; found {len(matches)}")
        input_files.extend([psg, matches[0]])
    manifest = [{"path": str(p.relative_to(cache)), "bytes": p.stat().st_size,
                 "sha256": sha256(p)} for p in input_files]
    started = datetime.now(timezone.utc)
    experiment = {
        "none": "P0",
        "bandpass": "P1",
        "wavelet": "P2",
        "broken_segments": "P3",
        "denoise_clipping": "P5",
    }[args.preprocess]
    tag = f"_{output_tag}" if output_tag else ""
    output = (args.resume or args.output_dir or ROOT / "results" /
              f"real__{experiment}{tag}_{started.strftime('%Y%m%dT%H%M%S%fZ')}").resolve()
    if args.resume and args.output_dir:
        parser.error("Use --resume or --output-dir, not both")
    if output.exists() and not args.resume:
        parser.error(f"Output directory already exists: {output}")

    cfg = {"seed": seed, "preprocess": args.preprocess, "spectral_method": "welch",
           "select": "none"}
    track = SleepEDFTrack()

    print(
        f"Processing {len(psgs)} PSG/hypnogram pairs sequentially from {cache}",
        flush=True,
    )

    expected = {p.name.removesuffix("-PSG.edf") for p in psgs}
    loaded = set()
    subjects = set()

    Xs, ys, gs = [], [], []
    recording_info = []

    clipping_qc = None

    if args.preprocess == "denoise_clipping":
        detector = TargetedDenoising(
            noise_type="clipping",
            min_plateau_samples=3,
        )

        clipping_qc = {
            "method": "recording_extrema_plateau",
            "channel": "eeg",
            "action": "flag_only",
            "confirmed_clipping": False,
            "min_plateau_samples": 3,
            "threshold_duration_ms": 30.0,
            "extrema_scope": "individual_full_recording",
            "recordings": [],
        }

    print(
        f"Extracting the 11 supplied features "
        f"(preprocess={cfg['preprocess']}, no cropping)...",
        flush=True,
    )

    for i, psg in enumerate(psgs, start=1):
        print(
            f"[{i}/{len(psgs)}] Processing {psg.name}",
            flush=True,
        )

        # Load only the current PSG/Hypnogram pair
        recs = track.load(str(cache), psg_paths=[psg])

        # Verify that the expected recording was loaded
        expected_record = psg.name.removesuffix("-PSG.edf")

        if len(recs) != 1:
            raise ValueError(
                f"Expected one recording for {psg.name}, got {len(recs)}"
            )

        rec = recs[0]

        if rec.meta["record"] != expected_record:
            raise ValueError(
                f"Unexpected recording ID for {psg.name}: "
                f"{rec.meta['record']}"
            )

        loaded.add(rec.meta["record"])
        subjects.add(rec.group)

        # Preserve the original quality checks
        if len(rec.labels) == 0:
            raise ValueError(
                f"No labelled epochs in {rec.meta['record']}"
            )

        if rec.fs != 100 or any(
            v.shape != (len(rec.labels), 3000)
            for v in rec.epochs.values()
        ):
            raise ValueError(
                f"Unexpected sampling rate or epoch shape "
                f"in {rec.meta['record']}"
            )

        print(
            f"  {rec.meta['record']}: "
            f"subject={rec.group}, epochs={len(rec.labels)}",
            flush=True,
        )
        recording_info.append({
            "record": rec.meta["record"],
            "subject": rec.group,
            "epochs": len(rec.labels),
        })
        # Preserve the P5 clipping quality-control report
        if clipping_qc is not None:
            processed = detector.transform(rec)
            info = processed.meta["suspected_clipping"]

            clipping_qc["recordings"].append({
                "record": rec.meta["record"],
                "subject": rec.group,
                "n_epochs": len(rec.labels),
                "n_flagged": info["n_flagged"],
                "flagged_epoch_indices": info["flagged_epoch_indices"],
                "lower_extreme_uv": (
                    info["lower_extreme"] * 1e6
                    if info["lower_extreme"] is not None else None
                ),
                "upper_extreme_uv": (
                    info["upper_extreme"] * 1e6
                    if info["upper_extreme"] is not None else None
                ),
            })

        # Apply the existing preprocessing and feature extraction
        X_part, y_part, groups_part = track.build_dataset(recs, cfg)

        # Check features and labels for this recording
        if (
            X_part.shape != (len(y_part), 11)
            or len(groups_part) != len(y_part)
            or not np.isfinite(X_part).all()
        ):
            raise ValueError(
                f"Invalid features or labels in {rec.meta['record']}"
            )

        Xs.append(X_part)
        ys.append(y_part)
        gs.append(groups_part)

        # Release the raw recording before loading the next one
        if clipping_qc is not None:
            del processed
        del rec, recs

    # Verify that every selected recording was processed
    if loaded != expected:
        raise ValueError(
            f"Loader did not return every recording: "
            f"expected={expected}, loaded={loaded}"
        )

    subjects = sorted(subjects)

    if len(subjects) < 5:
        raise ValueError("5-fold GroupKFold requires at least five different subjects.")

    cfg["loso_max_groups"] = 12
    cfg["cv_max_splits"] = 5

    # Finalise the P5 quality-control summary
    if clipping_qc is not None:
        clipping_qc["total_epochs"] = sum(
            item["n_epochs"] for item in clipping_qc["recordings"]
        )

        clipping_qc["total_flagged"] = sum(
            item["n_flagged"] for item in clipping_qc["recordings"]
        )

        print(
            f"P5 QC: {clipping_qc['total_flagged']}/"
            f"{clipping_qc['total_epochs']} epochs flagged.",
            flush=True,
        )

    # Combine the features extracted from individual recordings
    X = np.vstack(Xs)
    y = np.concatenate(ys)
    groups = np.concatenate(gs)

    # Preserve the original dataset-level checks
    if (
        X.shape != (len(y), 11)
        or len(groups) != len(y)
        or not np.isfinite(X).all()
    ):
        raise ValueError(
            "Invalid feature shape, label alignment, or non-finite features."
        )

    if len(y) == 0:
        raise ValueError(
            "No labelled epochs remain after preprocessing."
        )

    retained_subjects = set(np.asarray(groups).tolist())
    missing_subjects = sorted(set(subjects) - retained_subjects)

    if missing_subjects:
        raise ValueError(
            f"Preprocessing removed every epoch for subjects: "
            f"{missing_subjects}."
        )

    print(f"Evaluating {len(y)} epochs with 5 GroupKFold folds...", flush=True)

    if clf is None:
        clf = default_baseline(
            seed=seed,
            n_estimators=200,
            imbalance="balanced",
        )

    rep = evaluate_groupkfold_with_checkpoints(
        track, X, y, groups, clf, cfg, output, manifest,
        n_splits=5, resume=args.resume is not None,
    )
    if len(rep["y_pred"]) != len(y) or np.asarray(rep["confusion"]).sum() != len(y):
        raise ValueError("Evaluation did not account for every epoch.")
    if len(rep["per_fold"]) != 5:
        raise ValueError("Expected exactly 5 GroupKFold folds.")

    provenance = {
        "data_kind": "real Sleep-EDF, not synthetic", "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "cache_dir": str(cache), "files": manifest, "config": cfg,
        "selection": {"subjects": args.subjects, "n_subjects": args.n_subjects,
                      "nights": args.nights},
        "classifier": classifier_info if classifier_info is not None else {
            "factory": "sleepedf.machine_learning.default_baseline", "seed": seed,
            "n_estimators": 200, "imbalance": "balanced"},
        "cropping": "none", "epoch_seconds": 30,
        "fs": 100, "feature_shape": X.shape, "feature_names": track.feature_names(),
        "subjects": subjects,
        "recordings": recording_info,
        "cv_protocol": "subject-fixed-groupkfold-v1",
        "cv_fold_plan": json.loads((output / "checkpoint_manifest.json").read_text(encoding="utf-8"))["fold_plan"],
        "class_counts": {str(k): int(v) for k, v in zip(*np.unique(y, return_counts=True))},
        "python": platform.python_version(),
        "packages": {p: version(p) for p in dict.fromkeys(
            ("numpy", "scipy", "scikit-learn", "mne") + tuple(extra_packages) +
            (("PyWavelets",) if args.preprocess == "wavelet" else ()))},
        "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "working_tree_status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True),
        "source_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in sorted(
            list((ROOT / "src").rglob("*.py")) + list((ROOT / "scripts").rglob("*.py")) +
            list(ROOT.glob("*.py")))},
    }
    for name, value in (("report.json", rep), ("provenance.json", provenance)):
        (output / name).write_text(json.dumps(json_ready(value), indent=2, allow_nan=False) + "\n")

    if clipping_qc is not None:
        (output / "clipping_qc.json").write_text(
            json.dumps(
                json_ready(clipping_qc),
                indent=2,
                allow_nan=False,
            ) + "\n"
        )

    print(rep["summary"])
    for key in ("accuracy", "cohens_kappa", "macro_f1", "balanced_accuracy"):
        print(f"{key}: {rep[key]}")
    print("Confusion matrix (rows=true, columns=predicted):", rep["labels"])
    print(np.asarray(rep["confusion"]))
    print(f"Saved results to {output}")
    return output


def main():
    parser = build_parser()
    return run(parser.parse_args(), parser)


if __name__ == "__main__":
    main()
