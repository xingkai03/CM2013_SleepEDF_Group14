import numpy as np
from scipy.signal import welch
import pywt

def compute_additional_features(eeg_epoch, emg_epoch, fs=100):
    """
    Computes 7 additional features for a given 30-second epoch.
    Expects 1D numpy arrays for EEG and EMG.
    """
    features = {}
    
    # --- Frequency Domain: EEG Welch PSD ---
    # Using a Hann window as the standard default for EEG spectral estimation
    freqs, psd = welch(eeg_epoch, fs=fs, window='hann', nperseg=fs*2)
    total_power = np.sum(psd)
    
    # 1 & 2. Relative Band Powers (Delta: 0.5-4 Hz, Sigma: 11-16 Hz)
    delta_mask = (freqs >= 0.5) & (freqs < 4)
    sigma_mask = (freqs >= 11) & (freqs < 16)
    
    features['eeg_rel_delta'] = np.sum(psd[delta_mask]) / total_power if total_power > 0 else 0
    features['eeg_rel_sigma'] = np.sum(psd[sigma_mask]) / total_power if total_power > 0 else 0
    
    # 3. Spectral Edge Frequency (95%)
    if total_power > 0:
        cumulative_power = np.cumsum(psd)
        edge_idx = np.where(cumulative_power >= 0.95 * total_power)[0]
        features['eeg_sef_95'] = freqs[edge_idx[0]] if len(edge_idx) > 0 else 0
    else:
        features['eeg_sef_95'] = 0

    # 4. EEG Zero-Crossing Rate (Time Domain)
    mean_centered_eeg = eeg_epoch - np.mean(eeg_epoch)
    features['eeg_zcr'] = np.sum(np.diff(np.sign(mean_centered_eeg)) != 0) / len(eeg_epoch)

    # 5. EMG Waveform Length (Time Domain)
    features['emg_wl'] = np.sum(np.abs(np.diff(emg_epoch)))

    # 6. EMG Median Frequency (Frequency Domain)
    emg_freqs, emg_psd = welch(emg_epoch, fs=fs, window='hann', nperseg=fs*2)
    emg_total_power = np.sum(emg_psd)
    
    if emg_total_power > 0:
        emg_cum_power = np.cumsum(emg_psd)
        med_idx = np.where(emg_cum_power >= 0.50 * emg_total_power)[0]
        features['emg_median_freq'] = emg_freqs[med_idx[0]] if len(med_idx) > 0 else 0
    else:
        features['emg_median_freq'] = 0

    # 7. Wavelet Detail 2 Energy (Time-Frequency Domain)
    # Using 'db4' wavelet, standard for transients like K-complexes and spindles
    # For fs=100, level 4 decomposition returns [cA4, cD4, cD3, cD2, cD1]
    # cD2 (index 3) roughly isolates the 12.5 - 25 Hz band.
    coeffs = pywt.wavedec(eeg_epoch, 'db4', level=4)
    cD2 = coeffs[3]
    features['eeg_dwt_d2_energy'] = np.sum(np.square(cD2))
    
    return features

def test_feature_output_dimensions():
    """Tests that the function returns a dictionary with exactly 7 features."""
    eeg_epoch = np.random.randn(3000)
    emg_epoch = np.random.randn(3000)
    
    result = compute_additional_features(eeg_epoch, emg_epoch, fs=100)
    
    assert isinstance(result, dict)
    assert len(result) == 7
    assert "eeg_rel_delta" in result