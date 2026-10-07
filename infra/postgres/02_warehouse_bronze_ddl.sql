create schema if not exists bronze;

-- creating table for <year>.csv
create table if not exists bronze.atp_history
(
    id BIGINT generated always as identity primary key,
    payload JSONB,
    _source_file VARCHAR not null,
    _source_file_hash VARCHAR,
    _ingested_at TIMESTAMP(3) default CURRENT_TIMESTAMP(3)
);

create index if not exists atp_history__source_file__source_file_hash_idx on bronze.atp_history (
    _source_file, _source_file_hash
);

-- creating table for ongoing_tourneys.csv
create table if not exists bronze.atp_ongoing (like bronze.atp_history including all);

-- creating table for *_wta.csv
create table if not exists bronze.wta_history (like bronze.atp_history including all);

-- creating table for wta_ongoing_tourneys.csv
create table if not exists bronze.wta_ongoing (like bronze.atp_history including all);
