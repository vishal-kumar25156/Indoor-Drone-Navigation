Top candidate features (most likely discriminatory)

peak — echo amplitude (strongly material-dependent)
snr and snr_norm_r — signal-to-noise (material affects returned SNR)
area and area_norm_r — integrated echo energy / normalized area
width_us and width_rel — echo pulse width and relative width
energy_density — material absorption / scattering proxy
echo_consistency — repeatability of echoes (surface roughness)
stability_std and snr_variance — temporal variability (texture/porosity)
resolution_mm — returned resolution of the echo (can vary by surface)
(optionally) rmse_cm / mae_cm — measurement error stats (use with caution; they can leak information about distance/label if computed using material-specific ground-truth)
Features to drop or treat carefully

timestamp — not useful except to identify / group runs
temp, conf, power_percent, latency_ms — appear constant in the Cardboard sample (drop if constant in both files)
material — label, not a feature
v_cms, resolution of sensor-control flags — include only if varying and meaningful
gt_distance_cm — distance strongly changes many echo features; either include as a control variable, or normalize features by distance (preferred) so classifier learns material, not distance
Preprocessing & checks

Remove near-constant columns across both datasets.
Inspect class-wise distributions and correlations (heatmap) to find redundant features (drop or combine highly correlated ones).
Normalize features or z-score by gt_distance_cm (or bin by distance) so model learns material, not distance effects.
Run feature-selection: univariate tests (ANOVA / KS), and model-based importance (RandomForest + permutation importance) and SHAP explanations.
Validate with stratified splits across distances and sensor runs (make sure training/test contain similar distance ranges to avoid leakage).