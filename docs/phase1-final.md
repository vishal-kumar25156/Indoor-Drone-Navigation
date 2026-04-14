analysis_and_model.ipynb — 6 phases, all verified working:

Phase	What it does
1 — Data Loading	Merges v1+v2 (38,000 rows, 4 classes), sanity checks (0 nulls, 0 dupes)
2 — EDA	Class distribution, distance box plots, per-class feature KDE, correlation heatmap, SNR vs Echo Area scatter across distances
3 — Feature Selection	MI scores, RF global importance, correlation filter (drops
4 — Model Training	Compares RandomForest / XGBoost / GradientBoosting on 4 sample buckets → trains best model across all 19 distance buckets
5 — Evaluation	Accuracy+F1 vs distance line chart, per-class F1 heatmap, confusion matrices (6 representative distances), misclassification analysis
6 — Persistence	Saves 19 models/model_XXcm.pkl + 19 scalers/scaler_XXcm.pkl + models/metadata.json
Results:

Best model: RandomForest (mean test accuracy across comparison buckets: 99.81%)
Overall mean accuracy across all 19 distance buckets: 99.91%
Worst bucket: 110cm @ 99.27% | Best bucket: 30cm @ 100%
14 features selected (out of 20) — psd_energy, rms, distance_cm, echo_area, echo_noise_ratio ranked highest