# %% [markdown]
# ## Sleep-EDF Feature Verification Script

# %%
from pathlib import Path
import numpy as np
import pandas as pd

from sleepedf import SleepEDFTrack
from run_baseline import build_parser, select_psgs

# Set paths relative to your project root
ROOT = Path(__file__).resolve().parents[1] if "__file__" in locals() else Path.cwd()
cache_dir = ROOT / "sleep_edf_data"

# Find PSG EDF files under cache directory (matching run_baseline.py)
psgs = sorted(cache_dir.rglob("*-PSG.edf"))

if not psgs:
    raise FileNotFoundError(f"No PSG EDF files found under {cache_dir.resolve()}")

# Select a 3-subject test subset (Night 1)
selected_psgs = select_psgs(psgs, n_subjects=3, nights=[1])

track = SleepEDFTrack()
print(f"Loading {len(selected_psgs)} PSG files...")
recs = track.load(str(cache_dir), psg_paths=selected_psgs)

# Build baseline dataset
cfg = {"preprocess": "none", "spectral_method": "welch", "select": "none"}
X, y, groups = track.build_dataset(recs, cfg)

# %% 1. Confirm 11 Column Names and Order
feature_names = track.feature_names()

print("--- Check 1: Feature Names & Ordering ---")
print(f"Number of features: {len(feature_names)}")
for i, name in enumerate(feature_names):
    print(f"  Col {i:2d}: {name}")

assert len(feature_names) == 11, f"Expected 11 features, found {len(feature_names)}"
assert X.shape[1] == 11, f"Expected X to have 11 columns, found {X.shape[1]}"

# %% 2. Verify Row Alignment and Lengths
print("\n--- Check 2: Row Alignment ---")
print(f"X shape:      {X.shape}")
print(f"y shape:      {y.shape}")
print(f"groups shape: {groups.shape}")

assert X.shape[0] == len(y), f"Row mismatch: X has {X.shape[0]}, y has {len(y)}"
assert len(groups) == len(y), f"Group mismatch: groups has {len(groups)}, y has {len(y)}"

# Verify epoch counts per subject match recording labels
for rec in recs:
    rec_epochs = len(rec.labels)
    subj_epochs = np.sum(groups == rec.group)
    print(f"Subject {rec.group} ({rec.meta['record']}): {rec_epochs} labels == {subj_epochs} rows in X")

# %% 3. Check for NaN / Infinite Values & Summary Statistics
print("\n--- Check 3: Data Integrity (NaNs / Infs) ---")
has_nan = np.isnan(X).any()
has_inf = np.isinf(X).any()

print(f"Contains NaNs:     {has_nan}")
print(f"Contains Infs:     {has_inf}")
print(f"All values finite: {np.isfinite(X).all()}")

assert not has_nan, "Data contains NaN values!"
assert not has_inf, "Data contains infinite values!"

# Summary statistics table
df_summary = pd.DataFrame(X, columns=feature_names)
print("\nFeature summary statistics:")
print(df_summary.describe().T[["mean", "std", "min", "50%", "max"]])


import matplotlib.pyplot as plt
import seaborn as sns

# Extract features
extractor = BaselineFeatureExtractor()
X, y, group = extractor.transform(recording)

# Plot heatmap of features across time
plt.figure(figsize=(12, 6))
sns.heatmap(X.T, yticklabels=extractor.feature_names(), cmap="viridis")
plt.xlabel("Epoch Index (Time)")
plt.ylabel("Extracted Features")
plt.title("Feature Matrix Across Sleep Epochs")
plt.show()