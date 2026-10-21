
"""Prepare P1/P6 Sleep-EDF features and aligned clock-cropping masks."""

from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sleepedf.track import SleepEDFTrack
from sleepedf.preprocessing.epoch_timestamps import attach_epoch_timestamps
from sleepedf.preprocessing.experiments import ClockBasedCropping
from sklearn.base import clone
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    cohen_kappa_score,
    f1_score,
    confusion_matrix,
)
import matplotlib.pyplot as plt
from sklearn.metrics import ConfusionMatrixDisplay
from sleepedf.machine_learning.baseline import make_random_forest

# --------------------------------------------------
# Configuration
# --------------------------------------------------

cache = ROOT / "sleep_edf_data"

record_ids = [
    "SC4001E0",
    "SC4002E0",
    "SC4011E0",
    "SC4012E0",
    "SC4021E0",
    "SC4022E0",
]

cfg = {
    "seed": 0,
    "preprocess": "clock_cropping",
    "spectral_method": "welch",
    "select": "none",
}

track = SleepEDFTrack()

cropper = ClockBasedCropping(
    start_time="20:30",
    end_time="11:00",
    action="flag",
)

recordings = []


# --------------------------------------------------
# Load recordings and attach timestamps
# --------------------------------------------------

for record_id in record_ids:

    psg_candidates = sorted(
        cache.rglob(f"{record_id}-PSG.edf")
    )

    assert len(psg_candidates) == 1, (
        f"Expected one PSG for {record_id}"
    )

    psg = psg_candidates[0]

    hyp_candidates = sorted(
        psg.parent.glob(
            f"{record_id[:6]}*-Hypnogram.edf"
        )
    )

    assert len(hyp_candidates) == 1, (
        f"Expected one hypnogram for {record_id}"
    )

    hyp = hyp_candidates[0]

    recording = track.load(
        str(cache),
        psg_paths=[psg],
    )[0]

    enriched = attach_epoch_timestamps(
        recording,
        psg,
        hyp,
    )

    # Detect only; the actual filtering is applied
    # by track.build_dataset() using cfg.
    mask = cropper.detect(enriched)

    meta = dict(enriched.meta)
    meta["nighttime_epoch_mask"] = mask.copy()

    from sleepedf.reference.adapter import Recording

    enriched = Recording(
        group=enriched.group,
        fs=enriched.fs,
        epochs=enriched.epochs,
        labels=enriched.labels,
        meta=meta,
    )

    recordings.append(enriched)

    print(
        f"{record_id}: "
        f"{len(enriched.labels)} epochs, "
        f"{int(mask.sum())} nighttime"
    )


# --------------------------------------------------
# Extract features using the P6 preprocessing
# --------------------------------------------------

X, y, groups = track.build_dataset(
    recordings,
    cfg,
)

nighttime_mask = np.concatenate([
    rec.meta["nighttime_epoch_mask"]
    for rec in recordings
])


# --------------------------------------------------
# Validate alignment
# --------------------------------------------------

assert len(X) == len(y)
assert len(X) == len(groups)
assert len(X) == len(nighttime_mask)

assert X.shape[0] == 16688
assert nighttime_mask.sum() == 10438

assert X.shape[1] == 11, (
    f"Expected 11 features, got {X.shape[1]}"
)

assert len(np.unique(groups)) == 3

print("\n====================================")
print("DATASET VALIDATION")
print("====================================")

print(f"Feature matrix shape: {X.shape}")
print(f"Labels shape: {y.shape}")
print(f"Groups shape: {groups.shape}")
print(f"Nighttime mask shape: {nighttime_mask.shape}")

print(f"Nighttime epochs: {int(nighttime_mask.sum())}")
print(f"Subjects: {np.unique(groups)}")

print("\nP6 dataset preparation PASSED.")


# --------------------------------------------------
# 6. LOSO evaluation: P1 vs P6
# --------------------------------------------------

print("\n====================================")
print("LOSO EVALUATION: P1 VS P6")
print("====================================")

