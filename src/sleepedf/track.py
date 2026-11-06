from .feature_extraction import BaselineFeatureExtractor
from .machine_learning import default_baseline
from .preprocessing import (
    make_preprocessor,
    BrokenSegmentHandling,
    TargetedDenoising,
)
from .reference.adapter import SPECTRAL_CFG_KEYS
from .reference.sleep_edf import SleepEDFTrack as ReferenceSleepEDFTrack


class SleepEDFTrack(ReferenceSleepEDFTrack):
    """Sleep-EDF pipeline with optional quality control."""

    SUPPORTED_CFG_KEYS = SPECTRAL_CFG_KEYS | {
        "preprocess",
        "quality_control",
        "wavelet",
    }

    def preprocess(self, rec, cfg=None):
        cfg = self._cfg(cfg)

        if cfg.get("quality_control", False):
            rec = BrokenSegmentHandling(action="flag").transform(rec)
            rec = TargetedDenoising(
                noise_type="clipping",
                min_plateau_samples=3,
            ).transform(rec)
        if cfg["preprocess"] == "p1d":
            if not rec.meta.get("continuous_eeg_bandpass", False):
                raise ValueError(
                    "P1d requires continuous EEG filtering during loading."
                )

            return rec
        preprocessor = make_preprocessor(cfg["preprocess"])

        if cfg["preprocess"] in ("wavelet", "bandpass_wavelet"):
            preprocessor.wavelet = cfg.get("wavelet", "db4")

        return preprocessor.transform(rec)

    def extract_features(self, rec, cfg=None):
        return BaselineFeatureExtractor().transform(rec, self._cfg(cfg))

    def feature_names(self, cfg=None):
        return BaselineFeatureExtractor().feature_names()

    def baseline(self, cfg=None):
        cfg = self._cfg(cfg)
        return default_baseline(
            seed=int(cfg["seed"]),
            imbalance=cfg["imbalance"],
            threshold=float(cfg["threshold"]),
            smote_k=int(cfg["smote_k"]),
        )