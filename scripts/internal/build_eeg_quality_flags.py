from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "eeg_clipping_68"

clipping = pd.read_csv(RESULTS / "clipping_epochs.csv")
limits = pd.read_csv(RESULTS / "edf_limits_check.csv")

# Add recording-level EDF limit information.
qc = clipping.merge(
    limits[
        ["record", "min_matches", "max_matches"]
    ],
    on="record",
    how="left",
    validate="many_to_one",
)

assert len(qc) == len(clipping)
assert not qc[["min_matches", "max_matches"]].isna().any().any()

# Retain only plateau samples at verified EDF boundaries.
qc["edf_clipped_samples"] = (
    qc["negative_samples"] * qc["min_matches"].astype(int)
    + qc["positive_samples"] * qc["max_matches"].astype(int)
)

qc["edf_clipping_flag"] = (
    qc["edf_clipped_samples"] > 0
).astype(int)

# This equality was established in our previous audit.
assert (
    qc["edf_clipped_samples"] == qc["clipped_samples"]
).all()

assert (
    qc["edf_clipping_flag"] == qc["suspected_clipping"]
).all()

qc["edf_limit_reached"] = (
    qc["min_matches"] | qc["max_matches"]
).astype(int)

# Descriptive categories, not validated clinical thresholds.
def severity(pct):
    if pct == 0:
        return "none"
    if pct <= 1:
        return "low"
    if pct <= 5:
        return "moderate"
    if pct <= 10:
        return "high"
    return "very_high"

qc["clipping_severity"] = qc["clipped_pct"].apply(severity)

columns = [
    "subject",
    "record",
    "epoch_index",
    "stage",
    "edf_clipping_flag",
    "edf_clipped_samples",
    "clipped_pct",
    "longest_clipping_ms",
    "clipping_severity",
    "edf_limit_reached",
]

output = RESULTS / "eeg_quality_flags.csv"
qc[columns].to_csv(output, index=False)

print("Saved:", output)
print("Total epochs:", len(qc))
print("Flagged epochs:", int(qc["edf_clipping_flag"].sum()))
print("\nSeverity distribution:")
print(qc["clipping_severity"].value_counts())