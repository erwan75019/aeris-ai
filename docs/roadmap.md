# Delivery roadmap

## Delivered vertical slice

- Responsive live radar and historical replay experience
- Synthetic provider with explicit provenance
- Flight selection, observed track and 5/10/15-minute prediction baseline
- Transparent anomaly evidence and deterministic intelligence report
- Scenario simulation endpoint and analytics summary endpoint
- API/unit/browser/accessibility tests, Docker images and CI
- PostGIS schema/migration and idempotent observation ingestion
- Versioned Isolation Forest plus LSTM/GRU/Transformer experiments and model cards

## Next production increments

1. Credentialed provider adapters with caching, quota control and provenance
2. External dataset snapshots and real-data licence review
3. Shadow evaluation, drift monitoring and artifact rollback controls
4. Authentication, tenant isolation, audit trails and distributed rate limiting
5. Observability, backups, restore drills and production deployment manifests

Each model increment must publish data lineage, metrics by horizon/region,
calibration, known failure modes and a reproducible evaluation command.
