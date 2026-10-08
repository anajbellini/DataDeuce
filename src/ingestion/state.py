"""Track which source files were already ingested, via meta.source_file_state."""

from datetime import datetime

import psycopg


def get_state(conn: psycopg.Connection) -> dict[str, datetime]:
    """Read the last ingested mtime of every source file.

    Args:
        conn: The database connection.

    Returns:
        A mapping of source_file to source_mtime, empty if nothing was ingested yet.
    """
    with conn.cursor() as cursor:
        cursor.execute("select source_file, source_mtime from meta.source_file_state")
        return dict(cursor.fetchall())
