import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score
import joblib

# -------------------------
# Load dataset
# -------------------------
df = pd.read_csv("raw_dataset/combined_dataset_processed.csv")

print("Dataset loaded.")
print("Total samples:", len(df))

# -------------------------
# Create distance bucket
# -------------------------
df["distance_bucket"] = (df["r_cm"] / 10).round() * 10

print("\nUnique distance buckets:")
print(sorted(df["distance_bucket"].unique()))

# -------------------------
# Select features
# -------------------------
features = [
    "snr",
    "area_norm_r",
    "energy_density",
    "width_rel",
    "snr_variance",
    "echo_consistency"
]

# -------------------------
# Train model per distance
# -------------------------
models = {}

for distance in sorted(df["distance_bucket"].unique()):

    subset = df[df["distance_bucket"] == distance]

    if len(subset) < 30:
        continue  # skip very small buckets

    print(f"\n==============================")
    print(f"Distance: {distance} cm")
    print(f"Samples: {len(subset)}")

    X = subset[features]
    y = subset["material"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        random_state=42
    )

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    print("Accuracy:", acc)
    print(classification_report(y_test, y_pred))

    # Save model and scaler per distance
    joblib.dump(model, f"model_{int(distance)}cm.pkl")
    joblib.dump(scaler, f"scaler_{int(distance)}cm.pkl")

    models[distance] = model

print("\nAll distance models trained and saved.")
