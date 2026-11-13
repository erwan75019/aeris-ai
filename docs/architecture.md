# Architecture

AERIS AI currently ships as a testable vertical slice with an offline,
deterministic flight provider and three integrity-checked learned artifacts. It
exercises the full user journey without pretending that synthetic evaluation
is external aviation validation or that a local LLM is configured.

```text
Browser (Next.js + MapLibre)
          |
          | same-origin /api/v1 rewrite
          v
FastAPI routes -> application services -> FlightProvider protocol
                         |                    |
                         |                    +-- deterministic demo provider
                         +-- trajectory, anomaly, density, simulation, agent tools

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

- Prediction: an integrity-checked Transformer at 5, 10 and 15 minutes when at
  least 20 observations exist, with a deterministic constant-velocity fallback.
- Anomaly detection: promoted Isolation Forest with named evidence and a
  transparent-rules fallback.
- Density: promoted Random Forest forecasts at 15, 30 and 60 minutes with a
  persistence baseline and held-out count errors.
- Intelligence: deterministic tool orchestration that cites the evidence used.
  It does not claim to be an LLM response when no LLM is configured.
- Simulation: bounded wind/heading/speed scenarios derived from the selected
  flight state.

All learned artifacts are versioned, checksum-verified and promoted only for
the synthetic demo. Their held-out metrics and limitations are model cards, not
claims about real-world aviation performance.

## Deployment

`compose.yaml` runs the frontend, API and PostGIS. Both application images run
as unprivileged users, expose health checks and receive secrets only through
environment variables. The official PostGIS 18/3.7 image is pinned to amd64;
Docker Desktop emulates it on Apple Silicon.
