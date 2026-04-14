# Ultrasonic Material Classification Dataset Collection

This project has two parts:

1. **STM32 firmware** that excites the ultrasonic transducer, captures the echo, processes the signal, and prints **20 ML features** over UART.
2. **Python collection script** that reads those UART measurements and saves them into a CSV dataset for later clustering or classification.

This README explains:

- what the full pipeline is doing,
- what each parameter means,
- **how each parameter is calculated in the code**,
- how the Python script stores the data,
- and what precautions to follow during dataset collection.

The explanations below are based directly on the uploaded firmware and Python files. fileciteturn1file1 fileciteturn1file0

---

## 1. Project flow

### Step 1: STM32 generates an ultrasonic chirp
The STM32 sends a short PWM chirp using `TIM1`. In the firmware, the timer auto-reload value is swept from:

- `start_arr = 1828`
- `end_arr = 1422`
- `chirp_steps = 60`
- `step_delay = 20 us`

This creates a short frequency sweep instead of a single fixed tone. The idea is to improve echo detectability and preserve useful material-dependent signal content. fileciteturn1file1

### Step 2: STM32 captures the echo with ADC + DMA
After transmitting the chirp, ADC samples are collected into:

- `ADC_BUFFER_SIZE = 2400`
- `SAMPLE_TIME_US = 11.11`
- `SAMPLE_RATE_HZ = 1,000,000 / 11.11 ≈ 90,009 Hz`

So one frame contains about:

- `2400 × 11.11 us ≈ 26.7 ms` of received signal. fileciteturn1file1

### Step 3: Signal conditioning pipeline
The raw ADC frame is processed in this order:

1. **DC offset estimation**
2. **Matched filtering**
3. **Envelope generation**
4. **Envelope smoothing**
5. **Frame accumulation**
6. **Primary echo detection**
7. **Feature extraction**
8. **UART printing**

The Python script then reads each UART block and stores it in CSV. fileciteturn1file1 fileciteturn1file0

---

## 2. Files in this project

### `stm_code.c`
This is the STM32 firmware. It:

- generates the ultrasonic chirp,
- captures the echo,
- detects the main echo,
- computes **20 features**,
- prints the result over UART in `key = value` format. fileciteturn1file1

### `serial_capture.py`
This is the PC-side dataset collection tool. It:

- connects to the serial port,
- waits for `--- Measurement ---`,
- parses the `key = value` lines,
- validates the feature block,
- writes the features to CSV,
- adds `label` and `target_distance_cm`. fileciteturn1file0

---

## 3. UART output format expected by Python

The Python script expects the STM32 to print one block like this:

```text
--- Measurement ---
distance_cm = ...
snr = ...
confidence = ...
kurtosis = ...
skewness = ...
rms = ...
zero_crossing_rate = ...
peak_to_peak = ...
pulse_width_us = ...
rise_time_us = ...
fall_time_us = ...
echo_area = ...
crest_factor = ...
spectral_centroid = ...
spectral_crest = ...
psd_energy = ...
spectral_entropy = ...
dominant_freq_hz = ...
target_strength_dB = ...
echo_noise_ratio = ...
```

The Python file defines these names in `FEATURE_NAMES`, and it expects 20 features in this exact order. It accepts a measurement when at least 15 of them are present. fileciteturn1file0

---

## 4. Signal processing before feature extraction

This part is important because **all parameters are not computed from the raw ADC directly**. Most features are computed from the processed echo signal.

### 4.1 DC offset calculation
Before each measurement, the code takes 16 ADC readings and averages them:

```c
calculated_dc_offset = (sum of 16 ADC readings) / 16
```

This is used to remove ADC bias before matched filtering. fileciteturn1file1

### 4.2 Matched filter
For each sample:

```text
x = adc_sample - dc_offset
v_new = x - (K * v0) - (R^2 * v1)
y = v_new - v1
abs_y = |y|
current_gain = 1 + i * gain_step
output = abs_y * current_gain
```

Constants used in code:

- `R = 0.90`
- `K = -1.618`
- `gain_step = 0.010`

Then the result is clipped to `20000`. This stage boosts the echo and applies a time-varying gain so later echoes are not too weak. fileciteturn1file1

### 4.3 Envelope generation
In the current firmware, the envelope stage is simple:

