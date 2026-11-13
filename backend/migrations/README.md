# Database migrations

Run `alembic upgrade head` against the URL in `AERIS_DATABASE_URL`. The first
migration enables PostGIS and creates normalized observation and ingestion-audit
tables. Downgrades remove AERIS-owned tables but deliberately keep the shared
PostGIS extension installed.

Production migrations are forward-only: use `downgrade` only for local testing,
and repair production with a new reviewed migration. Never edit an applied
revision.
