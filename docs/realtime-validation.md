Basic usage


python realtime_classifier.py --csv /path/to/your/live_capture.csv
With verbose probability breakdown


python realtime_classifier.py \
    --csv /path/to/your/live_capture.csv \
    --verbose
All options


python realtime_classifier.py \
    --csv /path/to/your/live_capture.csv \
    --models-dir /path/to/models \       # default: ./models
    --output-csv /path/to/results.csv \  # default: ./live_predictions.csv
    --verbose
What it does on each new row:

Terminal prints:


►  Row    4  dist=20.0 cm    material=cardboard    confidence=99.98%
  proba: cardboard=0.9998  metal=0.0001  wall=0.0001  wood=0.000
live_predictions.csv appends:


timestamp,source_row,distance_cm,predicted_label,confidence,p_cardboard,p_metal,p_wall,p_wood
2026-04-14T17:11:13,4,20.0,cardboard,0.9998,0.9998,0.0001,0.0001,0.0
Key behaviours:

Starts immediately even if the CSV already has rows (classifies all on startup, then watches for new ones)
Waits and retries if the CSV doesn't exist yet when launched
Low confidence predictions (< 70%) are highlighted in red in the terminal
Stops cleanly on Ctrl+C