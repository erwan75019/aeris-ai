# Data sources and licensing

## Built-in demo

The default provider generates four fictional aircraft and 61 observations per
track. Callsigns, positions and anomalies are synthetic. This makes local runs,
tests and screenshots reproducible and safe to redistribute.

Every flight response exposes `source: "synthetic_demo"`. The interface must
continue to surface provenance when a real provider is added.

## OpenSky Network

OpenSky is a candidate adapter, not a bundled dataset. Its API authentication,
quotas and data licence change independently of this repository. Before enabling
an adapter, review the current official API documentation and terms, obtain the
required credentials, and confirm that the intended storage and redistribution
are permitted. Never commit credentials or raw provider captures.

## Aviation Weather Center

Weather data should be fetched server-side from the official Aviation Weather
Center endpoints with caching, attribution and conservative retry limits. Check
the current product-specific documentation before production use.

## Operational safety

AERIS AI is experimental decision support. It is not certified for navigation,
separation, air-traffic control or any safety-critical operational decision.
External feeds can be delayed, incomplete, inaccurate or legally restricted.
