import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.signal import hilbert

# -----------------------------------------
# 1️⃣ Load WAV file
# -----------------------------------------

file_path = "wood/wood30.wav"   # <-- change this
sr, signal = wavfile.read(file_path)

signal = signal.astype(np.float32)
signal = signal - np.mean(signal)   # remove DC

# Optional: zoom into region if signal very long
signal = signal[:60000]

# -----------------------------------------
# 2️⃣ Compute Analytic Signal (Hilbert)
# -----------------------------------------

analytic_signal = hilbert(signal)

real_part = np.real(analytic_signal)
imag_part = np.imag(analytic_signal)

envelope = np.abs(analytic_signal)

# Smooth envelope (moving average)
window_size = 500
smooth_envelope = np.convolve(
    envelope,
    np.ones(window_size)/window_size,
    mode='same'
)

# -----------------------------------------
# 3️⃣ Plot All Steps Like Research Figure
# -----------------------------------------

plt.figure(figsize=(12,8))

# Raw Signal
plt.subplot(2,2,1)
plt.plot(signal)
plt.title("Raw Signal")

# Real + Imaginary
plt.subplot(2,2,2)
plt.plot(real_part, label="Real Part")
plt.plot(imag_part, label="Imaginary Part", alpha=0.7)
plt.legend()
plt.title("Analytic Signal (Hilbert Transform)")

# Envelope over signal
plt.subplot(2,2,3)
plt.plot(signal, alpha=0.5)
plt.plot(envelope, color='green', linewidth=2)
plt.title("Envelope Extraction")

# Smoothed Envelope
plt.subplot(2,2,4)
plt.plot(envelope, alpha=0.4)
plt.plot(smooth_envelope, color='red', linewidth=2)
plt.title("Smoothed Envelope")

plt.tight_layout()
plt.show()