loso = LeaveOneGroupOut()

classifier = make_random_forest(
    seed=0,
    n_estimators=200,
    imbalance="balanced",
)

results = {}
predictions_by_experiment = {}

for experiment in ("P1", "P6"):

    print(f"\n--- {experiment} ---")

    all_true = []
    all_pred = []
    per_subject = []
    all_test_indices = []

    for fold, (train_idx, test_idx) in enumerate(
        loso.split(X, y, groups),
        start=1,
    ):

        test_subject = np.unique(groups[test_idx])

        assert len(test_subject) == 1
        test_subject = test_subject[0]

        # P1: all training epochs
        # P6: nighttime training epochs only
        if experiment == "P6":
            selected_train_idx = train_idx[
                nighttime_mask[train_idx]
            ]
        else:
            selected_train_idx = train_idx

        assert len(selected_train_idx) > 0

        # Subject leakage guard
        assert not np.intersect1d(
            groups[selected_train_idx],
            groups[test_idx],
        ).size

        # Feature selection fitted on training data only
        selector = track.select_features(
            X[selected_train_idx],
            y[selected_train_idx],
            cfg,
        )

        X_train = selector.transform(
            X[selected_train_idx]
        )

        X_test = selector.transform(
            X[test_idx]
        )

        # Fresh classifier for each fold
        fold_classifier = clone(classifier)

        fold_classifier.fit(
            X_train,
            y[selected_train_idx],
        )

        predictions = fold_classifier.predict(X_test)

        y_test = y[test_idx]
        # Confusion matrix for this subject, normalized by true class
        classes = ["W", "N1", "N2", "N3", "REM"]

        cm = confusion_matrix(
            y_test,
            predictions,
            labels=classes,
            normalize="true",
        )

        fig, ax = plt.subplots(figsize=(7, 6))

        display = ConfusionMatrixDisplay(
            confusion_matrix=cm * 100,
            display_labels=classes,
        )

        display.plot(
            ax=ax,
            cmap="Blues",
            values_format=".1f",
            colorbar=True,
        )

        ax.set_title(
            f"{experiment} - {test_subject}\n"
            "Confusion matrix (%)"
        )

        ax.set_xlabel("Predicted sleep stage")
        ax.set_ylabel("True sleep stage")

        plt.tight_layout()

        output_dir = ROOT / "results" / "clock_cropping"
        output_dir.mkdir(parents=True, exist_ok=True)

        plt.savefig(
            output_dir / f"{experiment}_{test_subject}_confusion_pct.png",
            dpi=300,
            bbox_inches="tight",
        )

        plt.close(fig)

        # Store predictions
        all_true.extend(y_test)
        all_pred.extend(predictions)
        all_test_indices.extend(test_idx)

        # Per-subject metrics
        subject_result = {
            "subject": test_subject,
            "train_epochs": len(selected_train_idx),
            "test_epochs": len(test_idx),
            "accuracy": accuracy_score(
                y_test, predictions
            ),
            "balanced_accuracy": balanced_accuracy_score(
                y_test, predictions
            ),
            "macro_f1": f1_score(
                y_test,
                predictions,
                average="macro",
                zero_division=0,
            ),
            "cohens_kappa": cohen_kappa_score(
                y_test, predictions
            ),
        }

        per_subject.append(subject_result)

        print(
            f"Fold {fold} | "
            f"Test subject: {test_subject} | "
            f"Train: {len(selected_train_idx)} | "
            f"Test: {len(test_idx)} | "
            f"Kappa: {subject_result['cohens_kappa']:.4f} | "
            f"Macro-F1: {subject_result['macro_f1']:.4f}"
        )

    # Pooled metrics
    all_true = np.asarray(all_true)
    all_pred = np.asarray(all_pred)
    all_test_indices = np.asarray(all_test_indices, dtype=int)

    # Reconstruct predictions in the original dataset order.
    predictions_in_original_order = np.empty(
        len(y),
        dtype=all_pred.dtype,
    )

    predictions_in_original_order[all_test_indices] = all_pred

    assert len(np.unique(all_test_indices)) == len(y)
    np.testing.assert_array_equal(
        y[all_test_indices],
        all_true,
    )

    predictions_by_experiment[experiment] = predictions_in_original_order

    results[experiment] = {
        "accuracy": accuracy_score(all_true, all_pred),
        "balanced_accuracy": balanced_accuracy_score(
            all_true, all_pred
        ),
        "macro_f1": f1_score(
            all_true,
            all_pred,
            average="macro",
            zero_division=0,
        ),
        "cohens_kappa": cohen_kappa_score(
            all_true, all_pred
        ),
        "per_subject": per_subject,
        "confusion_matrix": confusion_matrix(
            all_true,
            all_pred,
            labels=["W", "N1", "N2", "N3", "REM"],
        ),
    }


