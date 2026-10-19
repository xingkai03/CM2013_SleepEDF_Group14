
from pathlib import Path
from collections import Counter
import csv
import json

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

RESULTS_DIR = ROOT / "results" / "wavelet_comparison" / "loso"
JSON_PATH = RESULTS_DIR / "wavelet_loso_reports.json"

SUBJECTS = ["SC400", "SC401", "SC402"]

# Load original stage labels and subject identifiers
with open(JSON_PATH, "r", encoding="utf-8") as f:
    reports = json.load(f)

report = reports["db4"]

labels = list(report["labels"])
y_true = np.asarray(report["y_true"])
y_group = np.asarray(report["y_group"])

assert len(y_true) == len(y_group)
assert set(np.unique(y_group)) == set(SUBJECTS)

counts = np.zeros(
    (len(SUBJECTS), len(labels)),
    dtype=int
)

# Count the actual number of epochs per stage and subject
for i, subject in enumerate(SUBJECTS):
    subject_labels = y_true[y_group == subject]
    stage_counts = Counter(subject_labels)

    for j, stage in enumerate(labels):
        counts[i, j] = stage_counts[stage]

# Convert counts to percentages within each subject
subject_totals = counts.sum(axis=1, keepdims=True)

percentages = (
    counts / subject_totals * 100
)

# Print results
print("\nSTAGE DISTRIBUTION — COUNTS")

print(f"{'Subject':<10}", end="")
for stage in labels:
    print(f"{stage:>10}", end="")
print(f"{'Total':>10}")

for i, subject in enumerate(SUBJECTS):
    print(f"{subject:<10}", end="")
    for value in counts[i]:
        print(f"{value:>10}", end="")
    print(f"{counts[i].sum():>10}")

print("\nSTAGE DISTRIBUTION — PERCENTAGES")

print(f"{'Subject':<10}", end="")
for stage in labels:
    print(f"{stage:>10}", end="")
print()

for i, subject in enumerate(SUBJECTS):
    print(f"{subject:<10}", end="")
    for value in percentages[i]:
        print(f"{value:>9.1f}%", end="")
    print()

# Save numerical results
csv_path = RESULTS_DIR / "stage_distribution_by_subject.csv"

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(
        ["subject", "total_epochs"]
        + [f"{stage}_count" for stage in labels]
        + [f"{stage}_percent" for stage in labels]
    )

    for i, subject in enumerate(SUBJECTS):
        writer.writerow(
            [subject, int(counts[i].sum())]
            + counts[i].tolist()
            + percentages[i].round(2).tolist()
        )

# Plot percentage distribution
fig, ax = plt.subplots(figsize=(11, 6))

x = np.arange(len(SUBJECTS))
bottom = np.zeros(len(SUBJECTS))

for j, stage in enumerate(labels):
    values = percentages[:, j]

    bars = ax.bar(
        x,
        values,
        bottom=bottom,
        label=stage,
    )

    for i, value in enumerate(values):
        if value >= 4:
            ax.text(
                x[i],
                bottom[i] + value / 2,
                f"{value:.1f}%",
                ha="center",
                va="center",
                fontsize=10,
            )

    bottom += values

ax.set_xticks(x, SUBJECTS)
ax.set_ylabel("Percentage of epochs (%)")
ax.set_ylim(0, 100)
ax.set_title(
    "Sleep-EDF — True sleep-stage distribution by subject"
)
ax.legend(
    title="Sleep stage",
    bbox_to_anchor=(1.02, 1),
    loc="upper left",
)

fig.tight_layout()

figure_path = RESULTS_DIR / "stage_distribution_by_subject.png"

fig.savefig(
    figure_path,
    dpi=200,
    bbox_inches="tight",
)

print(f"\nCSV saved to: {csv_path}")
print(f"Figure saved to: {figure_path}")

plt.show()
