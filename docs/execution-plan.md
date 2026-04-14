Execution Plan
Phase 1 — Data Analysis Notebook (analysis_and_model.ipynb)
Step 1: Data Loading & Sanity Check
Merge v1 + v2 into one 38,000-row DataFrame
Drop target_distance_cm, keep distance_cm
Verify: class balance (9,500 each × 4), no nulls, column dtypes
Step 2: Exploratory Data Analysis (EDA)
Class distribution — bar chart of label counts
Distance distribution per class — box plots of distance_cm grouped by label (check if all 4 classes are collected across all 19 distances: 20–200cm)
Feature distributions — histograms/KDE per feature, colored by label (spot which features separate classes visually)
Correlation heatmap — identify redundant features (e.g., echo_noise_ratio vs snr may be near-identical)
Per-distance class overlap — for each 10cm bucket, plot snr vs echo_area scatter colored by label
Step 3: Feature Selection
Mutual Information scores (classification) — rank all 20 features against label, within each distance bucket
RandomForest global feature importance — train one quick RF on the full merged set to get a baseline importance ranking
Correlation filter — drop one from any pair with |r| > 0.95
Output: a ranked feature list; propose a top-k feature set (likely 8–12 features) to carry forward
Phase 2 — Per-Distance Model Training
Step 4: Distance Bucketing Strategy
Use target_distance_cm (19 integer values: 20, 30, …, 200) as bucket keys — each bucket groups ~2,000 rows (38,000 ÷ 19)
Drop target_distance_cm after bucketing; distance_cm is retained as a feature within each model
Step 5: Train/Test Split
Stratified split per bucket — 80% train / 20% test, stratified by label
Keep the test set fixed across all model comparisons
Step 6: Model Training (per distance bucket)
Candidate models: RandomForest, GradientBoosting (XGBoost/sklearn), SVM — compare on a few buckets first
Use selected feature set from Phase 1
StandardScaler fit on train, applied to test
Grid/random search on best candidate (n_estimators, max_depth, min_samples_leaf)
Step 7: Evaluation
Per-bucket metrics — classification report (precision, recall, F1 per class) for each of the 19 distance models
Confusion matrices — per bucket, heatmap layout (4×4, all materials)
Accuracy vs distance plot — line chart showing how model accuracy degrades with distance
Aggregated overall accuracy — weighted average across all buckets
Hard cases analysis — which class pairs are most confused at which distances
Step 8: Model Persistence
Save each distance model as models/model_{distance}cm.pkl and its scaler as scalers/scaler_{distance}cm.pkl
Save selected feature list to models/feature_list.json
Deliverables
File	Contents
analysis_and_model.ipynb	All phases in one notebook with markdown explanations
models/model_XXcm.pkl	19 trained classifiers
scalers/scaler_XXcm.pkl	19 fitted scalers
models/feature_list.json	Selected feature names
