# AERIS radar design contract

## Product surface

- **Job:** monitor a clearly identified demonstration airspace, inspect a flight,
  replay its history and compare observed, predicted and simulated paths.
- **Audience:** aviation-data researchers and software engineers. They need data
  provenance, time, altitude and anomaly context before decorative metrics.
- **Primary action:** select an aircraft on the radar or in search, then inspect
  its observed track and experimental projection.
- **Navigation aids:** geographic sector filters, explicit static airport focus
  and 2D/3D perspective controls remain secondary to aircraft analysis.
- **Tone:** dense, calm, technical and operational, without imitating a certified
  air-traffic-control display.
- **Memorable detail:** concentric cyan range rings and a continuous timeline make
  the central map read as an analysis instrument rather than a generic dashboard.

## Hierarchy and constraints

1. The radar occupies most of the first viewport.
2. `SYNTHETIC DEMO` and the non-operational disclaimer remain visible.
3. Flight selection, connection state and UTC replay time are never encoded by
   color alone.
4. Desktop target: 1440x900. Mobile target: 390x844, with the inspector below
   the map and touch targets at least 40px.
5. MapLibre uses a local dark style by default. A configured external style must
   provide its own legally correct attribution.
6. Respect `prefers-reduced-motion`; keep keyboard focus visible.

## Content states

| State | Feedback | Recovery |
| --- | --- | --- |
| Loading | Stable radar shell and status text | Wait; no layout shift |
| Empty | `No aircraft in this view` | Clear search or reset replay |
| Error | API error banner | Retry button |
| Partial | Weather/LLM/model limitations named in inspector | Continue with available tools |
| Success | Aircraft and source count in header | Select and inspect |
| Permission | External live provider is disabled | Continue in demo mode |

