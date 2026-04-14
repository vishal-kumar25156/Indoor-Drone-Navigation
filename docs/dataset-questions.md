### Questions

1. Dataset combination
v1 has cardboard + wood, v2 has wall + metal. Total: 4 classes, 38,000 rows combined. Should I merge both into a single 4-class classifier, or train separate models per dataset?

2. Target: distance-aware or distance-agnostic?
The data has distance_cm as a feature and samples span multiple distances (20cm, 30cm, 40cm...). Two approaches:

Single global model — include distance_cm as a feature (simpler, but risks overfitting to distance-material correlation)
Per-distance models — train one model per distance bucket, like train_model.py does (more robust, how the existing code works)
Which do you prefer, or should I explore both?

3. distance_cm vs target_distance_cm
There are two distance columns — distance_cm (measured by sensor, slightly noisy) and target_distance_cm (the ground truth integer distance). Which should be used as a feature, and should the other be dropped?

4. Feature scope
v1/v2 have 20 raw STM32 features (vs the 6 curated features used in train_model.py). Should I:

Use all 20 features and let the model/feature importance decide
Start with the 6 curated features from combined_dataset_processed.csv
Run feature selection as part of the analysis
5. Deliverable format
Should the analysis and model live in a Jupyter notebook (like dev_test.ipynb) or in Python scripts (like train_model.py)?

6. Evaluation priority
What matters most — overall accuracy, per-class performance (some materials harder at certain distances), or inference speed (runs on a drone)?




### ANSWER 

1. Merge both dataset
2. Per-distance models
3. distance_cm
4. Run feature selection as part of the analysis
5. Jupyter notebook 
6. per-class performance and overall accuracy

