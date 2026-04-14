import numpy as np
import pandas as pd
from scipy.io import wavfile
from scipy.signal import hilbert
from scipy.fft import fft
from scipy.stats import skew, kurtosis
import os

# -----------------------------------------
# FILE LIST
# -----------------------------------------

files = [
    "paper/paper15.wav",
    "paper/paper30.wav",
    "paper/paper45.wav",
    "paper/paper60.wav",
    "paper/paper75.wav",
    "paper/paper90.wav",
    "paper/paper105.wav",
    "paper/paper120.wav",
    "paper/paper135.wav",
    "paper/paper150.wav",
    "paper/paper165.wav",
    "paper/paper180.wav",
    "paper/paper195.wav",
    "paper/paper210.wav",
    "paper/paper225.wav",
    "paper/paper240.wav",
    "paper/paper255.wav",
    "paper/paper270.wav",
    "paper/paper285.wav",
    "paper/paper300.wav",
]
    

# -----------------------------------------
# FEATURE EXTRACTION FUNCTION
# -----------------------------------------

def extract_features(file_path):

    fs, signal = wavfile.read(file_path)

    signal = signal.astype(np.float32)
    signal -= np.mean(signal)

    signal = signal[:60000]  # optional trimming

    N = len(signal)

    # -------- TIME DOMAIN --------
    peak_amplitude = np.max(np.abs(signal))
    rms_value = np.sqrt(np.mean(signal**2))
    total_energy = np.sum(signal**2)
    zcr = np.sum(np.diff(np.sign(signal)) != 0) / (N - 1)
    variance = np.var(signal)
    skewness = skew(signal)
    kurt_val = kurtosis(signal)

    # -------- ENVELOPE --------
    analytic = hilbert(signal)
    envelope = np.abs(analytic)

    envelope_peak = np.max(envelope)
    envelope_energy = np.sum(envelope**2)
    envelope_area = np.sum(envelope)

    half_max = envelope_peak / 2
    above_half = np.where(envelope >= half_max)[0]

    if len(above_half) > 0:
        fwhm_samples = above_half[-1] - above_half[0]
        fwhm_time = fwhm_samples / fs
    else:
        fwhm_samples = 0
        fwhm_time = 0

    mid_point = N // 2
    early_energy = np.sum(envelope[:mid_point]**2)
    late_energy = np.sum(envelope[mid_point:]**2)
    early_late_ratio = early_energy / (late_energy + 1e-6)

    env_tail = envelope[mid_point:]
    env_tail = env_tail[env_tail > 0]

    if len(env_tail) > 10:
        log_env = np.log(env_tail)
        x = np.arange(len(log_env))
        decay_slope = np.polyfit(x, log_env, 1)[0]
    else:
        decay_slope = 0

    # -------- FREQUENCY DOMAIN --------
    spectrum = np.abs(fft(signal))
    freqs = np.fft.fftfreq(N, 1/fs)

    positive = freqs > 0
    spectrum = spectrum[positive]
    freqs = freqs[positive]

    spectral_energy = np.sum(spectrum**2)

    spectral_centroid = np.sum(freqs * spectrum) / np.sum(spectrum)
    spectral_bandwidth = np.sqrt(
        np.sum(((freqs - spectral_centroid)**2) * spectrum) /
        np.sum(spectrum)
    )

    dominant_freq = freqs[np.argmax(spectrum)]

    psd = spectrum / np.sum(spectrum)
    spectral_entropy = -np.sum(psd * np.log(psd + 1e-12))

    cutoff = fs / 4
    low_energy = np.sum(spectrum[freqs < cutoff]**2)
    high_energy = np.sum(spectrum[freqs >= cutoff]**2)
    hl_ratio = high_energy / (low_energy + 1e-6)

    return [
        peak_amplitude,
        rms_value,
        total_energy,
        zcr,
        variance,
        skewness,
        kurt_val,
        envelope_peak,
        envelope_energy,
        envelope_area,
        fwhm_samples,
        fwhm_time,
        early_late_ratio,
        decay_slope,
        spectral_energy,
        spectral_centroid,
        spectral_bandwidth,
        dominant_freq,
        spectral_entropy,
        hl_ratio
    ]

# -----------------------------------------
# PROCESS ALL FILES
# -----------------------------------------

feature_list = []

for file in files:

    features = extract_features(file)

    # Extract material name from folder
    material = os.path.dirname(file)

    feature_list.append(features + [material])

# -----------------------------------------
# CREATE DATAFRAME
# -----------------------------------------

columns = [
    "peak_amplitude",
    "rms",
    "total_energy",
    "zcr",
    "variance",
    "skewness",
    "kurtosis",
    "envelope_peak",
    "envelope_energy",
    "envelope_area",
    "fwhm_samples",
    "fwhm_time",
    "early_late_ratio",
    "decay_slope",
    "spectral_energy",
    "spectral_centroid",
    "spectral_bandwidth",
    "dominant_frequency",
    "spectral_entropy",
    "high_low_ratio",
    "material"
]

df = pd.DataFrame(feature_list, columns=columns)

# -----------------------------------------
# SAVE CSV
# -----------------------------------------

df.to_csv("ultrasonic_featuresPaper.csv", index=False)

print("Feature extraction complete.")
print("Saved as ultrasonic_featuresPaper.csv")
print(df)