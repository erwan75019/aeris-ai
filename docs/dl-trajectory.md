# Deep-learning trajectory prediction

## Contract

Given the latest 20 one-minute aircraft states, AERIS predicts local east/north
displacements at 5, 10 and 15 minutes. The API converts those displacements back
to WGS84 coordinates and reports held-out p90 error as empirical uncertainty.
This uncertainty is not a calibrated safety bound.

The model uses only information available at prediction time: relative position,
relative altitude, ground speed, heading sine/cosine and vertical rate. Training
and serving import the same encoder.

## Dataset and split

The reproducible generator creates 180 explicitly synthetic flights with smooth,
predictable turn rates and accelerations. Flights are time-ordered and split
60/20/20; windows never cross flight boundaries. Selection uses only validation
error. The final test period is evaluated once.

## Reproduce

```bash
python -m pip install -e '.[dl]'
python -m backend.dl.train --output-dir artifacts/models/trajectory --device auto
pytest backend/tests/test_dl_pipeline.py
```

`auto` prefers Apple Metal (MPS), then CUDA, then CPU. The committed reference
run used CPU for deterministic comparison. Every checkpoint stores a `state_dict`
and is loaded with `weights_only=True` after SHA-256 verification.

## Reference evaluation

| Model | 5 min MAE | 10 min MAE | 15 min MAE | Mean MAE |
|---|---:|---:|---:|---:|
| Constant-vector baseline | 1.19 km | 5.37 km | 12.50 km | 6.35 km |
| LSTM | 3.36 km | 6.10 km | 13.07 km | 7.51 km |
| GRU | 1.87 km | 4.72 km | 10.07 km | 5.55 km |
| Transformer (selected) | 2.00 km | 3.54 km | 4.81 km | 3.45 km |

The Transformer was selected by validation mean MAE and promoted because its
held-out mean MAE beats the baseline. The baseline remains better at five
minutes; this known limitation is visible here rather than hidden. AERIS falls
back to the baseline when fewer than 20 observations exist or the artifact is
missing/invalid.

These metrics characterize only the procedural synthetic distribution. They do
not establish performance on real aircraft, unusual weather, sensor gaps or new
regions.
