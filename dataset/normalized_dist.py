import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import matplotlib.pyplot as plt

# -----------------------------------------
# Load CSV files
# -----------------------------------------

df_cardboard = pd.read_csv("ultrasonic_featuresCardboard.csv")
df_paper = pd.read_csv("ultrasonic_featuresPaper.csv")
df_wood = pd.read_csv("ultrasonic_featuresWood.csv")

df = pd.concat([df_cardboard, df_paper, df_wood], ignore_index=True)

print("Total samples:", len(df))
print("Samples per class:")
print(df["material"].value_counts())

# -----------------------------------------
# Select features (physics-based)
# -----------------------------------------

features = [
    "skewness",
    "fwhm_samples",
    "spectral_centroid",
    "spectral_entropy",
    "high_low_ratio",
    "decay_slope",
    "early_late_ratio"
]

X = df[features]
y = df["material"]

# -----------------------------------------
# Train / Test split
# -----------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, stratify=y, random_state=42
)

# -----------------------------------------
# Standardize
# -----------------------------------------

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# -----------------------------------------
# Train SVM
# -----------------------------------------

svm = SVC(kernel='rbf', C=10, gamma='scale')
svm.fit(X_train, y_train)

y_pred = svm.predict(X_test)

# -----------------------------------------
# Results
# -----------------------------------------

print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nClassification Report:\n")
print(classification_report(y_test, y_pred))

cm = confusion_matrix(y_test, y_pred)

plt.imshow(cm)
plt.title("Confusion Matrix")
plt.xlabel("Predicted")
plt.ylabel("True")
plt.colorbar()
plt.show()