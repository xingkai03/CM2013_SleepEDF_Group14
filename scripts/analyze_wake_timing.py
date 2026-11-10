from pathlib import Path
import numpy as np
import pandas as pd
import mne

from sleepedf.reference.sleep_edf import RK_TO_AASM

DATA_DIR = Path("sleep_edf_data")
EPOCH_S = 30.0

SUBJECTS = {"SC400", "SC401", "SC402"}

rows = []

psg_files = sorted(DATA_DIR.rglob("*PSG.edf"))

psg_files = [
    psg for psg in psg_files
    if psg.name[:5] in SUBJECTS
]

print(f"Found {len(psg_files)} PSG files for selected subjects")

for psg in psg_files:
    # Match PSG and hypnogram using the recording prefix.
    # Example: SC4001E0-PSG.edf -> SC4001EC-Hypnogram.edf

    record_prefix = psg.name[:6]

    hyp_candidates = sorted(
        psg.parent.glob(f"{record_prefix}*Hypnogram.edf")
    )

    if len(hyp_candidates) != 1:
        raise ValueError(
            f"Expected exactly one hypnogram for {psg.name}, "
            f"found {len(hyp_candidates)}: {hyp_candidates}"
        )

    hyp = hyp_candidates[0]

    print(f"Processing {psg.name} with {hyp.name}")

    raw = mne.io.read_raw_edf(
        str(psg), preload=False, verbose="ERROR"
    )
    raw.set_annotations(
        mne.read_annotations(str(hyp)),
        emit_warning=False
    )

    events, ev_id = mne.events_from_annotations(
        raw,
        event_id={k: i for i, k in enumerate(RK_TO_AASM)},
        chunk_duration=EPOCH_S,
        verbose="ERROR"
    )

    id_to_stage = {
        i: RK_TO_AASM[k]
        for k, i in ev_id.items()
    }

    # Reproduce the loader's full-length epoch condition.
    step = int(EPOCH_S * raw.info["sfreq"])
    labels = [
        id_to_stage[e[2]]
        for e in events
        if id_to_stage.get(e[2]) is not None
        and e[0] + step <= raw.n_times
    ]

    labels = np.asarray(labels)

    if len(labels) == 0 or not np.any(labels != "W"):
        continue

    sleep_indices = np.flatnonzero(labels != "W")
    first_sleep = sleep_indices[0]
    last_sleep = sleep_indices[-1]

    pre_w = np.sum(labels[:first_sleep] == "W")
    intra_w = np.sum(
        labels[first_sleep:last_sleep + 1] == "W"
    )
    post_w = np.sum(labels[last_sleep + 1:] == "W")

    rows.append({
        "record": psg.name.split("-")[0],
        "subject": psg.name[:5],
        "total_epochs": len(labels),
        "total_w": int(np.sum(labels == "W")),
        "pre_sleep_w": int(pre_w),
        "intra_sleep_w": int(intra_w),
        "post_sleep_w": int(post_w),
        "pre_sleep_minutes": pre_w * EPOCH_S / 60,
        "post_sleep_minutes": post_w * EPOCH_S / 60,
    })

df = pd.DataFrame(rows)

print(df.to_string(index=False))
print("\nTOTALS")
print(
    df[
        ["total_epochs", "total_w", "pre_sleep_w",
         "intra_sleep_w", "post_sleep_w"]
    ].sum()
)

output = Path("results/wake_timing")
output.mkdir(parents=True, exist_ok=True)

df.to_csv(output / "wake_timing_by_night.csv", index=False)