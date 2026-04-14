1. How "distance-independent" should it be?

Strict: Exclude distance_cm entirely — model gets only echo features, no distance hint. Harder but truly generalizable.
Relaxed: Keep distance_cm as a feature but train one global model (no bucketing). Simpler but still distance-aware.
2. Feature handling for distance decay?
Echo features like rms, psd_energy, echo_area physically decay with distance (inverse square law). A model trained naively will struggle to separate material effect from distance effect. Options:

Distance-normalize features — divide each feature by a distance scaling factor before training (e.g. rms / distance_cm²) so the model sees distance-corrected values
Use only inherently distance-stable features — spectral features (spectral_centroid, spectral_crest, spectral_entropy, dominant_freq_hz), shape features (kurtosis, skewness, crest_factor, zero_crossing_rate), and ratios (snr, echo_noise_ratio) are more stable across distances
No normalization — train as-is and let the model figure it out
3. Where should it live?

Extend the existing analysis_and_model.ipynb with a new Phase 7?
Or a separate notebook distance_independent_model.ipynb?
My recommendation would be: Strict (no distance_cm) + distance-normalize the decay-sensitive features + add to the existing notebook as Phase 7, so you can directly compare against the per-distance models. What do you think?