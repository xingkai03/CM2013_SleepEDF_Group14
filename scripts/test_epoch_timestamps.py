
"""Validate epoch timestamps and P6 clock-based cropping on six Sleep-EDF nights."""

from pathlib import Path
import sys

import numpy as np

# Make the src/ directory importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sleepedf.track import SleepEDFTrack
from sleepedf.preprocessing.epoch_timestamps import attach_epoch_timestamps
from sleepedf.preprocessing.experiments import ClockBasedCropping, EEGBandpass


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

cache = ROOT / "sleep_edf_data"

record_ids = [
    "SC4001E0",
    "SC4002E0",
    "SC4011E0",
    "SC4012E0",
    "SC4021E0",
    "SC4022E0",
]

expected_nighttime_epochs = {
    "SC4001E0": 1740,
    "SC4002E0": 1739,
    "SC4011E0": 1740,
    "SC4012E0": 1740,
    "SC4021E0": 1740,
    "SC4022E0": 1739,
}

track = SleepEDFTrack()

cropper = ClockBasedCropping(
    start_time="20:30",
    end_time="11:00",
    action="flag",
)

total_epochs = 0
total_selected = 0


# --------------------------------------------------
# 2. Process each recording
# --------------------------------------------------

for record_id in record_ids:

    print(f"\n--- {record_id} ---")

    # Find the PSG file
    psg_candidates = sorted(
        cache.rglob(f"{record_id}-PSG.edf")
    )

    assert len(psg_candidates) == 1, (
        f"Expected exactly one PSG for {record_id}, "
        f"found {len(psg_candidates)}"
    )

    psg = psg_candidates[0]

    # Find the corresponding hypnogram
    hyp_candidates = sorted(
        psg.parent.glob(
            f"{record_id[:6]}*-Hypnogram.edf"
        )
    )

    assert len(hyp_candidates) == 1, (
        f"Expected exactly one hypnogram for {record_id}, "
        f"found {len(hyp_candidates)}"
    )

    hyp = hyp_candidates[0]

    # Load the original recording
    recording = track.load(
        str(cache),
        psg_paths=[psg],
    )[0]

    # --------------------------------------------------
    # 3. Attach temporal metadata
    # --------------------------------------------------

    enriched = attach_epoch_timestamps(
        recording,
        psg,
        hyp,
    )

    onsets = np.asarray(
        enriched.meta["epoch_onsets_seconds"],
        dtype=float,
    )

    assert len(onsets) == len(recording.labels)

    np.testing.assert_array_equal(
        enriched.labels,
        recording.labels,
    )

    assert np.all(np.diff(onsets) > 0)

    total_epochs += len(onsets)

    print(
        f"Recording start: "
        f"{enriched.meta['recording_start']}"
    )

    print(f"Total epochs: {len(onsets)}")
    print("Timestamp alignment: OK")

    # --------------------------------------------------
    # 4. Apply P6 clock-based detection
    # --------------------------------------------------

    mask = cropper.detect(enriched)

    assert mask.dtype == bool
    assert len(mask) == len(enriched.labels)

    # --------------------------------------------------
    # 5. Apply P6 transform
    # --------------------------------------------------

    transformed = cropper.transform(enriched)

    assert len(transformed.labels) == len(enriched.labels)

    np.testing.assert_array_equal(
        transformed.labels,
        enriched.labels,
    )

    np.testing.assert_array_equal(
        transformed.meta["nighttime_epoch_mask"],
        mask,
    )

    assert (
        transformed.meta["clock_cropping"]["epochs_selected"]
        == int(mask.sum())
    )

    print("P6 transform: OK")

    # --------------------------------------------------
    # 6. Verify P6 filtering is identical to P1
    # --------------------------------------------------

    p1_transformed = EEGBandpass().transform(enriched)

    for channel in ("eeg", "eog", "emg"):

        # Verify epoch dimensions are preserved
        assert (
            transformed.epochs[channel].shape
            == enriched.epochs[channel].shape
        )

        # Verify P6 and P1 signals are identical
        np.testing.assert_allclose(
            transformed.epochs[channel],
            p1_transformed.epochs[channel],
            rtol=0,
            atol=0,
        )

    print("P6 filtering identical to P1: OK")
    print("Epoch dimensions preserved: OK")

    # --------------------------------------------------
    # 7. Validate cropping counts
    # --------------------------------------------------

    selected = int(mask.sum())
    removed = len(mask) - selected

    total_selected += selected

    print(f"Nighttime epochs: {selected}")
    print(f"Excluded epochs: {removed}")

    expected = expected_nighttime_epochs[record_id]

    assert selected == expected, (
        f"Unexpected nighttime count for {record_id}: "
        f"expected {expected}, got {selected}"
    )

    print("P6 cropping count: OK")


# --------------------------------------------------
# 8. Final validation
# --------------------------------------------------

print("\n====================================")
print("FINAL VALIDATION")
print("====================================")

print(f"Total original epochs: {total_epochs}")
print(f"Total nighttime epochs: {total_selected}")
print(f"Total excluded epochs: {total_epochs - total_selected}")

print(
    f"Percentage retained: "
    f"{100 * total_selected / total_epochs:.2f}%"
)

assert total_epochs == 16688, (
    f"Expected 16688 original epochs, got {total_epochs}"
)

assert total_selected == 10438, (
    f"Expected 10438 nighttime epochs, got {total_selected}"
)

print("\nAll six recordings validated.")
print("P6 clock-based cropping test PASSED.")
