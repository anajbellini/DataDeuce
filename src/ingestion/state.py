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


def has_changed(
    source_file: str, source_mtime: datetime, state: dict[str, datetime]
) -> bool:
    """Check if a source file differs from the last ingested version.

    Compares with != rather than > so a source that moves its mtime backwards
    (e.g. a restored backup) is still detected.

    Args:
        source_file: The source file name (e.g. "2025.csv").
        source_mtime: The file mtime reported by the source API.
        state: The mapping returned by get_state().

    Returns:
        True if the file was never ingested or its mtime differs, False otherwise.
    """
    return state.get(source_file) != source_mtime


def save_state(
    conn: psycopg.Connection, source_file: str, source_mtime: datetime
) -> None:
    """Record the mtime of a source file after it was loaded successfully.

    Inserts the file on first sight and updates its mtime and processed_at after
    that. Call it only once the load succeeded, so a failed load is retried.

    Args:
        conn: The database connection.
        source_file: The source file name (e.g. "2025.csv").
        source_mtime: The file mtime reported by the source API.
    """
    query = """insert into meta.source_file_state (source_file, source_mtime)
    values (%s, %s)
    on conflict (source_file) do update set source_mtime = excluded.source_mtime, processed_at = now()"""

    with conn.cursor() as cursor:
        cursor.execute(
            query,
            (source_file, source_mtime),
        )

    conn.commit()
