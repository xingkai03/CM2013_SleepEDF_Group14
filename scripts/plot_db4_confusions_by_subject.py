
from pathlib import Path
import json

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

RESULTS_DIR = ROOT / "results" / "wavelet_comparison" / "loso"
JSON_PATH = RESULTS_DIR / "wavelet_loso_reports.json"
OUTPUT_PATH = RESULTS_DIR / "db4_confusions_by_subject.png"

SUBJECTS = ["SC400", "SC401", "SC402"]

# Load previously saved LOSO predictions
with open(JSON_PATH, "r", encoding="utf-8") as f:
    reports = json.load(f)

report = reports["db4"]

labels = list(report["labels"])
y_true = np.asarray(report["y_true"])
y_pred = np.asarray(report["y_pred"])
y_group = np.asarray(report["y_group"])

assert len(y_true) == len(y_pred) == len(y_group)
assert set(np.unique(y_group)) == set(SUBJECTS)

fig, axes = plt.subplots(
    1, 3,
    figsize=(18, 5.5),
    constrained_layout=True,
)

for ax, subject in zip(axes, SUBJECTS):

    mask = y_group == subject

    # Construct the confusion matrix using NumPy
    cm = np.zeros((len(labels), len(labels)), dtype=int)

    for i, true_label in enumerate(labels):
        for j, predicted_label in enumerate(labels):
            cm[i, j] = np.sum(
                (y_true[mask] == true_label)
                & (y_pred[mask] == predicted_label)
            )

    # Normalize by true stage (rows)
    row_totals = cm.sum(axis=1, keepdims=True)

    cm_pct = np.divide(
        cm,
        row_totals,
        out=np.zeros_like(cm, dtype=float),
        where=row_totals != 0,
    ) * 100

    # Plot the normalized confusion matrix
    im = ax.imshow(
        cm_pct,
        cmap="Blues",
        vmin=0,
        vmax=100,
    )

    ax.set_xticks(range(len(labels)), labels)
    ax.set_yticks(range(len(labels)), labels)

    ax.set_xlabel("Predicted stage")
    ax.set_ylabel("True stage")

    ax.set_title(
        f"{subject} — {mask.sum()} epochs",
        fontsize=13,
        fontweight="bold",
    )

    # Display percentage inside each cell
    for i in range(len(labels)):
        for j in range(len(labels)):

            value = cm_pct[i, j]

            ax.text(
                j, i,
                f"{value:.1f}",
                ha="center",
                va="center",
                color="white" if value > 55 else "black",
                fontsize=10,
            )

    # Add cell boundaries
    ax.set_xticks(
        np.arange(-0.5, len(labels), 1),
        minor=True,
    )
    ax.set_yticks(
        np.arange(-0.5, len(labels), 1),
        minor=True,
    )
    ax.grid(
        which="minor",
        color="white",
        linewidth=1,
    )
    ax.tick_params(which="minor", bottom=False, left=False)

fig.colorbar(
    im,
    ax=axes,
    shrink=0.75,
    label="Percentage of true stage (%)",
)

fig.suptitle(
    "Sleep-EDF — db4: LOSO confusion matrices by subject",
    fontsize=16,
    fontweight="bold",
)

fig.savefig(OUTPUT_PATH, dpi=200, bbox_inches="tight")

print(f"Figure saved to: {OUTPUT_PATH}")

plt.show()
