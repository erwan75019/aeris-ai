# Delivery roadmap

## Delivered vertical slice

- Responsive live radar and historical replay experience
- Synthetic provider with explicit provenance
- Flight selection, observed track and 5/10/15-minute prediction baseline
- Transparent anomaly evidence and deterministic intelligence report
- Scenario simulation endpoint and analytics summary endpoint
- API/unit/browser/accessibility tests, Docker images and CI

## Next production increments

1. PostGIS repositories, migrations and ingestion idempotency
2. Credentialed provider adapters with caching, quota control and provenance
3. Dataset snapshots, feature registry and leakage-safe temporal splits
4. Versioned anomaly models benchmarked against the rule baseline
5. Versioned trajectory models benchmarked against constant velocity
6. Model registry, shadow evaluation, drift monitoring and rollback
7. Authentication, tenant isolation, audit trails and distributed rate limiting
8. Observability, backups, restore drills and production deployment manifests

Each model increment must publish data lineage, metrics by horizon/region,
calibration, known failure modes and a reproducible evaluation command.
