
from pathlib import Path
import numpy as np

from sleepedf import SleepEDFTrack

CACHE = Path(
    r"G:\My Drive\CM2013\data_cache\sleep_edf\physionet-sleep-data"
)

psg = sorted(CACHE.rglob("*-PSG.edf"))[0]

track = SleepEDFTrack()

raw = track.load(
    str(CACHE),
    psg_paths=[psg],
    continuous_eeg_bandpass=False,
)[0]

continuous = track.load(
    str(CACHE),
    psg_paths=[psg],
    continuous_eeg_bandpass=True,
)[0]

assert raw.group == continuous.group
assert raw.meta["record"] == continuous.meta["record"]
assert raw.fs == continuous.fs
assert np.array_equal(raw.labels, continuous.labels)

for channel in ("eeg", "eog", "emg"):
    assert raw.epochs[channel].shape == continuous.epochs[channel].shape

for channel in ("eog", "emg"):
    assert np.array_equal(
        raw.epochs[channel],
        continuous.epochs[channel],
    )

assert np.isfinite(continuous.epochs["eeg"]).all()

assert not np.array_equal(
    raw.epochs["eeg"],
    continuous.epochs["eeg"],
)

# Check that P1d does not filter the EEG a second time.
cfg = {"preprocess": "p1d"}
processed = track.preprocess(continuous, cfg)

assert np.array_equal(
    processed.epochs["eeg"],
    continuous.epochs["eeg"],
)

print("P1d alignment checks passed.")
print("Recording:", raw.meta["record"])
print("Epochs:", len(raw.labels))
print("Sampling rate:", raw.fs)
print("EOG and EMG unchanged.")
print("EEG filtered continuously, without double filtering.")
