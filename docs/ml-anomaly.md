# ML anomaly detection

## Prediction contract

The model ranks a completed or partial track by geometric/statistical novelty.
Its output changes only the research UI's `nominal`/`unusual` indicator. It must
never trigger an operational aviation action. Missing or invalid artifacts fall
back to the transparent rule baseline.

## Dataset and leakage controls

`backend.ml.synthetic` creates 180 explicitly synthetic tracks. One quarter
contains an injected heading, altitude-rate or speed scenario. No sample is
presented as a real incident. Tracks are ordered by start time and split 60/20/20
into train, validation and test sets; a flight exists in exactly one split.

The Isolation Forest fits only nominal training tracks. The decision threshold
is selected once on validation data, and the latest held-out period is evaluated
once. Features use only observations at or before inference time and the same
function is imported by training and serving.

## Reproduce training

```bash
python -m backend.ml.train_anomaly --output-dir artifacts/models/anomaly
pytest backend/tests/test_ml_pipeline.py
```

The versioned manifest records configuration, split policy, test metrics,
feature order and the model SHA-256. Serving verifies both the feature contract
and checksum before deserializing the repository-owned artifact. Never load
untrusted joblib/pickle files.

## Promotion and rollback

The learned model is useful in the demo only if held-out F1 is at least 0.80,
ROC-AUC is at least 0.90, and the false-positive rate is at most 0.15 on the
synthetic evaluation. These gates reflect a small research dataset and do not
imply real-world performance. Rollback is immediate: remove or invalidate the
artifact and AERIS returns to `transparent_rules_baseline`.

Real provider data requires a new dataset version, point-in-time review,
provider licence confirmation, error analysis and shadow evaluation before a
model can be described as externally validated.
