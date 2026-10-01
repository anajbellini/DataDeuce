#!/bin/bash
# Creates the dedicated bronze_writer role. Runs once, on first init of an empty
# warehouse-postgres data volume. The password comes from the container env,
# so it is not hardcoded in the repo.
set -euo pipefail

psql -v ON_ERROR_STOP=1 -v bronze_password="${BRONZE_WRITER_PASSWORD}" \
    --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" <<'EOSQL'
-- bronze layer: the ingestion load only needs to read and append
CREATE ROLE bronze_writer WITH LOGIN PASSWORD :'bronze_password';
GRANT USAGE ON SCHEMA bronze TO bronze_writer;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA bronze TO bronze_writer;

-- also cover tables created in bronze after this script runs
ALTER DEFAULT PRIVILEGES IN SCHEMA bronze GRANT SELECT, INSERT ON TABLES TO bronze_writer;
EOSQL
