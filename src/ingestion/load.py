"""Load fetched ATP/WTA raw CSVs into the warehouse-postgres bronze schema."""

import csv
import hashlib
import io
import json
import logging

import psycopg
from psycopg import sql

logger = logging.getLogger(__name__)

TABLES = {
    ("atp", True): "bronze.atp_ongoing",
    ("atp", False): "bronze.atp_history",
    ("wta", True): "bronze.wta_ongoing",
    ("wta", False): "bronze.wta_history",
}


def already_loaded(
    conn: psycopg.Connection, table: str, source_file: str, source_file_hash: str
) -> bool:
    """Check if (_source_file, _source_file_hash) already exists before inserting.

    Args:
        conn: The database connection.
        table: The table to check.
        source_file: The source file path.
        source_file_hash: The hash of the source file.

    Returns:
        True if the (_source_file, _source_file_hash) pair already exists, False otherwise.
    """
    query = sql.SQL(
        "SELECT 1 FROM {table} WHERE _source_file = %s AND _source_file_hash = %s LIMIT 1"
    ).format(table=sql.Identifier(*table.split(".")))

    with conn.cursor() as cursor:
        cursor.execute(query, (source_file, source_file_hash))
        return cursor.fetchone() is not None


def load(
    conn: psycopg.Connection, tour: str, ongoing: bool, source_file: str, content: bytes
) -> int:
    """Hash content (sha256), skip if already loaded, else parse CSV rows and insert as jsonb payload.

    Args:
        conn: The database connection.
        tour: Either "atp" or "wta", used with ongoing to resolve the target
            bronze table.
        ongoing: True for the in-progress tournaments file, False for the
            per-year history files.
        source_file: The source file name (e.g. "2025.csv").
        content: The raw CSV bytes, as returned by fetch().

    Returns:
        Rows inserted, or 0 if the file was already loaded.

    Raises:
        ValueError: If the file has no data rows.
    """
    table = TABLES[tour, ongoing]
    source_file_hash = hashlib.sha256(content).hexdigest()

    if already_loaded(conn, table, source_file, source_file_hash):
        logger.info(
            "skip_already_loaded", extra={"tour": tour, "source_file": source_file}
        )
        return 0

    rows = list(
        csv.DictReader(io.StringIO(content.decode("utf-8")), restkey="_extra_fields")
    )

    if not rows:
        raise ValueError(f"{source_file} has no data rows")

    query = sql.SQL(
        "INSERT INTO {table} (payload, _source_file, _source_file_hash) VALUES (%s, %s, %s)"
    ).format(table=sql.Identifier(*table.split(".")))

    try:
        with conn.cursor() as cursor:
            cursor.executemany(
                query,
                [(json.dumps(row), source_file, source_file_hash) for row in rows],
            )
        conn.commit()
        logger.info(
            "rows_inserted",
            extra={"tour": tour, "source_file": source_file, "rows": len(rows)},
        )
    except Exception:
        conn.rollback()
        logger.exception(
            "insert_failed", extra={"tour": tour, "source_file": source_file}
        )
        raise

    return len(rows)
