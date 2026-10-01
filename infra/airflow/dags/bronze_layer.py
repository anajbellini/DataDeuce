"""Ingest ATP/WTA raw match data into the warehouse bronze schema."""

import logging
from datetime import UTC, datetime, timedelta

from airflow.sdk import dag, task

from ingestion.fetch import SourceFile, fetch, list_source_files
from ingestion.load import get_connection, load
from logging_config import configure_logger

configure_logger()
logger = logging.getLogger(__name__)

_TOURS = ["atp", "wta"]


@dag(
    start_date=datetime(2026, 10, 1, tzinfo=UTC),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(seconds=30)},
)
def bronze_layer():
    """Fetch every ATP/WTA source file and load it into bronze."""

    @task
    def list_files():
        return [
            {"tour": tour, "name": source.name, "url": source.url}
            for tour in _TOURS
            for source in list_source_files(tour)
        ]

    @task
    def fetch_load(source: dict[str, str]) -> int:
        fetched = fetch(SourceFile(name=source["name"], url=source["url"]))

        with get_connection() as conn:
            return load(conn, source["tour"], fetched.source_file, fetched.content)

    @task
    def summarize(row_counts) -> None:
        row_counts = list(row_counts)
        logger.info(
            "bronze_load_summary",
            extra={
                "files": len(row_counts),
                "files_loaded": sum(count > 0 for count in row_counts),
                "rows_inserted": sum(row_counts),
            },
        )

    summarize(fetch_load.expand(source=list_files()))


_ = bronze_layer()
