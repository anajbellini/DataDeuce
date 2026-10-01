"""Ingest ATP/WTA raw match data into the warehouse bronze schema."""

from airflow.sdk import dag, task

from ingestion.fetch import fetch, list_source_files
from ingestion.load import TABLES, get_connection, load

_TOURS = ["atp", "wta"]


@dag()
def bronze_layer():
    """Fetch every ATP/WTA source file and load it into bronze."""

    @task
    def list_files():
        return [
            {"tour": tour, "file": source}
            for tour in _TOURS
            for source in list_source_files(tour)
        ]

    @task
    def fetch_load(source: dict) -> None:
        fetched = fetch(source_file=source)

        with get_connection() as conn:
            load(conn, TABLES[source["tour"]], fetched.source_file, fetched.content)

    fetch_load.expand(source=list_files())


bronze_layer()
