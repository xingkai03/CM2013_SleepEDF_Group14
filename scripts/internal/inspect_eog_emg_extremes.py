from pathlib import Path
import sys

import numpy as np
import matplotlib.pyplot as plt
import mne
import glob

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sleepedf import SleepEDFTrack

CACHE = Path(
    r"G:\My Drive\CM2013\data_cache\sleep_edf\physionet-sleep-data"
)

OUTPUT = ROOT / "results" / "multichannel_audit_68" / "eog_emg_inspection"
OUTPUT.mkdir(parents=True, exist_ok=True)

SELECTED = {
    "SC4201E0": {
        "eog": [1043, 891],
        "emg": [2519, 1030],
    },
    "SC4372F0": {
        "eog": [1070, 35],
        "emg": [1886, 2599],
    },
    "SC4592G0": {
        "eog": [1262, 1413],
        "emg": [1525, 209],
    },
}

track = SleepEDFTrack()

for record, channels in SELECTED.items():
    psg = next(CACHE.rglob(f"{record}-PSG.edf"))

    rec = track.load(str(CACHE), psg_paths=[psg])[0]

    # Reproduce the loader's annotation-to-epoch alignment.
    raw = mne.io.read_raw_edf(
        psg, preload=False, verbose="ERROR"
    )
    hyp = str(psg).replace("-PSG.edf", "-Hypnogram.edf")

    if not Path(hyp).exists():
        candidates = glob.glob(str(psg)[:-10] + "*Hypnogram.edf")

        if not candidates:
            raise FileNotFoundError(
                f"No Hypnogram found for {psg.name}"
            )

        hyp = candidates[0]

    print(f"{record}: using {Path(hyp).name}")

    ann = mne.read_annotations(hyp)
    raw.set_annotations(ann, emit_warning=False)

    # Mapping from the CM2013 reference SleepEDF loader.
    RK_TO_AASM = {
        "Sleep stage W": "W",
        "Sleep stage 1": "N1",
        "Sleep stage 2": "N2",
        "Sleep stage 3": "N3",
        "Sleep stage 4": "N3",
        "Sleep stage R": "REM",
    }

    events, ev_id = mne.events_from_annotations(
        raw,
        event_id={k: i for i, k in enumerate(RK_TO_AASM)},
        chunk_duration=30.0,
        verbose="ERROR",
    )

    valid_ids = {
        i for k, i in ev_id.items()
        if RK_TO_AASM[k] is not None
    }

    onsets = []
    for event in events:
        if event[2] not in valid_ids:
            continue
        start = int(event[0])
        if start + 3000 <= raw.n_times:
            onsets.append(start)

    assert len(onsets) == len(rec.labels), (
        f"Epoch alignment mismatch for {record}"
    )

    # Load original 1 Hz EMG separately.
    raw_emg = mne.io.read_raw_edf(
        psg,
        include=["EMG submental"],
        preload=False,
        verbose="ERROR",
    )
    assert raw_emg.info["sfreq"] == 1.0

    for channel, indices in channels.items():
        for epoch_idx in indices:
            signal = np.asarray(
                rec.epochs[channel][epoch_idx]
            ) * 1e6

            fs = rec.fs
            t = np.arange(len(signal)) / fs
            std = np.std(signal)
            stage = rec.labels[epoch_idx]

            fig, ax = plt.subplots(figsize=(12, 4))

            ax.plot(t, signal, linewidth=0.8,
                    label=f"{channel.upper()} (loader)")

            if channel == "emg":
                # EEG event samples are at 100 Hz.
                # Convert the epoch onset to seconds, then to 1 Hz.
                start_seconds = onsets[epoch_idx] / fs
                start_original = round(
                    start_seconds * raw_emg.info["sfreq"]
                )

                original = raw_emg.get_data(
                    start=start_original,
                    stop=start_original + 30,
                )[0] * 1e6

                if len(original) == 30:
                    ax.scatter(
                        np.arange(30),
                        original,
                        s=15,
                        color="red",
                        label="Original EMG (1 Hz)",
                        zorder=3,
                    )

            ax.set(
                title=(
                    f"{record} | {channel.upper()} | "
                    f"Epoch {epoch_idx} | {stage} | "
                    f"STD={std:.3f} µV"
                ),
                xlabel="Time (s)",
                ylabel="Amplitude (µV)",
                xlim=(0, 30),
            )

            ax.grid(alpha=0.3)
            ax.legend()
            fig.tight_layout()

            path = OUTPUT / (
                f"{record}_{channel}_epoch_{epoch_idx}.png"
            )
            fig.savefig(path, dpi=150)
            plt.close(fig)

            print("Saved:", path)