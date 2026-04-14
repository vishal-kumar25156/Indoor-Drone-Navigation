import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load dataset
df = pd.read_csv("combinedV2.csv")
df = df[["area", "r_cm", "material"]].dropna()

plt.figure(figsize=(10,6))

materials = df["material"].unique()
colors = plt.cm.tab10.colors

for i, mat in enumerate(materials):
    subset = df[df["material"] == mat]
    
    plt.scatter(
        subset["area"],
        subset["r_cm"],
        label=mat,
        color=colors[i % len(colors)],
        alpha=0.6
    )

plt.xlabel("area")
plt.ylabel("r_cm")
plt.title("Material Distribution (area vs r_cm)")
plt.legend()
plt.show()