```text
envelope[i] = filtered_buffer[i]
```

So the code is effectively using the magnitude-like matched-filter output as the envelope input. fileciteturn1file1

### 4.4 Smoothing
The code smooths the envelope with a 4-point moving average:

```text
envelope[i] = (envelope[i-1] + envelope[i] + envelope[i+1] + envelope[i+2]) / 4
```

This reduces jitter in the detected echo shape. fileciteturn1file1

### 4.5 Frame accumulation
A running accumulated signal is built as:

```text
accum[i] = ACCUM_ALPHA * accum[i] + (1 - ACCUM_ALPHA) * envelope[i]
```

with:

- `ACCUM_ALPHA = 0.85`

This acts like temporal smoothing across frames, which is why the Python script discards some initial readings after the object is moved. fileciteturn1file1 fileciteturn1file0

---

## 5. Echo detection variables used by many features

The code first finds the **main echo**. These values are then used by later features.

### 5.1 Noise floor
Noise is estimated from the first 80 samples:

```text
frame_noise = mean(envelope[0:79])
```

Then it is smoothed over time:

```text
if noise_floor == 0:
    noise_floor = frame_noise
else:
    noise_floor = 0.9 * noise_floor + 0.1 * frame_noise
```

And it is never allowed below 1:

```text
if noise_floor < 1.0:
    noise_floor = 1.0
```

This `noise_floor` is later used for SNR and sonar features. fileciteturn1file1

### 5.2 Peak amplitude and peak index
The code scans from sample index 80 onward and finds the largest value:

```text
peak_val = max(envelope[80 : end])
peak_idx = index of that maximum
```

### 5.3 Echo threshold region
The pulse width and area are computed using a threshold at 20% of the peak:

```text
thresh = 0.20 × peak_val
```

Then the code expands left and right from `peak_idx` until the signal falls below this threshold:

```text
start = first index before peak where envelope <= thresh
end   = first index after peak where envelope <= thresh
```

These become:

- `echo_start_idx = start`
- `echo_end_idx = end`
- `echo_peak_idx = peak_idx` fileciteturn1file1

---

## 6. How each of the 20 parameters is calculated

Below is the exact meaning of every parameter printed by the STM32 firmware.

---

### 6.1 `distance_cm`
**What it means:** estimated distance of the reflector from the sensor.

**How it is calculated:**

```text
time_sec = peak_idx × (SAMPLE_TIME_US / 1e6)
distance_cm = (time_sec × SPEED_OF_SOUND × 100) / 2
```

Where:

- `SPEED_OF_SOUND = 343.0 m/s`
- divide by `2` because the echo travels **to the object and back**.

Then the firmware applies a short moving average over recent distance values:

```text
filtered_distance = mean(non-zero values in distance_history)
```

with history length:

- `MOVING_AVG_SIZE = 4` fileciteturn1file1

---

### 6.2 `snr`
**What it means:** how strong the echo peak is relative to the noise floor.

**Formula used in code:**

```text
snr = peak_amp / noise_floor
```

This is a **linear ratio**, not dB. fileciteturn1file1

---

### 6.3 `confidence`
**What it means:** normalized confidence that the detected echo is a real object.

**Formula used in code:**

```text
confidence = (snr - SNR_EXIT) / (SNR_ENTER - SNR_EXIT)
confidence = clamp(confidence, 0, 1)
```

Thresholds used:

- `SNR_ENTER = 2.5`
- `SNR_EXIT = 1.8`

So:

- below `1.8` → confidence becomes `0`
- above `2.5` → confidence becomes `1` fileciteturn1file1

---

### 6.4 `kurtosis`
**What it means:** how sharply peaked or heavy-tailed the echo shape is.

This is computed over the echo region from `echo_start_idx` to `echo_end_idx`.

First:

```text
mean = average(echo samples)
variance = average((x - mean)^2)
std_dev = sqrt(variance)
```

Then the firmware uses **excess kurtosis**:

```text
kurtosis = average((x - mean)^4) / variance^2 - 3
```

If `std_dev` is too small, it sets kurtosis to `0`. fileciteturn1file1

---

### 6.5 `skewness`
**What it means:** asymmetry of the echo shape.

**Formula:**

