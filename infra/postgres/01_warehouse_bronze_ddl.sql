CREATE SCHEMA IF NOT EXISTS bronze;

-- creating table for <year>.csv
CREATE TABLE IF NOT EXISTS bronze.atp_history
(
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payload           jsonb,
    _source_file      VARCHAR NOT NULL,
    _source_file_hash VARCHAR,
    _ingested_at      TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3)
);

CREATE INDEX IF NOT EXISTS atp_history__source_file__source_file_hash_idx ON bronze.atp_history (_source_file, _source_file_hash);

-- creating table for ongoing_tourneys.csv
CREATE TABLE IF NOT EXISTS bronze.atp_ongoing (LIKE bronze.atp_history INCLUDING ALL);

-- creating table for *_wta.csv
CREATE TABLE IF NOT EXISTS bronze.wta_history (LIKE bronze.atp_history INCLUDING ALL);

-- creating table for wta_ongoing_tourneys.csv
CREATE TABLE IF NOT EXISTS bronze.wta_ongoing (LIKE bronze.atp_history INCLUDING ALL);
