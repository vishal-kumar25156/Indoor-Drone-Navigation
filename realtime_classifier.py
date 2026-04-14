"""
realtime_classifier.py
======================
Watches a live-capture CSV for new rows and classifies each measurement
using the distance-independent global model (XGBoost + distance normalisation).

Usage
-----
    python realtime_classifier.py --csv /path/to/live_capture.csv

Optional flags
--------------
    --models-dir   Path to the models/ directory  (default: ./models)
    --output-csv   Path for predictions log        (default: ./live_predictions.csv)
    --verbose      Print full feature vector for each prediction
"""

import argparse
import csv
import json
import logging
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# ── ANSI colour helpers ───────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RED    = "\033[91m"
DIM    = "\033[2m"

LABEL_COLOURS = {
    "cardboard": "\033[33m",   # orange-ish
    "metal":     "\033[94m",   # blue
    "wall":      "\033[37m",   # white/grey
    "wood":      "\033[32m",   # green
}

def colour(text: str, code: str) -> str:
    return f"{code}{text}{RESET}"


# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("classifier")


# ── Model loader ──────────────────────────────────────────────────────────────
class GlobalModel:
    """Wraps the trained global model, scaler, and normalisation config."""

    def __init__(self, models_dir: Path):
        meta_path = models_dir / "global_metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(
                f"global_metadata.json not found in {models_dir}. "
                "Run analysis_and_model.ipynb Phase 7 first."
            )

        with open(meta_path) as f:
            self.meta = json.load(f)

        self.model   = joblib.load(models_dir / "global_model.pkl")
        self.scaler  = joblib.load(models_dir / "global_scaler.pkl")
        self.norm    = self.meta["normalisation"]
        self.classes = self.meta["classes"]
        self.features = self.meta["features"]

        log.info(
            "Loaded %s global model  |  %d features  |  classes: %s",
            self.meta["model_type"],
            len(self.features),
            self.classes,
        )

    def _normalise(self, row: dict) -> dict:
        """Apply distance normalisation to a raw feature row."""
        d     = float(row["distance_cm"])
        d_ref = self.norm["d_ref_cm"]
        normed = {}

        for feat in self.norm["amplitude_feats"]:
            normed[feat + "_dnorm"] = float(row[feat]) / d

        for feat in self.norm["power_feats"]:
            normed[feat + "_dnorm"] = float(row[feat]) / (d ** 2)

        for feat in self.norm["db_feats"]:
            normed[feat + "_dnorm"] = float(row[feat]) + 20 * math.log10(d / d_ref)

        for feat in self.norm["stable_feats"]:
            if feat in row:
                normed[feat + "_dnorm"] = float(row[feat])

        return normed

    def predict(self, row: dict) -> dict:
        """
        Classify one measurement row.

        Parameters
        ----------
        row : dict  Raw feature values (column_name -> value), including distance_cm.

        Returns
        -------
        dict with keys: label, confidence, probabilities
        """
        normed = self._normalise(row)
        x = np.array([[normed[f] for f in self.features]])
        x_scaled = self.scaler.transform(x)

        pred_idx   = int(self.model.predict(x_scaled)[0])
        label      = self.classes[pred_idx]
        proba      = self.model.predict_proba(x_scaled)[0]
        confidence = float(proba[pred_idx])

        return {
            "label":         label,
            "confidence":    confidence,
            "probabilities": dict(zip(self.classes, proba.tolist())),
        }


# ── Prediction logger ─────────────────────────────────────────────────────────
class PredictionLogger:
    """Appends predictions to a CSV file, creating it with a header if needed."""

    COLUMNS = [
        "timestamp", "source_row", "distance_cm",
        "predicted_label", "confidence",
        "p_cardboard", "p_metal", "p_wall", "p_wood",
    ]

    def __init__(self, output_path: Path):
        self.path = output_path
        if not output_path.exists():
            with open(output_path, "w", newline="") as f:
                csv.DictWriter(f, fieldnames=self.COLUMNS).writeheader()
            log.info("Created predictions log: %s", output_path)
        else:
            log.info("Appending to existing predictions log: %s", output_path)

    def write(self, row_index: int, distance_cm: float, result: dict):
        proba = result["probabilities"]
        record = {
            "timestamp":       datetime.now().isoformat(timespec="seconds"),
            "source_row":      row_index,
            "distance_cm":     round(distance_cm, 2),
            "predicted_label": result["label"],
            "confidence":      round(result["confidence"], 4),
            "p_cardboard":     round(proba.get("cardboard", 0), 4),
            "p_metal":         round(proba.get("metal", 0), 4),
            "p_wall":          round(proba.get("wall", 0), 4),
            "p_wood":          round(proba.get("wood", 0), 4),
        }
        with open(self.path, "a", newline="") as f:
            csv.DictWriter(f, fieldnames=self.COLUMNS).writerow(record)


