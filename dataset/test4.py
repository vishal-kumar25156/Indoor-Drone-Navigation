import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.signal import hilbert

# -----------------------------------------
# 1️⃣ Load Four WAV Files
# -----------------------------------------

files = [
    "wood.wav",
    "cardboard.wav",
    "paper.wav"
]

signals = []
sample_rates = []

for file in files:
    sr, sig = wavfile.read(file)
    sig = sig.astype(np.float32) - np.mean(sig)
    signals.append(sig)
    sample_rates.append(sr)

# Ensure same sampling rate
if len(set(sample_rates)) != 1:
    raise ValueError("Sampling rates are not equal!")

# Make all signals same length
min_len = min(len(sig) for sig in signals)
signals = [sig[:min_len] for sig in signals]

# Optional zoom
signals = [sig[:60000] for sig in signals]

# -----------------------------------------
# 2️⃣ Hilbert + Envelope
# -----------------------------------------

envelopes = []
smooth_envelopes = []

window_size = 500

for sig in signals:
    analytic = hilbert(sig)
    env = np.abs(analytic)
    env /= np.max(env)   # normalize
    
    smooth = np.convolve(
        env,
        np.ones(window_size)/window_size,
        mode='same'
    )
    
    envelopes.append(env)
    smooth_envelopes.append(smooth)

# -----------------------------------------
# 3️⃣ Plot Comparison
# -----------------------------------------

plt.figure(figsize=(12,10))

# Raw signals
plt.subplot(3,1,1)
for i, sig in enumerate(signals):
    plt.plot(sig, label=files[i])
plt.title("Raw Signal Comparison")
plt.legend()

# Envelope comparison
plt.subplot(3,1,2)
for i, env in enumerate(envelopes):
    plt.plot(env, label=files[i])
plt.title("Envelope Comparison")
plt.legend()

# Smoothed envelope comparison
plt.subplot(3,1,3)
for i, smooth in enumerate(smooth_envelopes):
    plt.plot(smooth, linewidth=2, label=files[i])
plt.title("Smoothed Envelope Comparison")
plt.legend()

plt.tight_layout()
plt.show()