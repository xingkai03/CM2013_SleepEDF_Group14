
"""Attach clock timestamps to Sleep-EDF recordings without changing epochs."""

from pathlib import Path

import mne
import numpy as np

from ..reference.adapter import Recording
from ..reference.sleep_edf import RK_TO_AASM


def attach_epoch_timestamps(
    recording: Recording,
    psg_path: str | Path,
    hypnogram_path: str | Path,
    epoch_s: float = 30.0,
) -> Recording:
    """Enrich a Recording with timestamps aligned to its original epochs."""

    psg_path = Path(psg_path)
    hypnogram_path = Path(hypnogram_path)

    raw = mne.io.read_raw_edf(
        str(psg_path), preload=False, verbose="ERROR"
    )

    annotations = mne.read_annotations(str(hypnogram_path))
    raw.set_annotations(annotations, emit_warning=False)

    # Reproduce the reference loader's sampling rate.
    if abs(raw.info["sfreq"] - recording.fs) > 1e-6:
        raw.resample(recording.fs, verbose="ERROR")

    fs = float(raw.info["sfreq"])
    step = int(epoch_s * fs)

    events, event_id = mne.events_from_annotations(
        raw,
        event_id={k: i for i, k in enumerate(RK_TO_AASM)},
        chunk_duration=epoch_s,
        verbose="ERROR",
    )

    id_to_stage = {
        i: RK_TO_AASM[k]
        for k, i in event_id.items()
    }

    onsets_samples = []
    selected_labels = []

    for event in events:
        stage = id_to_stage.get(event[2])

        if stage is None:
            continue

        onset = int(event[0])
        relative_onset = onset - raw.first_samp

        # Same full-length condition as the reference loader.
        if relative_onset < 0:
            continue

        if relative_onset + step > raw.n_times:
            continue

        onsets_samples.append(relative_onset)
        selected_labels.append(stage)

    onsets_samples = np.asarray(onsets_samples, dtype=np.int64)
    selected_labels = np.asarray(selected_labels)

    # Validate alignment with the already loaded recording.
    if len(onsets_samples) != len(recording.labels):
        raise ValueError(
            f"Epoch count mismatch for {recording.meta['record']}: "
            f"timestamps={len(onsets_samples)}, "
            f"loaded={len(recording.labels)}"
        )

    if not np.array_equal(selected_labels, recording.labels):
        raise ValueError(
            f"Stage alignment mismatch for {recording.meta['record']}"
        )

    recording_start = raw.info["meas_date"]

    if recording_start is None:
        raise ValueError(
            f"Missing PSG recording start time: {psg_path.name}"
        )

    meta = dict(recording.meta)

    meta["recording_start"] = recording_start.isoformat()
    meta["epoch_onsets_seconds"] = (
        onsets_samples / fs
    ).tolist()
    meta["original_epoch_indices"] = list(range(len(onsets_samples)))
    meta["timestamp_source"] = "PSG EDF measurement date + MNE events"

    return Recording(
        group=recording.group,
        fs=recording.fs,
        epochs=recording.epochs,
        labels=recording.labels,
        meta=meta,
    )
