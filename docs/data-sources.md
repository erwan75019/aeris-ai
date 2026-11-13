# Data sources and licensing

## Built-in demo

The default provider generates four fictional aircraft and 61 observations per
track. Callsigns, positions and anomalies are synthetic. This makes local runs,
tests and screenshots reproducible and safe to redistribute.

Every flight response exposes `source: "synthetic_demo"`. The interface must
continue to surface provenance when a real provider is added.

## OpenSky Network

`OpenSkyFlightProvider` implements `/states/all`, including bbox/time filters,
SI-to-aviation unit normalization, an eight-second cache, bounded in-process
track history, transient retry handling and optional OAuth2 client credentials.
It is disabled by default. Enable it with `AERIS_DATA_PROVIDER=opensky`; set both
OpenSky credential variables for authenticated access or leave both empty for
anonymous current vectors.

As checked on 2026-11-13, the [official OpenSky REST documentation](https://openskynetwork.github.io/opensky-api/rest.html)
states that anonymous users receive only the latest vectors at 10-second
resolution and 400 credits/day. Authenticated standard users receive 4,000
credits/day, five-second resolution and up to one hour of past state vectors.
Global `/states/all` requests cost more credits than bounded queries. OAuth2
client credentials are the only supported authenticated flow; basic auth is no
longer accepted.

OpenSky data are not bundled. Confirm the current research/non-commercial terms,
citation requirements, storage rights and redistribution rights for every use.
Never commit credentials or raw provider captures.

## Aviation Weather Center

`AviationWeatherClient` reads current METAR JSON server-side from
`/api/data/metar`, normalizes provenance and caches each station for 15 minutes.
HTTP 204, 429 and upstream failures remain distinct errors. Browsers never call
the provider directly.

As checked on 2026-11-13, the [official Aviation Weather Center Data API](https://aviationweather.gov/data/api/)
limits clients to 100 requests/minute and most responses to 400 records, asks for
a custom User-Agent, and recommends cache files for large queries. CORS is not
permitted. AERIS therefore uses scoped station requests and server-side caching.

Offline agent reports use a synthetic weather grid explicitly labelled
`synthetic_demo`; they never present it as an observed METAR.

## Operational safety

AERIS AI is experimental decision support. It is not certified for navigation,
separation, air-traffic control or any safety-critical operational decision.
External feeds can be delayed, incomplete, inaccurate or legally restricted.
