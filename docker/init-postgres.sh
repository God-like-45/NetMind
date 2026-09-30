#!/bin/bash
# PostgreSQL initialization script.
# Runs once on first container startup.
# Creates extensions required by NetMind.

set -e

echo "[init-postgres] Creating extensions..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- TimescaleDB: for time-series telemetry hypertables (Phase 2+)
    -- CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

    -- pgvector: for document embeddings (Phase 5+)
    -- CREATE EXTENSION IF NOT EXISTS vector;

    -- pg_stat_statements: for query performance monitoring
    CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

    -- uuid-ossp: for server-side UUID generation
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    GRANT ALL PRIVILEGES ON DATABASE "$POSTGRES_DB" TO "$POSTGRES_USER";
EOSQL

echo "[init-postgres] Extensions created successfully."
