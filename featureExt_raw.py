import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.signal import hilbert
from scipy.fft import fft
from scipy.stats import skew, kurtosis

# -----------------------------------------
# LOAD WAV FILE
# -----------------------------------------

file_path = "dataset/cardboard.wav"  # <-- change this
fs, signal = wavfile.read(file_path)

signal = signal.astype(np.float32)
signal -= np.mean(signal)  # remove DC

# Optional: use only first part
signal = signal[:60000]

N = len(signal)
time = np.arange(N) / fs

# -----------------------------------------
# TIME DOMAIN FEATURES
# -----------------------------------------

peak_amplitude = np.max(np.abs(signal))
rms_value = np.sqrt(np.mean(signal**2))
total_energy = np.sum(signal**2)

zero_crossings = np.sum(np.diff(np.sign(signal)) != 0)
zcr = zero_crossings / (N - 1)

mean_val = np.mean(signal)
variance = np.var(signal)
skewness = skew(signal)
kurt = kurtosis(signal)

# -----------------------------------------
# ENVELOPE FEATURES (Hilbert)
# -----------------------------------------

analytic = hilbert(signal)
envelope = np.abs(analytic)

envelope_peak = np.max(envelope)
envelope_energy = np.sum(envelope**2)
envelope_area = np.sum(envelope)

# FWHM
half_max = envelope_peak / 2
above_half = np.where(envelope >= half_max)[0]
if len(above_half) > 0:
    fwhm_samples = above_half[-1] - above_half[0]
    fwhm_time = fwhm_samples / fs
else:
    fwhm_samples = 0
    fwhm_time = 0

# Early / Late Energy
mid_point = N // 2
early_energy = np.sum(envelope[:mid_point]**2)
late_energy = np.sum(envelope[mid_point:]**2)
early_late_ratio = early_energy / (late_energy + 1e-6)

# Envelope Decay Rate (fit log-linear)
env_tail = envelope[mid_point:]
env_tail = env_tail[env_tail > 0]
if len(env_tail) > 10:
    log_env = np.log(env_tail)
    x = np.arange(len(log_env))
    decay_slope = np.polyfit(x, log_env, 1)[0]
else:
    decay_slope = 0

# -----------------------------------------
# FREQUENCY DOMAIN FEATURES
# -----------------------------------------

spectrum = np.abs(fft(signal))
freqs = np.fft.fftfreq(N, 1/fs)

# Use only positive frequencies
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

# Spectral entropy
psd = spectrum / np.sum(spectrum)
spectral_entropy = -np.sum(psd * np.log(psd + 1e-12))

# High / Low frequency ratio
cutoff = fs / 4
low_energy = np.sum(spectrum[freqs < cutoff]**2)
high_energy = np.sum(spectrum[freqs >= cutoff]**2)
hl_ratio = high_energy / (low_energy + 1e-6)

# -----------------------------------------
# PRINT ALL FEATURES
# -----------------------------------------

print("===== TIME DOMAIN =====")
print("Peak Amplitude:", peak_amplitude)
print("RMS:", rms_value)
print("Total Energy:", total_energy)
print("Zero Crossing Rate:", zcr)
print("Variance:", variance)
print("Skewness:", skewness)
print("Kurtosis:", kurt)

print("\n===== ENVELOPE =====")
print("Envelope Peak:", envelope_peak)
print("Envelope Energy:", envelope_energy)
print("Envelope Area:", envelope_area)
print("FWHM (samples):", fwhm_samples)
print("FWHM (seconds):", fwhm_time)
print("Early/Late Ratio:", early_late_ratio)
print("Decay Slope:", decay_slope)

print("\n===== FREQUENCY DOMAIN =====")
print("Spectral Energy:", spectral_energy)
print("Spectral Centroid:", spectral_centroid)
print("Spectral Bandwidth:", spectral_bandwidth)
print("Dominant Frequency:", dominant_freq)
print("Spectral Entropy:", spectral_entropy)
print("High/Low Energy Ratio:", hl_ratio)
