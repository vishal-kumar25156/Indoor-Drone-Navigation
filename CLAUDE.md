# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **Ultrasonic Material Classification System** for indoor drone navigation. It collects ultrasonic sensor data from STM32 firmware over UART, builds labeled CSV datasets per material, and trains distance-specific RandomForest classifiers to identify materials (Cardboard, Cloth, Hand, Paper, Suitcase, Wood) from echoes.

## Commands

There is no build system. Install dependencies manually:

```bash
pip install pandas numpy scikit-learn joblib pyserial jupyter
```

**Collect data from STM32 over UART:**
```bash
python serial_capture.py --port COM3 --label wood --start 20 --end 300 --step 10
python serial_capture.py --port COM3 --label metal --quick --samples 50
```

**Train distance-specific models:**
```bash
python train_model.py
```

**Explore data and clustering:**
```bash
jupyter notebook dev_test.ipynb
```

## Architecture

The system has three tiers:

### Tier 1: STM32 Firmware (not in this repo)
- Excites an ultrasonic transducer via PWM frequency sweep (chirp: start_arr=1828 → end_arr=1422, 60 steps)
- Captures 2400 ADC samples via DMA at ~90kHz (26.7ms capture window)
- Signal processing pipeline: DC removal → matched filtering with time-varying gain → envelope extraction → 4-point moving average smoothing → temporal frame accumulation (alpha=0.85)
- Detects echoes with SNR thresholds (ENTER=2.5, EXIT=1.8) and extracts 20 features
- Streams results as `key = value` pairs over UART (115200 baud) wrapped in `--- Measurement ---` blocks

### Tier 2: Data Collection — `serial_capture.py`
- Reads UART stream and parses measurement blocks
- Validates that each block has ≥15 of 20 expected features
- **Guided mode:** steps through distances (default 20–300cm, 10cm steps), waits for user to position object
- **Quick mode:** collects N samples at current position
- Skips first 15 measurements after each object movement (due to temporal frame accumulation settling)
- Appends rows to per-material CSVs in `raw_dataset/`

### Tier 3: ML Training — `train_model.py`
- Loads `raw_dataset/combined_dataset_processed.csv` (7 features + material label)
- Features used: `snr`, `area_norm_r`, `energy_density`, `width_rel`, `snr_variance`, `echo_consistency`, `r_cm`
- Groups samples into 10cm distance buckets; skips buckets with <30 samples
- Trains one `RandomForestClassifier(n_estimators=300)` + `StandardScaler` per distance bucket
- Saves artifacts as `model_XXXcm.pkl` and `scaler_XXXcm.pkl`

### Data Flow
```
STM32 (20 features via UART)
  → serial_capture.py
  → raw_dataset/{Material}.csv
  → raw_dataset/combined_dataset.csv  (16 features, all materials)
  → raw_dataset/combined_dataset_processed.csv  (7 features, filtered)
  → train_model.py
  → model_XXXcm.pkl + scaler_XXXcm.pkl  (one pair per 10cm bucket)
```

## Dataset Structure

| File | Rows | Features |
|------|------|----------|
| `raw_dataset/combined_dataset.csv` | ~3,440 | 16 engineered features + material |
| `raw_dataset/combined_dataset_processed.csv` | ~3,440 | 7 key features + material |
| `dataset_version1.csv` / `dataset_version2.csv` | ~19,000 each | 20 raw STM32 features + label + target_distance_cm |

The 7 features in `combined_dataset_processed.csv` are the training inputs: `r_cm`, `snr`, `area_norm_r`, `energy_density`, `width_rel`, `snr_variance`, `echo_consistency`.

## Known Gaps

- No `serial_capture.py` or STM32 C code is currently in this repo — only the ML training side
- No inference/prediction script exists yet (only training)
- No `requirements.txt` — dependencies must be installed manually
- Distance-leakage risk: `r_cm` is included as a feature, which means models learn distance-material correlation rather than generalizing across distances. The README recommends training strictly distance-isolated models to avoid this.