```text
skewness = average((x - mean)^3) / std_dev^3
```

Again, if `std_dev` is too small, it is set to `0`. fileciteturn1file1

---

### 6.6 `rms`
**What it means:** root-mean-square strength of the echo region.

**Formula:**

```text
rms = sqrt( average(x^2) )
```

Computed over the detected echo region only. fileciteturn1file1

---

### 6.7 `zero_crossing_rate`
**What it means:** how often the echo waveform changes side relative to its own mean.

Important note: since the signal is envelope-like and mostly positive, the code does **not** check crossing of zero volts. It checks crossing of the **mean** of the echo segment.

**Formula used in code:**

```text
count how many times:
(x[i] - mean) × (x[i-1] - mean) < 0

zero_crossing_rate = zero_crossings / (echo_len - 1)
```

So this is really a **mean-crossing rate**. fileciteturn1file1

---

### 6.8 `peak_to_peak`
**What it means:** amplitude span of the echo region.

**Formula:**

```text
peak_to_peak = max(echo region) - min(echo region)
```

fileciteturn1file1

---

### 6.9 `pulse_width_us`
**What it means:** width of the detected echo pulse at 20% of its peak value.

**Formula:**

```text
pulse_width_us = (echo_end_idx - echo_start_idx) × SAMPLE_TIME_US
```

The echo start and end are found using the 20% peak threshold described earlier. fileciteturn1file1

---

### 6.10 `rise_time_us`
**What it means:** time taken for the echo to rise from 10% of its peak to 90% of its peak.

Thresholds:

```text
thresh_10 = 0.10 × peak_val
thresh_90 = 0.90 × peak_val
```

The code scans from `echo_start_idx` toward the peak and finds:

- first index where signal reaches 10%
- first index where signal reaches 90%

Then:

```text
rise_time_us = (rise_90_idx - rise_10_idx) × SAMPLE_TIME_US
```

fileciteturn1file1

---

### 6.11 `fall_time_us`
**What it means:** time taken for the echo to fall from 90% of peak down to 10% of peak.

The code scans from `peak_idx` toward `echo_end_idx` and finds:

- first index where signal is at or below 90%
- first index where signal is at or below 10%

Then:

```text
fall_time_us = (fall_10_idx - fall_90_idx) × SAMPLE_TIME_US
```

fileciteturn1file1

---

### 6.12 `echo_area`
**What it means:** total integrated echo magnitude inside the pulse window.

**Formula used in code:**

```text
echo_area = sum(envelope[i]) for i = echo_start_idx to echo_end_idx
```

This is not multiplied by sample time, so it is a discrete accumulated amplitude, not a physical area unit. fileciteturn1file1

---

### 6.13 `crest_factor`
**What it means:** how sharp the peak is compared to the average signal energy.

**Formula:**

```text
crest_factor = peak_val / rms
```

If `rms` is too small, it is set to `0`. fileciteturn1file1

---

### 6.14 `spectral_centroid`
**What it means:** the frequency “center of mass” of the echo spectrum.

The firmware first selects a 256-sample window centered near the echo, removes its DC mean, applies a Hann window, and performs a 256-point FFT. Then:

```text
freq_resolution = SAMPLE_RATE_HZ / FFT_SIZE
mag[i] = sqrt(re[i]^2 + im[i]^2)

spectral_centroid = sum(mag[i] × freq[i]) / sum(mag[i])
```

Where:

```text
freq[i] = i × freq_resolution
```

Constants used:

- `FFT_SIZE = 256`
- `FFT_LOG2 = 8` fileciteturn1file1

---

### 6.15 `spectral_crest`
**What it means:** how dominant the strongest spectral bin is relative to the average spectrum.

**Formula:**

```text
mean_mag = sum(mag[i]) / (FFT_SIZE / 2)
spectral_crest = max(mag[i]) / mean_mag
```

This becomes larger when one frequency component dominates. fileciteturn1file1

---

### 6.16 `psd_energy`
**What it means:** average squared spectrum magnitude across FFT bins.

**Formula used in code:**

```text
psd_energy = sum(mag[i]^2) / (FFT_SIZE / 2)
```

This is a spectrum-energy-style feature. It is named PSD energy in the code, but it is not a fully unit-normalized PSD in the strict signal-processing textbook sense. fileciteturn1file1

