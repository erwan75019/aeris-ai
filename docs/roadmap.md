# Delivery roadmap

## Delivered vertical slice

- Responsive live radar and historical replay experience
- Synthetic provider with explicit provenance
- Flight selection, observed track and 5/10/15-minute prediction baseline
- Transparent anomaly evidence and deterministic intelligence report
- Scenario simulation endpoint and analytics summary endpoint
- Digital Twin UI with synthetic wind, comparative ML scores and DL forecasts
- API-backed analytics UI with metrics, chart and normalized telemetry table
- API/unit/browser/accessibility tests, Docker images and CI
- PostGIS schema/migration and idempotent observation ingestion
- Versioned Isolation Forest plus LSTM/GRU/Transformer experiments and model cards
- Versioned Random Forest traffic-density forecast with a persistence benchmark

## Next production increments

1. Licensed historical dataset snapshots and a real-data licence review
2. Shadow evaluation, drift monitoring and artifact rollback controls
3. Spatially segmented density calibration on licensed historical observations
4. Authentication, tenant isolation, audit trails and distributed rate limiting
5. Observability, backups, restore drills and production deployment manifests

Each model increment must publish data lineage, metrics by horizon/region,
calibration, known failure modes and a reproducible evaluation command.
