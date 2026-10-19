
from pathlib import Path
import json

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]

RESULTS_DIR = ROOT / "results" / "wavelet_comparison" / "loso"
JSON_PATH = RESULTS_DIR / "wavelet_loso_reports.json"
OUTPUT_PATH = RESULTS_DIR / "wavelet_confusion_matrices.png"

WAVELETS = ["db4", "sym4", "coif1", "coif3"]

with open(JSON_PATH, "r", encoding="utf-8") as f:
    reports = json.load(f)

fig, axes = plt.subplots(
    nrows=4,
    ncols=2,
    figsize=(15, 22),
    constrained_layout=True,
)

for row, wavelet in enumerate(WAVELETS):

    report = reports[wavelet]

    labels = report["labels"]
    cm = np.asarray(report["confusion"], dtype=int)

    # Each row corresponds to one true sleep stage.
    row_totals = cm.sum(axis=1, keepdims=True)

    cm_pct = np.divide(
        cm,
        row_totals,
        out=np.zeros_like(cm, dtype=float),
        where=row_totals != 0,
    ) * 100

    # Left: absolute number of epochs
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=labels,
        yticklabels=labels,
        ax=axes[row, 0],
        cbar=False,
        linewidths=0.5,
        linecolor="white",
    )

    axes[row, 0].set_title(
        f"{wavelet} — Confusion matrix (counts)",
        fontsize=13,
        fontweight="bold",
    )
    axes[row, 0].set_xlabel("Predicted stage")
    axes[row, 0].set_ylabel("True stage")

    # Right: percentage of each true stage
    sns.heatmap(
        cm_pct,
        annot=True,
        fmt=".1f",
        cmap="Blues",
        vmin=0,
        vmax=100,
        xticklabels=labels,
        yticklabels=labels,
        ax=axes[row, 1],
        cbar=False,
        linewidths=0.5,
        linecolor="white",
        annot_kws={"fontsize": 10},
    )

    axes[row, 1].set_title(
        f"{wavelet} — Row-normalized confusion matrix (%)",
        fontsize=13,
        fontweight="bold",
    )
    axes[row, 1].set_xlabel("Predicted stage")
    axes[row, 1].set_ylabel("True stage")

fig.suptitle(
    "Sleep-EDF — Wavelet comparison (3-fold LOSO)",
    fontsize=18,
    fontweight="bold",
)

fig.savefig(OUTPUT_PATH, dpi=200, bbox_inches="tight")
plt.show()

print(f"Figure saved to: {OUTPUT_PATH}")
