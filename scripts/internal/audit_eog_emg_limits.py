from pathlib import Path
import csv
import numpy as np
import mne

ROOT = Path(__file__).resolve().parents[2]

CACHE = Path(
    r"G:\My Drive\CM2013\data_cache\sleep_edf\physionet-sleep-data"
)

OUTPUT = (
    ROOT / "results" / "eeg_clipping_68"
    / "eog_emg_recording_audit.csv"
)

HOLDOUT = {f"SC{x:03d}" for x in range(408, 481, 8)}

CHANNELS = {
    "EOG horizontal": "eog",
    "EMG submental": "emg",
}


def read_limits(psg):
    with open(psg, "rb") as f:
        header = f.read(256)
        ns = int(header[252:256].decode("ascii").strip())
        data = f.read(ns * 256)

    def field(offset, width):
        start = offset * ns
        return [
            data[start + i * width:start + (i + 1) * width]
            .decode("ascii").strip()
            for i in range(ns)
        ]

    labels = field(0, 16)
    pmin = field(104, 8)
    pmax = field(112, 8)

    return {
        label: (float(pmin[i]), float(pmax[i]))
        for i, label in enumerate(labels)
    }


def main():
    psgs = sorted(CACHE.rglob("SC*-PSG.edf"))
    psgs = [
        p for p in psgs
        if p.name[:5] not in HOLDOUT
    ]

    subjects = {p.name[:5] for p in psgs}

    assert len(psgs) == 133
    assert len(subjects) == 68

    rows = []

    for i, psg in enumerate(psgs, start=1):
        record = psg.name.replace("-PSG.edf", "")
        limits = read_limits(psg)

        for channel, short_name in CHANNELS.items():
            raw = mne.io.read_raw_edf(
                psg,
                include=[channel],
                preload=False,
                verbose="ERROR",
            )

            fs = float(raw.info["sfreq"])
            x = raw.get_data()[0] * 1e6

            physical_min, physical_max = limits[channel]

            # Values converted from EDF digital boundaries.
            # Small tolerance for floating-point representation.
            at_min = np.isclose(
                x, physical_min, rtol=0, atol=1e-6
            )
            at_max = np.isclose(
                x, physical_max, rtol=0, atol=1e-6
            )

            rows.append({
                "subject": record[:5],
                "record": record,
                "channel": short_name,
                "fs_original": fs,
                "physical_min_uv": physical_min,
                "physical_max_uv": physical_max,
                "observed_min_uv": float(x.min()),
                "observed_max_uv": float(x.max()),
                "samples_at_lower_limit": int(at_min.sum()),
                "samples_at_upper_limit": int(at_max.sum()),
                "total_samples": len(x),
            })

            del raw, x

        print(f"[{i}/{len(psgs)}] {record}", flush=True)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=rows[0].keys()
        )
        writer.writeheader()
        writer.writerows(rows)

    print("\nSaved:", OUTPUT)

    for channel in ["eog", "emg"]:
        selected = [
            r for r in rows if r["channel"] == channel
        ]

        affected = [
            r for r in selected
            if r["samples_at_lower_limit"]
            + r["samples_at_upper_limit"] > 0
        ]

        total_boundary_samples = sum(
            r["samples_at_lower_limit"]
            + r["samples_at_upper_limit"]
            for r in selected
        )

        print(f"\n{channel.upper()}")
        print("Records analyzed:", len(selected))
        print("Records reaching EDF limits:", len(affected))
        print("Samples at EDF limits:", total_boundary_samples)


if __name__ == "__main__":
    main()