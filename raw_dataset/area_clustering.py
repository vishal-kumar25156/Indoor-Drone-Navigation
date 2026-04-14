import pandas as pd
import matplotlib.pyplot as plt

files = {
    "Cardboard": "Cardboard.csv",
    "Cloth": "Cloth.csv",
    "Hand": "Hand.csv",
    "Paper": "Paper.csv",
    "Suitcase": "Suitcase.csv",
    "Wood": "Wood.csv"
}

data = []
labels = []

for label, file in files.items():
    df = pd.read_csv(file)
    data.append(df["area"].values)
    labels.append(label)

plt.figure(figsize=(10,6))
plt.boxplot(data)
plt.xticks(range(1, len(labels)+1), labels)
plt.ylabel("Area")
plt.title("Area Distribution per Object")
plt.show()
from scipy.stats import gaussian_kde
import numpy as np

plt.figure(figsize=(10,6))

for label, file in files.items():
    df = pd.read_csv(file)
    area_values = df["area"].values
    kde = gaussian_kde(area_values)
    
    x_range = np.linspace(min(area_values), max(area_values), 500)
    plt.plot(x_range, kde(x_range), label=label)

plt.legend()
plt.xlabel("Area")
plt.ylabel("Density")
plt.title("KDE Density Plot of Area (No Seaborn)")
plt.show()
