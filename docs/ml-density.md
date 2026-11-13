# ML traffic-density forecast

## Prediction contract

The service forecasts an experimental regional aircraft count 15, 30 and 60
minutes ahead. It always returns the current-count persistence baseline beside
the learned result. The output is not a sector-capacity, flow-management or
safety prediction.

## Dataset and leakage controls

`backend.ml.density` generates 120 days of explicitly synthetic 15-minute count
observations with daily, weekly and stochastic demand variation. Features use
only the forecast timestamp, current/lagged counts and a trailing 60-minute
mean. Targets are later counts at the three horizons.

Samples are split chronologically 60/20/20: 6,907 train, 2,302 validation and
2,303 held-out test samples. The test window is evaluated once and no future
count appears in a feature. A Random Forest is promoted only when it beats
persistence on both validation and held-out mean MAE.

## Held-out synthetic metrics

| Horizon | Random Forest MAE | Persistence MAE | Random Forest RMSE |
| --- | ---: | ---: | ---: |
| 15 min | 1.87 aircraft | 2.51 aircraft | 2.41 aircraft |
| 30 min | 1.88 aircraft | 2.63 aircraft | 2.43 aircraft |
| 60 min | 1.88 aircraft | 2.75 aircraft | 2.43 aircraft |
| Mean | 1.88 aircraft | 2.63 aircraft | — |

These measurements describe only the synthetic generator. They do not estimate
performance on OpenSky, EUROCONTROL or operational sector data.

## Reproduce training

```bash
python -m backend.ml.train_density --output-dir artifacts/models/density
pytest backend/tests/test_density_pipeline.py
```

The manifest stores configuration, temporal split counts, baseline/model
metrics, limitations and a SHA-256 digest. Serving checks the feature and
horizon contracts plus the digest before deserializing the repository-owned
joblib artifact. A missing, rejected or corrupted artifact falls back to the
named `persistence_baseline`.

## Next validation gate

Promotion beyond the synthetic demo requires licensed point-in-time traffic
counts, spatially disjoint evaluation by region, season/airport error analysis,
drift monitoring and uncertainty calibration. No current result is described as
real-world validated.
