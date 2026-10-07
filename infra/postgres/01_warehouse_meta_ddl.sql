create schema if not exists meta;

-- creating state table to safely manage incremental loads
create table if not exists meta.source_file_state
(
    source_file VARCHAR not null primary key,
    source_mtime TIMESTAMPTZ not null,
    _loaded_at TIMESTAMP(3) default CURRENT_TIMESTAMP(3)
);