# ── Pretty terminal printer ───────────────────────────────────────────────────
def print_prediction(row_index: int, distance_cm: float, result: dict, verbose: bool = False):
    label      = result["label"]
    confidence = result["confidence"]
    proba      = result["probabilities"]
    lc         = LABEL_COLOURS.get(label, "")

    conf_colour = GREEN if confidence >= 0.90 else (YELLOW if confidence >= 0.70 else RED)

    print(
        f"{colour('►', CYAN)} "
        f"{colour(f'Row {row_index:>5}', DIM)}  "
        f"dist={colour(f'{distance_cm:.1f} cm', CYAN):<18}  "
        f"material={colour(f'{label:<10}', lc + BOLD)}  "
        f"confidence={colour(f'{confidence:.1%}', conf_colour)}"
    )

    if verbose:
        prob_bar = "  ".join(
            f"{colour(cls, LABEL_COLOURS.get(cls,''))}={p:.3f}"
            for cls, p in sorted(proba.items(), key=lambda kv: -kv[1])
        )
        print(f"  {colour('proba:', DIM)} {prob_bar}")


# ── CSV watcher ───────────────────────────────────────────────────────────────
class CSVWatcher(FileSystemEventHandler):
    """
    Tracks the number of rows already processed in the target CSV.
    On each file-modified event, reads only the new rows and classifies them.
    """

    def __init__(
        self,
        csv_path: Path,
        model: GlobalModel,
        pred_logger: PredictionLogger,
        verbose: bool,
    ):
        super().__init__()
        self.csv_path   = csv_path
        self.model      = model
        self.pred_logger = pred_logger
        self.verbose    = verbose
        self._processed = 0          # number of data rows already handled (excluding header)
        self._header    = None       # column names

        # Process any rows that already exist when we start
        if csv_path.exists():
            self._process_new_rows()

    # watchdog calls this on any file change in the watched directory
    def on_modified(self, event):
        if Path(event.src_path).resolve() == self.csv_path.resolve():
            self._process_new_rows()

    def _process_new_rows(self):
        try:
            df = pd.read_csv(self.csv_path)
        except (pd.errors.EmptyDataError, FileNotFoundError):
            return

        if df.empty:
            return

        # Drop target_distance_cm if present (not needed by global model)
        if "target_distance_cm" in df.columns:
            df = df.drop(columns=["target_distance_cm"])

        new_rows = df.iloc[self._processed:]
        if new_rows.empty:
            return

        for idx, row in new_rows.iterrows():
            try:
                result = self.model.predict(row.to_dict())
                distance_cm = float(row["distance_cm"])

                print_prediction(idx + 1, distance_cm, result, self.verbose)
                self.pred_logger.write(idx + 1, distance_cm, result)

            except Exception as e:
                log.warning("Could not classify row %d: %s", idx + 1, e)

        self._processed += len(new_rows)


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Real-time material classifier — watches a live CSV for new rows."
    )
    parser.add_argument(
        "--csv",
        required=True,
        metavar="PATH",
        help="Path to the live-capture CSV (same 20-feature format as dataset_version1.csv).",
    )
    parser.add_argument(
        "--models-dir",
        default="models",
        metavar="DIR",
        help="Directory containing global_model.pkl, global_scaler.pkl, global_metadata.json. "
             "Default: ./models",
    )
    parser.add_argument(
        "--output-csv",
        default="live_predictions.csv",
        metavar="PATH",
        help="Where to write prediction results. Default: ./live_predictions.csv",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Also print per-class probability breakdown for each prediction.",
    )
    args = parser.parse_args()

    csv_path    = Path(args.csv).expanduser().resolve()
    models_dir  = Path(args.models_dir).expanduser().resolve()
    output_path = Path(args.output_csv).expanduser().resolve()

    # ── Load model ────────────────────────────────────────────────────────────
    try:
        model = GlobalModel(models_dir)
    except FileNotFoundError as e:
        log.error(str(e))
        sys.exit(1)

    pred_logger = PredictionLogger(output_path)

    # ── Wait for CSV to exist ─────────────────────────────────────────────────
    if not csv_path.exists():
        log.info("Waiting for CSV to appear at: %s", csv_path)
        while not csv_path.exists():
            time.sleep(0.5)
        log.info("CSV found — starting classifier.")

    # ── Start file watcher ────────────────────────────────────────────────────
    handler  = CSVWatcher(csv_path, model, pred_logger, args.verbose)
    observer = Observer()
    observer.schedule(handler, str(csv_path.parent), recursive=False)
    observer.start()

    print(
        f"\n{colour('  Ultrasonic Material Classifier', BOLD + CYAN)}\n"
        f"  Watching : {colour(str(csv_path), YELLOW)}\n"
        f"  Log      : {colour(str(output_path), YELLOW)}\n"
        f"  Model    : {colour(model.meta['model_type'], GREEN)}\n"
        f"  {colour('Press Ctrl+C to stop.', DIM)}\n"
    )

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        log.info("Stopping...")
        observer.stop()

    observer.join()
    log.info("Classifier stopped. Predictions saved to %s", output_path)


if __name__ == "__main__":
    main()
