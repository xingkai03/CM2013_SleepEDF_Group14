
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "results" / "multichannel_audit_68" / "epoch_metrics.csv"
OUTPUT = ROOT / "results" / "multichannel_audit_68"

df = pd.read_csv(INPUT)

print("Total rows:", len(df))
print("Channels:", df["channel"].value_counts().to_dict())
print("Subjects:", df["subject"].nunique())
print("Recordings:", df["record"].nunique())

# Summary of signal integrity by channel.
summary = df.groupby("channel").agg(
    epochs=("epoch_index", "count"),
    nonfinite=("finite", lambda x: (~x).sum()),
    plateaus=("plateau_detected", "sum"),
    median_std_v=("std_v", "median"),
    median_ptp_v=("ptp_v", "median"),
    median_max_step_v=("max_step_v", "median"),
    max_plateau_samples=("longest_plateau_samples", "max"),
)

summary["plateau_pct"] = (
    100 * summary["plateaus"] / summary["epochs"]
)

print("\n=== CHANNEL SUMMARY ===")
print(summary.to_string())

summary.to_csv(OUTPUT / "channel_summary.csv")

# Distribution quantiles help identify extreme values.
quantiles = (
    df.groupby("channel")[
        ["std_v", "ptp_v", "max_step_v", "longest_plateau_samples"]
    ]
    .quantile([0.01, 0.05, 0.50, 0.95, 0.99, 0.999])
)

print("\n=== QUANTILES ===")
print(quantiles.to_string())

quantiles.to_csv(OUTPUT / "channel_quantiles.csv")

# Where are plateaus concentrated?
plateau_by_record = (
    df.groupby(["subject", "record", "channel"])
    .agg(
        epochs=("epoch_index", "count"),
        plateaus=("plateau_detected", "sum"),
        longest_plateau=("longest_plateau_samples", "max"),
    )
    .reset_index()
)

plateau_by_record["plateau_pct"] = (
    100 * plateau_by_record["plateaus"] / plateau_by_record["epochs"]
)

plateau_by_record.to_csv(
    OUTPUT / "plateaus_by_record.csv", index=False
)

print("\n=== RECORDINGS WITH MOST PLATEAUS ===")
print(
    plateau_by_record.sort_values(
        "plateau_pct", ascending=False
    ).head(15).to_string(index=False)
)

# Long plateaus: exploratory thresholds at 100 Hz.
print("\n=== LONG PLATEAUS BY CHANNEL ===")

thresholds = [3, 5, 10, 20, 50]

rows = []

for channel, group in df.groupby("channel"):
    for threshold in thresholds:
        count = int(
            (group["longest_plateau_samples"] >= threshold).sum()
        )

        rows.append({
            "channel": channel,
            "threshold_samples": threshold,
            "threshold_ms": threshold * 10,
            "n_epochs": count,
            "pct_epochs": 100 * count / len(group),
        })

long_plateaus = pd.DataFrame(rows)

print(long_plateaus.to_string(index=False))

long_plateaus.to_csv(
    OUTPUT / "long_plateau_thresholds.csv",
    index=False,
)

# Investigate EEG plateaus lasting at least 200 ms.
eeg_long = df[
    (df["channel"] == "eeg")
    & (df["longest_plateau_samples"] >= 20)
].copy()

print("\n=== EEG PLATEAUS >= 200 MS ===")
print("Total epochs:", len(eeg_long))
print("Affected subjects:", eeg_long["subject"].nunique())
print("Affected recordings:", eeg_long["record"].nunique())

print("\nBy sleep stage:")
print(eeg_long["stage"].value_counts().to_string())

print("\nTop affected recordings:")
by_record = (
    eeg_long.groupby(["subject", "record"])
    .agg(
        n_epochs=("epoch_index", "count"),
        longest_plateau=("longest_plateau_samples", "max"),
        first_epoch=("epoch_index", "min"),
        last_epoch=("epoch_index", "max"),
    )
    .sort_values("n_epochs", ascending=False)
)

print(by_record.head(20).to_string())

eeg_long.to_csv(
    OUTPUT / "eeg_long_plateau_epochs.csv",
    index=False,
)
by_record.to_csv(
    OUTPUT / "eeg_long_plateaus_by_record.csv",
)

# Rate of long EEG plateaus within each sleep stage.
eeg = df[df["channel"] == "eeg"].copy()

eeg["long_plateau_200ms"] = (
    eeg["longest_plateau_samples"] >= 20
)

stage_summary = (
    eeg.groupby("stage")
    .agg(
        total_epochs=("epoch_index", "count"),
        flagged_epochs=("long_plateau_200ms", "sum"),
    )
)

stage_summary["flagged_pct"] = (
    100
    * stage_summary["flagged_epochs"]
    / stage_summary["total_epochs"]
)

print("\n=== LONG EEG PLATEAUS BY STAGE ===")
print(stage_summary.to_string())

stage_summary.to_csv(
    OUTPUT / "eeg_long_plateaus_by_stage.csv"
)

print("\nAnalysis complete.")
