from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from sleepedf import SleepEDFTrack

CACHE = Path(
    r"G:\My Drive\CM2013\data_cache\sleep_edf\physionet-sleep-data"
)

OUTPUT = ROOT / "results" / "multichannel_audit_68" / "final_inspection"
OUTPUT.mkdir(parents=True, exist_ok=True)

RECORD = "SC4372F0"
EPOCHS = [35, 2599]

track = SleepEDFTrack()
psg = next(CACHE.rglob(f"{RECORD}-PSG.edf"))
rec = track.load(str(CACHE), psg_paths=[psg])[0]

for epoch_idx in EPOCHS:
    fig, axes = plt.subplots(
        3, 1, figsize=(14, 9), sharex=True
    )

    for ax, channel in zip(axes, ["eeg", "eog", "emg"]):
        signal = (
            np.asarray(rec.epochs[channel][epoch_idx]) * 1e6
        )
        t = np.arange(len(signal)) / rec.fs

        ax.plot(t, signal, linewidth=0.8)
        ax.set_ylabel(f"{channel.upper()} (µV)")
        ax.grid(alpha=0.3)

        ax.text(
            0.99, 0.95,
            f"STD = {np.std(signal):.3f} µV",
            transform=ax.transAxes,
            ha="right", va="top",
        )

    axes[-1].set_xlabel("Time (s)")
    axes[-1].set_xlim(0, 30)

    fig.suptitle(
        f"{RECORD} | Epoch {epoch_idx} | "
        f"Stage: {rec.labels[epoch_idx]}",
        fontsize=14,
    )

    fig.tight_layout()

    path = OUTPUT / f"{RECORD}_epoch_{epoch_idx}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)

    print("Saved:", path)