---

### 6.17 `spectral_entropy`
**What it means:** how spread out the spectral energy is.

First, the code forms normalized spectral probabilities:

```text
p[i] = mag[i] / sum(mag[i])
```

Then entropy:

```text
entropy = -sum( p[i] × log2(p[i]) )
```

Then it normalizes by the maximum possible entropy:

```text
spectral_entropy = entropy / log2(FFT_SIZE / 2)
```

So the value is roughly between 0 and 1:

- near 0 → concentrated spectrum
- near 1 → spread-out spectrum fileciteturn1file1

---

### 6.18 `dominant_freq_hz`
**What it means:** frequency of the strongest FFT bin.

**Formula:**

```text
dominant_freq_hz = argmax(mag[i]) × freq_resolution
```

This shows where the strongest echo spectral component lies. fileciteturn1file1

---

### 6.19 `target_strength_dB`
**What it means:** a dB-style measure of how strong the reflected echo is relative to noise.

**Formula:**

```text
target_strength_dB = 20 × log10(peak_val / noise_floor)
```

If noise or peak is too small, the code sets it to `0`. fileciteturn1file1

---

### 6.20 `echo_noise_ratio`
**What it means:** direct linear ratio of echo strength to noise.

**Formula:**

```text
echo_noise_ratio = peak_val / noise_floor
```

This is numerically very close to the same quantity used for `snr`. In this firmware, `echo_noise_ratio` and `snr` are effectively based on the same core ratio. fileciteturn1file1

---

## 7. Important observation about the parameters

A few features are very closely related in the current code:

- `snr` and `echo_noise_ratio` use the same ratio form.
- `target_strength_dB` is just the dB version of that same ratio.
- `pulse_width_us`, `echo_area`, `rise_time_us`, and `fall_time_us` all depend on the detected echo window and peak.

So while the firmware prints 20 features, some are correlated. That is normal, but during ML training you may later remove redundant features after feature importance analysis. fileciteturn1file1

---

## 8. CSV file structure

The Python script writes these columns:

| Column | Source |
|---|---|
| 20 firmware features | parsed from UART |
| `label` | provided through `--label` |
| `target_distance_cm` | distance step chosen by user in guided mode |

Final CSV columns are:

```text
distance_cm, snr, confidence,
kurtosis, skewness, rms, zero_crossing_rate,
peak_to_peak, pulse_width_us, rise_time_us, fall_time_us,
echo_area, crest_factor,
spectral_centroid, spectral_crest, psd_energy,
spectral_entropy, dominant_freq_hz,
target_strength_dB, echo_noise_ratio,
label, target_distance_cm
```

The script appends new runs to the same CSV unless you change the filename. fileciteturn1file0

---

## 9. Python script modes

## Guided mode
This is the default mode. It walks you distance by distance.

Example:

```bash
python serial_capture.py --port COM3 --label metal
```

You can also set your own range:

```bash
python serial_capture.py --port COM3 --label wood --start 20 --end 300 --step 10
```

### What happens in guided mode
At each distance:

1. you place the material,
2. optionally press Enter,
3. the script discards some initial readings,
4. the script collects valid measurements,
5. each valid block is stored in CSV. fileciteturn1file0

## Quick mode
This just collects samples at the current object position.

Example:

```bash
python serial_capture.py --port COM3 --label plastic --quick --samples 50
```

Useful for testing or collecting extra data. fileciteturn1file0

---

## 10. Command-line arguments

| Argument | Meaning | Default |
|---|---|---|
| `--port` | Serial port like `COM3` or `/dev/ttyUSB0` | required |
| `--baud` | UART baud rate | `115200` |
| `--label` | Material name for dataset labeling | required |
| `--csv` | Output CSV filename | `dataset.csv` |
| `--timeout` | Serial read timeout in seconds | `2.0` |
| `--start` | Start distance in guided mode | `20` cm |
| `--end` | End distance in guided mode | `300` cm |
| `--step` | Step size in guided mode | `10` cm |
| `--samples-per-distance` | Number of saved samples per distance | `40` |
| `--stabilize` | Number of initial measurements discarded after moving object | `15` |
| `--auto` | Skip interactive Enter prompts | off |
| `--quick` | Enable quick mode | off |
| `--samples` | Number of samples in quick mode | `100` |

