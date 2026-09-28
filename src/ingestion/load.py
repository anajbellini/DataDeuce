"""Load fetched ATP/WTA raw CSVs into the warehouse-postgres bronze schema."""

from os import environ, getenv

import psycopg
from dotenv import load_dotenv

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
