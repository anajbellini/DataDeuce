"""Load fetched ATP/WTA raw CSVs into the warehouse-postgres bronze schema."""

from os import environ, getenv

import psycopg
from dotenv import load_dotenv
from psycopg import sql

load_dotenv()

TABLES = {"atp": "bronze.atp_history", "wta": "bronze.wta_history"}


def get_connection() -> psycopg.Connection:
    """Open a connection to warehouse-postgres using WAREHOUSE_DB_* env vars.

    Host and port default to the local docker-compose mapping; user,
    password, and database name are required and raise KeyError if unset.

    Returns:
        An open connection to the warehouse-postgres database.
    """
    return psycopg.connect(
        host=getenv("WAREHOUSE_DB_HOST", "localhost"),
        port=getenv("WAREHOUSE_DB_PORT", "5433"),
        dbname=environ["WAREHOUSE_DB_NAME"],
        user=environ["WAREHOUSE_DB_USER"],
        password=environ["WAREHOUSE_DB_PASSWORD"],
    )


def already_loaded(
    db_conn: psycopg.Connection, table: str, source_file: str, source_file_hash: str
) -> bool:
    """Check if (_source_file, _source_file_hash) before inserting already exists.

    Args:
        db_conn: The database connection.
        table: The table to check.
        source_file: The source file path.
        source_file_hash: The hash of the source file.

    Returns:
        True if the (_source_file, _source_file_hash) pair already exists, False otherwise.
    """
    query = sql.SQL(
        "SELECT 1 FROM {table} WHERE _source_file = %s AND _source_file_hash = %s LIMIT 1"
    ).format(table=sql.Identifier(*table.split(".")))

    with db_conn.cursor() as cursor:
        cursor.execute(query, (source_file, source_file_hash))
        return cursor.fetchone() is not None