# --------------------------------------------------
# 7. Comparison
# --------------------------------------------------

print("\n====================================")
print("POOLED RESULTS: P1 VS P6")
print("====================================")

metrics = [
    "accuracy",
    "balanced_accuracy",
    "macro_f1",
    "cohens_kappa",
]

for metric in metrics:

    p1 = results["P1"][metric]
    p6 = results["P6"][metric]

    print(
        f"{metric:20s} "
        f"P1={p1:.4f} | "
        f"P6={p6:.4f} | "
        f"Delta={p6 - p1:+.4f}"
    )

print("\nP1 confusion matrix:")
print(results["P1"]["confusion_matrix"])

print("\nP6 confusion matrix:")
print(results["P6"]["confusion_matrix"])

print("\nLOSO evaluation completed.")


# --------------------------------------------------
# 8. Nighttime vs outside-window evaluation
# --------------------------------------------------

print("\n====================================")
print("NIGHTTIME VS OUTSIDE-WINDOW ANALYSIS")
print("====================================")

classes = ["W", "N1", "N2", "N3", "REM"]

evaluation_regions = {
    "Nighttime (20:30-11:00)": nighttime_mask,
    "Outside window": ~nighttime_mask,
}

for region_name, region_mask in evaluation_regions.items():

    print(f"\n--- {region_name} ---")

    y_region = y[region_mask]

    print(f"Number of epochs: {len(y_region)}")

    unique_labels, counts = np.unique(
        y_region,
        return_counts=True,
    )

    print("True label distribution:")
    for label, count in zip(unique_labels, counts):
        print(f"  {label}: {count}")

    for experiment in ("P1", "P6"):

        pred_region = predictions_by_experiment[
            experiment
        ][region_mask]

        accuracy = accuracy_score(
            y_region,
            pred_region,
        )

        print(f"\n{experiment}:")
        print(f"  Accuracy: {accuracy:.4f}")

        if len(unique_labels) > 1:

            balanced_acc = balanced_accuracy_score(
                y_region,
                pred_region,
            )

            macro_f1 = f1_score(
                y_region,
                pred_region,
                labels=classes,
                average="macro",
                zero_division=0,
            )

            kappa = cohen_kappa_score(
                y_region,
                pred_region,
            )

            print(f"  Balanced accuracy: {balanced_acc:.4f}")
            print(f"  Macro-F1: {macro_f1:.4f}")
            print(f"  Cohen's kappa: {kappa:.4f}")

        else:
            print(
                "  Only one true class is present; "
                "five-class metrics are not reported."
            )

        cm = confusion_matrix(
            y_region,
            pred_region,
            labels=classes,
        )

        print("  Confusion matrix:")
        print(cm)

        if len(unique_labels) == 1 and unique_labels[0] == "W":

            wake_recall = np.mean(
                pred_region == "W"
            )

            false_wake_rate = 1 - wake_recall

            print(f"  Wake recall: {wake_recall:.4f}")
            print(
                f"  Wake misclassification rate: "
                f"{false_wake_rate:.4f}"
            )
