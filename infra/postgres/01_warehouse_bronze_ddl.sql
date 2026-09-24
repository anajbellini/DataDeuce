CREATE SCHEMA IF NOT EXISTS bronze;

-- creating table for *.csv
CREATE TABLE IF NOT EXISTS bronze.atp_history
(
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payload           jsonb,
    _source_file      VARCHAR NOT NULL,
    _source_file_hash VARCHAR,
    _ingested_at      TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3)
);

-- creating table for *_wta.csv
CREATE TABLE IF NOT EXISTS bronze.wta_history
(
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payload           jsonb,
    _source_file      VARCHAR NOT NULL,
    _source_file_hash VARCHAR,
    _ingested_at      TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3)
);

