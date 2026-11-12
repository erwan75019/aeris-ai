# Security policy

AERIS AI is pre-1.0 experimental software and must not be used for operational
aviation decisions. Security fixes are applied to the latest `main` branch; no
older release line is currently supported.

Please report suspected vulnerabilities privately through GitHub's security
advisory feature rather than opening a public issue. Include affected versions,
reproduction steps, impact and any suggested mitigation. Do not include live
aviation-provider credentials or personal data in a report.

The offline demo has no authentication and is intended for a trusted local
environment. Before any public deployment, add an identity layer, tenant-aware
authorization, distributed rate limiting, audit retention and a reviewed secret
management system as described in `docs/roadmap.md`.
