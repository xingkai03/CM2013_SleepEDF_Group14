
from pathlib import Path
from datetime import datetime, timedelta, time
from collections import Counter

import mne
import numpy as np
import pandas as pd

from sleepedf.reference.sleep_edf import RK_TO_AASM

# ============================================================
# CONFIGURATION
# ============================================================

DATA_DIR = Path("sleep_edf_data/physionet-sleep-data")
SUBJECTS = {"SC400", "SC401", "SC402"}

EPOCH_S = 30.0

# Provisional clock-time window.
# Confirm EDF time interpretation with the instructor.
NIGHT_START = time(20, 30)
NIGHT_END = time(11, 0)

# ============================================================
# ANALYSIS
# ============================================================

rows = []
stage_rows = []

psg_files = sorted(
    p for p in DATA_DIR.glob("*PSG.edf")
    if p.name[:5] in SUBJECTS
)

print(f"Found {len(psg_files)} PSG files")

for psg in psg_files:

    # Match the hypnogram using the recording prefix.
    prefix = psg.name[:6]
    candidates = sorted(
        psg.parent.glob(f"{prefix}*Hypnogram.edf")
    )

    if len(candidates) != 1:
        raise ValueError(
            f"Expected one hypnogram for {psg.name}, "
            f"found {len(candidates)}"
        )

    hyp = candidates[0]

    raw = mne.io.read_raw_edf(
        str(psg),
        preload=False,
        verbose="ERROR"
    )

    ann = mne.read_annotations(str(hyp))

    # Reproduce the reference loader's annotation-to-epoch logic.
    raw.set_annotations(ann, emit_warning=False)

    events, ev_id = mne.events_from_annotations(
        raw,
        event_id={
            k: i for i, k in enumerate(RK_TO_AASM)
        },
        chunk_duration=EPOCH_S,
        verbose="ERROR"
    )

    id_to_stage = {
        i: RK_TO_AASM[k]
        for k, i in ev_id.items()
    }

    fs = raw.info["sfreq"]
    step = int(EPOCH_S * fs)

    record_start = raw.info["meas_date"]

    if record_start is None:
        raise ValueError(f"Missing start time: {psg.name}")

    # Candidate windows that could overlap the recording.
    record_end = record_start + timedelta(
        seconds=raw.n_times / fs
    )

    candidate_windows = []

    for day_offset in (-1, 0, 1):
        day = record_start.date() + timedelta(
            days=day_offset
        )

        window_start = datetime.combine(
            day, NIGHT_START, tzinfo=record_start.tzinfo
        )

        window_end = datetime.combine(
            day + timedelta(days=1),
            NIGHT_END,
            tzinfo=record_start.tzinfo
        )

        overlap = max(
            0.0,
            (
                min(record_end, window_end)
                - max(record_start, window_start)
            ).total_seconds()
        )

        if overlap > 0:
            candidate_windows.append(
                (overlap, window_start, window_end)
            )

    if not candidate_windows:
        raise ValueError(
            f"No night window overlaps {psg.name}"
        )

    # Select the night window with the greatest overlap.
    _, window_start, window_end = max(
        candidate_windows,
        key=lambda item: item[0]
    )

    all_labels = []
    kept_labels = []

    for event in events:

        stage = id_to_stage.get(event[2])

        if stage is None:
            continue

        onset_sample = int(event[0])

        if onset_sample + step > raw.n_times:
            continue

        epoch_start = record_start + timedelta(
            seconds=onset_sample / fs
        )

        epoch_end = epoch_start + timedelta(
            seconds=EPOCH_S
        )

        all_labels.append(stage)

        # Keep only complete epochs inside the clock window.
        if (
            epoch_start >= window_start
            and epoch_end <= window_end
        ):
            kept_labels.append(stage)

    before = Counter(all_labels)
    after = Counter(kept_labels)

    record_id = psg.name.split("-")[0]

    rows.append({
        "record": record_id,
        "subject": psg.name[:5],
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "epochs_before": len(all_labels),
        "epochs_after": len(kept_labels),
        "epochs_removed": len(all_labels) - len(kept_labels),
        "wake_before": before.get("W", 0),
        "wake_after": after.get("W", 0),
    })

    for stage in sorted(set(before) | set(after)):
        stage_rows.append({
            "record": record_id,
            "stage": stage,
            "before": before[stage],
            "after": after[stage],
        })

# ============================================================
# OUTPUT
# ============================================================

df = pd.DataFrame(rows)
stages = pd.DataFrame(stage_rows)

print("\nPER RECORD")
print(df.to_string(index=False))

print("\nTOTALS")
print(
    df[
        [
            "epochs_before",
            "epochs_after",
            "epochs_removed",
            "wake_before",
            "wake_after",
        ]
    ].sum()
)

print("\nSTAGE DISTRIBUTION")
summary = stages.groupby("stage")[
    ["before", "after"]
].sum()

summary["before_pct"] = (
    100 * summary["before"] / summary["before"].sum()
)

summary["after_pct"] = (
    100 * summary["after"] / summary["after"].sum()
)

print(summary.round(2))

output_dir = Path("results/clock_cropping")
output_dir.mkdir(parents=True, exist_ok=True)

df.to_csv(
    output_dir / "cropping_by_record.csv",
    index=False
)

summary.to_csv(
    output_dir / "stage_distribution.csv"
)

print(f"\nSaved results to {output_dir}")
