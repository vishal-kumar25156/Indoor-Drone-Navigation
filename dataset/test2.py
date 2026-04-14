import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.signal import hilbert

# -----------------------------------------
# 1️⃣ Load Two WAV Files
# -----------------------------------------

file1 = "wood.wav"   # <-- change
file2 = "cardboard.wav"   # <-- change

sr1, sig1 = wavfile.read(file1)
sr2, sig2 = wavfile.read(file2)

sig1 = sig1.astype(np.float32) - np.mean(sig1)
sig2 = sig2.astype(np.float32) - np.mean(sig2)

# Make same length (important)
min_len = min(len(sig1), len(sig2))
sig1 = sig1[:min_len]
sig2 = sig2[:min_len]

# Optional zoom
sig1 = sig1[:60000]
sig2 = sig2[:60000]

# -----------------------------------------
# 2️⃣ Hilbert Transform
# -----------------------------------------

analytic1 = hilbert(sig1)
analytic2 = hilbert(sig2)

env1 = np.abs(analytic1)
env2 = np.abs(analytic2)

# Normalize for fair comparison
env1 /= np.max(env1)
env2 /= np.max(env2)

# Smooth envelopes
window_size = 500

smooth1 = np.convolve(env1,
                      np.ones(window_size)/window_size,
                      mode='same')

smooth2 = np.convolve(env2,
                      np.ones(window_size)/window_size,
                      mode='same')

# -----------------------------------------
# 3️⃣ Plot Comparison
# -----------------------------------------

plt.figure(figsize=(12,8))

# Raw signals
plt.subplot(3,1,1)
plt.plot(sig1, label="Object 1")
plt.plot(sig2, label="Object 2", alpha=0.7)
plt.title("Raw Signal Comparison")
plt.legend()

# Envelope comparison
plt.subplot(3,1,2)
plt.plot(env1, label="Envelope 1")
plt.plot(env2, label="Envelope 2")
plt.title("Envelope Comparison")
plt.legend()

# Smoothed envelope comparison
plt.subplot(3,1,3)
plt.plot(smooth1, label="Smoothed 1", linewidth=2)
plt.plot(smooth2, label="Smoothed 2", linewidth=2)
plt.title("Smoothed Envelope Comparison")
plt.legend()

plt.tight_layout()
plt.show()