"""Preprocessing experiments P0–P5; only P0 is implemented."""
from .base import NoPreprocessing, Preprocessor
from .experiments import (
    BrokenSegmentHandling,
    EEGBandpass,
    SubjectRecordingNormalisation,
    TargetedDenoising,
    WaveletDenoising,
    ClockBasedCropping,
    BandpassWavelet,
)


def make_preprocessor(name="none") -> Preprocessor:
    """Select the preprocessing transform. Planned experiments fail when called."""

    key = str(name or "none").lower()

    if key in ("broken_segments", "p3"):
        return BrokenSegmentHandling(action="exclude")
    if key in ("clock_cropping", "p6"):
        return ClockBasedCropping()
    if key in ("p1b", "bandpass_35_order4"):
        return EEGBandpass(
            low_hz=0.5,
            high_hz=35.0,
            order=4,
        )
    if key in ("p1c", "bandpass_35_order5"):
        return EEGBandpass(
            low_hz=0.5,
            high_hz=35.0,
            order=5,
        )

    choices = {
        "none": NoPreprocessing,
        "p0": NoPreprocessing,
        "bandpass": EEGBandpass,
        "p1": EEGBandpass,
        "wavelet": WaveletDenoising,
        "p2": WaveletDenoising,
        "normalisation": SubjectRecordingNormalisation,
        "p4": SubjectRecordingNormalisation,
        "denoise_clipping": TargetedDenoising,
        "p5": TargetedDenoising,
        "p6": ClockBasedCropping,
        "bandpass_wavelet": BandpassWavelet,
    }

    if key not in choices:
        raise ValueError(
            f"Unknown preprocessing experiment: {name!r}"
        )

    return choices[key]()