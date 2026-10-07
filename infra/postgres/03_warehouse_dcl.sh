#!/bin/bash
# Creates the dedicated ingestion_runner role. Runs once, on first init of an empty
# warehouse-postgres data volume. The password comes from the container env,
# so it is not hardcoded in the repo.
set -euo pipefail

psql -v ON_ERROR_STOP=1 -v ingestion_password="${INGESTION_RUNNER_PASSWORD}" \
    --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" <<'EOSQL'
-- bronze layer: the ingestion load only needs to read and append
CREATE ROLE ingestion_runner WITH LOGIN PASSWORD :'ingestion_password';
GRANT USAGE ON SCHEMA bronze TO ingestion_runner;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA bronze TO ingestion_runner;

-- also cover tables created in bronze after this script runs
ALTER DEFAULT PRIVILEGES IN SCHEMA bronze GRANT SELECT, INSERT ON TABLES TO ingestion_runner;
EOSQL
