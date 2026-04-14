#!/usr/bin/env python3
import argparse
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


def parse_args():
    p = argparse.ArgumentParser(description="K-means on area_norm_r and plot results")
    p.add_argument("--csv", default="combined_dataset.csv", help="CSV file path (relative to this script)" )
    p.add_argument("--k", type=int, default=3, help="Number of clusters (default: 3)")
    p.add_argument("--out-csv", default="combined_dataset_kmeans_area.csv", help="Output CSV with labels")
    p.add_argument("--out-plot", default="kmeans_area_plot.png", help="Output plot file")
    p.add_argument("--show", action="store_true", help="Show plot interactively")
    return p.parse_args()


def main():
    args = parse_args()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = args.csv if os.path.isabs(args.csv) else os.path.join(script_dir, args.csv)

    if not os.path.exists(csv_path):
        print(f"CSV not found: {csv_path}")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    if 'area_norm_r' not in df.columns:
        print("Column 'area_norm_r' not found in CSV.")
        sys.exit(1)

    # Keep original index mapping for plotting
    df_valid = df[['area_norm_r']].copy()
    df_valid = df_valid.dropna()
    if df_valid.shape[0] == 0:
        print("No valid 'area_norm_r' values to cluster.")
        sys.exit(1)

    X = df_valid[['area_norm_r']].values.reshape(-1, 1)

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    k = max(1, args.k)
    km = KMeans(n_clusters=k, random_state=0, n_init=10)
    labels = km.fit_predict(Xs)

    # Attach labels back to full dataframe (NaNs remain NaN)
    label_series = pd.Series(data=np.nan, index=df.index)
    label_series.loc[df_valid.index] = labels
    df_out = df.copy()
    df_out['area_kmeans_label'] = label_series

    out_csv_path = args.out_csv if os.path.isabs(args.out_csv) else os.path.join(script_dir, args.out_csv)
    df_out.to_csv(out_csv_path, index=False)

    # Prepare plotting
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(df_valid))
    y = df_valid['area_norm_r'].values
    cmap = plt.get_cmap('tab10')
    for lab in range(k):
        mask = labels == lab
        ax.scatter(x[mask], y[mask], s=30, color=cmap(lab % 10), label=f'cluster {lab}')

    # Plot cluster centers (in original scale)
    centers_original = scaler.inverse_transform(km.cluster_centers_).flatten()
    for lab, c in enumerate(centers_original):
        ax.hlines(c, xmin=-1, xmax=len(df_valid)+1, colors=cmap(lab % 10), linestyles='dashed', alpha=0.6)

    ax.set_title(f"K-means (k={k}) on area_norm_r")
    ax.set_xlabel('sample index (valid area_norm_r rows)')
    ax.set_ylabel('area_norm_r')
    ax.legend()
    ax.grid(True, linestyle=':', alpha=0.5)

    out_plot_path = args.out_plot if os.path.isabs(args.out_plot) else os.path.join(script_dir, args.out_plot)
    fig.tight_layout()
    fig.savefig(out_plot_path)

    print(f"Saved clustered CSV: {out_csv_path}")
    print(f"Saved plot: {out_plot_path}")
    if args.show:
        plt.show()


if __name__ == '__main__':
    main()
