"""Signal-based checks for the seven experimental features (no EDFs needed)."""
import importlib.util
from pathlib import Path
import sys
import unittest
import warnings

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
spec = importlib.util.spec_from_file_location("experimental_features", ROOT / "tests/test_features2.py")
prototype = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prototype
spec.loader.exec_module(prototype)

from sleepedf.reference.adapter import Recording


def recording(eeg, emg=None, fs=100):
    eeg = np.atleast_2d(eeg)
    emg = eeg.copy() if emg is None else np.atleast_2d(emg)
    return Recording("synthetic", fs, {"eeg": eeg, "emg": emg}, np.repeat("W", len(eeg)))


class AdditionalFeatureTests(unittest.TestCase):
    def setUp(self):
        self.t = np.arange(3000) / 100
        self.extractor = prototype.AdvancedSleepFeatures()

    def test_known_band_power_ratios_and_spectral_edge(self):
        # Squared amplitudes 1 and 0.25 imply power fractions 0.8 and 0.2.
        eeg = 1e-6 * (np.sin(2*np.pi*2*self.t) + 0.5*np.sin(2*np.pi*13*self.t))
        feats = self.extractor.extract(recording(eeg))
        self.assertAlmostEqual(feats["eeg_rel_delta"][0], 0.8, places=10)
        self.assertAlmostEqual(feats["eeg_rel_sigma"][0], 0.2, places=10)
        self.assertEqual(feats["eeg_sef_95"][0], 13.0)

    def test_relative_features_do_not_depend_on_volts_or_microvolts(self):
        eeg = np.sin(2*np.pi*13*self.t) + 0.3*np.sin(2*np.pi*2*self.t)
        high = self.extractor.extract(recording(eeg))
        low = self.extractor.extract(recording(eeg * 1e-9))
        for name in ("eeg_rel_delta", "eeg_rel_sigma", "eeg_sef_95", "eeg_dwt_d2_energy"):
            with self.subTest(name=name):
                np.testing.assert_allclose(high[name], low[name], rtol=1e-10, atol=1e-12)

    def test_emg_median_detects_a_known_tone_in_volts(self):
        feats = self.extractor.extract(recording(np.sin(2*np.pi*2*self.t),
                                                 1e-6*np.sin(2*np.pi*20*self.t)))
        self.assertEqual(feats["emg_median_freq"][0], 20.0)

    def test_flat_signals_have_zero_features_instead_of_spurious_frequencies(self):
        feats = self.extractor.extract(recording(np.zeros(3000)))
        for name, values in feats.items():
            with self.subTest(name=name):
                np.testing.assert_array_equal(values, [0.0])

    def test_zero_crossings_ignore_runs_of_exact_zeros(self):
        # A 25 Hz sine at 100 Hz, with exact zeros, has 1499 sign changes.
        eeg = np.tile([0.0, 1.0, 0.0, -1.0], 750)
        feats = self.extractor.extract(recording(eeg))
        self.assertAlmostEqual(feats["eeg_zcr"][0], 1499/2999)

    def test_wavelet_detail_energy_distinguishes_low_and_high_tones(self):
        eeg = np.stack([np.sin(2*np.pi*2*self.t), np.sin(2*np.pi*20*self.t)]) * 1e-6
        values = self.extractor.extract(recording(eeg))["eeg_dwt_d2_energy"]
        self.assertLess(values[0], 0.01)
        self.assertGreater(values[1], 0.5)

    def test_waveform_length_scales_with_amplitude(self):
        eeg = np.sin(2*np.pi*2*self.t)
        values = self.extractor.extract(recording(np.stack([eeg, 3*eeg])))["emg_wl"]
        self.assertAlmostEqual(values[1]/values[0], 3.0)

    def test_low_rate_or_known_envelope_skips_emg_spectrum(self):
        eeg = np.sin(2*np.pi*2*self.t)
        for extractor, emg in ((self.extractor, np.ones(30)),
                               (prototype.AdvancedSleepFeatures(emg_is_envelope=True), eeg)):
            with self.subTest(shape=emg.shape), warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                feats = extractor.extract(recording(eeg, emg))
                self.assertNotIn("emg_median_freq", feats)
                self.assertEqual(len(feats), 6)
                self.assertTrue(caught)

    def test_native_emg_rate_overrides_resampled_array_rate(self):
        eeg = np.sin(2*np.pi*2*self.t)
        extractor = prototype.AdvancedSleepFeatures(emg_native_fs=1.0)
        with self.assertWarnsRegex(UserWarning, "native/inferred fs=1.0"):
            feats = extractor.extract(recording(eeg))
        self.assertEqual(extractor.to_matrix(feats).shape, (1, 6))

    def test_all_seven_are_finite_aligned_and_do_not_modify_input(self):
        rng = np.random.default_rng(4)
        rec = recording(rng.normal(size=(3, 3000))*1e-6)
        before = rec.epochs["eeg"].copy()
        feats = self.extractor.extract(rec)
        matrix = self.extractor.to_matrix(feats)
        self.assertEqual(matrix.shape, (3, 7))
        self.assertTrue(np.isfinite(matrix).all())
        np.testing.assert_array_equal(rec.epochs["eeg"], before)

    def test_non_finite_samples_fail_clearly(self):
        eeg = np.ones(3000)
        eeg[10] = np.nan
        with self.assertRaisesRegex(ValueError, "finite"):
            self.extractor.extract(recording(eeg))

    def test_empty_batch_keeps_feature_width(self):
        feats = self.extractor.extract(recording(np.empty((0, 3000))))
        self.assertEqual(self.extractor.to_matrix(feats).shape, (0, 7))


if __name__ == "__main__":
    unittest.main()
