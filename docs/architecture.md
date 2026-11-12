# Architecture

AERIS AI currently ships as a testable vertical slice with an offline,
deterministic flight provider. It exercises the full user journey without
pretending that external aviation data, a trained model, or an LLM is present.

```text
Browser (Next.js + MapLibre)
          |
          | same-origin /api/v1 rewrite
          v
FastAPI routes -> application services -> FlightProvider protocol
                         |                    |
                         |                    +-- deterministic demo provider
                         +-- prediction, anomaly, simulation, report tools

PostgreSQL/PostGIS is provisioned by Compose for the persistence increment.
It is not required by the offline demo provider.
```

## Boundary decisions

- API schemas are Pydantic contracts and reject unknown fields.
- All timestamps are timezone-aware UTC. Replay requests outside the provider
  window return a validation error rather than silently showing current data.
- Coordinates use `(longitude, latitude)` internally and GeoJSON ordering at
  the API/UI boundary.
- Prediction, anomaly detection, simulation and intelligence are independent
  services. A model can replace a baseline without changing the HTTP contract.
- `FlightProvider` isolates data-source licensing and authentication concerns.
- The browser calls only the Next.js origin; backend credentials and upstream
  provider credentials remain server-side.

## Current model semantics

- Prediction: deterministic constant-velocity geodesic baseline at 5, 10 and
  15 minutes.
- Anomaly detection: transparent, named domain rules with evidence and scores.
- Intelligence: deterministic tool orchestration that cites the evidence used.
  It does not claim to be an LLM response when no LLM is configured.
- Simulation: bounded wind/heading/speed scenarios derived from the selected
  flight state.

These baselines are deliberately honest reference implementations. Versioned
scikit-learn and PyTorch artifacts can be evaluated against them before being
promoted.

## Deployment

`compose.yaml` runs the frontend, API and PostGIS. Both application images run
as unprivileged users, expose health checks and receive secrets only through
environment variables. The official PostGIS 18/3.7 image is pinned to amd64;
Docker Desktop emulates it on Apple Silicon.