All of these are defined in the Python argument parser. fileciteturn1file0

---

## 11. Why stabilization is needed

The Python script discards initial readings after the object is moved because the firmware uses frame accumulation:

```text
accum = 0.85 × old + 0.15 × new
```

So when you suddenly change distance or replace the material, the accumulated signal still contains some old history. Discarding early frames helps the features represent the new object position more cleanly. fileciteturn1file1 fileciteturn1file0

---

## 12. Precautions for correct parameter calculation

For these parameters to be meaningful, the measurement setup must stay controlled.

### Mechanical setup
- Fix the sensor firmly.
- Do not hold it in your hand.
- Keep the sensor facing straight.
- Keep the material surface as perpendicular as possible.

### Material setup
- Prefer flat sheets or boards.
- Use large enough area, especially for long distance.
- Measure distance from sensor face to object surface.

### During capture
- Do not move the object while sampling.
- Wait a few seconds after changing position.
- Avoid other objects in the beam path.
- Avoid people crossing in front of the sensor.

These precautions are also printed by the Python script itself. fileciteturn1file0

---

## 13. Recommended interpretation of the features

### Strong geometry and reflection features
These mainly describe how strong and wide the echo is:

- `snr`
- `target_strength_dB`
- `echo_noise_ratio`
- `peak_to_peak`
- `echo_area`
- `pulse_width_us`
- `crest_factor`

### Echo-shape features
These describe the shape of the detected pulse:

- `kurtosis`
- `skewness`
- `rise_time_us`
- `fall_time_us`
- `rms`
- `zero_crossing_rate`

### Spectral features
These describe how the echo energy is distributed in frequency:

- `spectral_centroid`
- `spectral_crest`
- `psd_energy`
- `spectral_entropy`
- `dominant_freq_hz`

### Distance/context features
These are useful but can also leak positional information:

- `distance_cm`
- `confidence`
- `target_distance_cm`

For material classification, you will usually want to be careful about distance-related leakage during ML training. fileciteturn1file1 fileciteturn1file0

---

## 14. Example usage

### Collect metal data from 20 cm to 300 cm

```bash
python serial_capture.py --port COM3 --label metal --start 20 --end 300 --step 10
```

### Collect wood data with larger spacing

```bash
python serial_capture.py --port COM3 --label wood --start 20 --end 200 --step 20
```

### Quick collection for testing

```bash
python serial_capture.py --port COM3 --label glass --quick --samples 50
```

fileciteturn1file0

---

## 15. Troubleshooting

### No serial data is coming
Check:

- correct COM/TTY port,
- baud rate is `115200`,
- STM32 is powered and firmware is running,
- UART pins and USB connection are correct. fileciteturn1file0 fileciteturn1file1

### Script says “No object detected” often
Possible reasons:

- object is too small,
- object is tilted,
- object is outside the beam,
- object is too far,
- echo is too weak for current threshold. fileciteturn1file0 fileciteturn1file1

### Distance looks unstable
Possible reasons:

- hand movement,
- loose sensor mounting,
- nearby reflectors,
- inconsistent object placement,
- early frames being used before stabilization completes. fileciteturn1file0 fileciteturn1file1

---

## 16. Practical note for ML work

If your final goal is **material classification independent of distance**, then during model training you should be careful with:

- `distance_cm`
- `target_distance_cm`
- very distance-sensitive amplitude features

A good practice is to first analyze feature distributions and correlations, then try:

- models with and without distance features,
- normalized energy/amplitude features,
- grouped train/test splits by distance. 

That way the model learns material behavior, not just object position.

---

## 17. Summary

This project already has a solid full chain:

- chirp generation,
- ADC capture,
- matched filtering,
- envelope extraction,
- echo detection,
- **20-feature extraction**,
- UART streaming,
- CSV dataset generation.

The most important thing to remember is this:

> almost all printed features are derived from the **detected echo region** inside the processed accumulated envelope, not from raw ADC directly.

That is why good setup and stable collection conditions matter so much.

---

## 18. Source files used for this README

- STM32 firmware: `stm_code.c` fileciteturn1file1
- Python collector: `serial_capture.py` fileciteturn1file0
