"""Ingest ATP/WTA raw match data into the warehouse bronze schema."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from airflow.sdk import TriggerRule, dag, task

from ingestion.db import get_connection
from ingestion.fetch import SourceFile, fetch, list_source_files
from ingestion.load import load
from ingestion.state import get_state, has_changed, save_state
from logging_config import configure_logger

configure_logger()
logger = logging.getLogger(__name__)

_TOURS = ["atp", "wta"]


@dag(
    start_date=datetime(2026, 10, 1, tzinfo=UTC),
    schedule="0 */3 * * *",
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(seconds=30)},
)
def bronze_layer():
    """Fetch every ATP/WTA source file and load it into bronze."""

    @task
    def list_files():
        with get_connection() as conn:
            states = get_state(conn)

        listed = [
            (tour, ongoing, source)
            for tour in _TOURS
            for ongoing in [True, False]
            for source in list_source_files(tour, ongoing)
        ]
        changed = [
            {
                "tour": tour,
                "ongoing": ongoing,
                "name": source.name,
                "url": source.url,
                "mtime": source.mtime,
            }
            for tour, ongoing, source in listed
            if has_changed(source.name, source.mtime, states)
        ]

        logger.info(
            "source_files_filtered",
            extra={
                "files": len(listed),
                "files_changed": len(changed),
                "files_unchanged": len(listed) - len(changed),
            },
        )
        return changed

    @task
    def fetch_load(source: dict[str, Any]) -> int:
        fetched = fetch(
            SourceFile(
                name=source["name"],
                url=source["url"],
                mtime=source["mtime"],
            )
        )

        with get_connection() as conn:
            rows = load(
                conn,
                source["tour"],
                source["ongoing"],
                fetched.source_file,
                fetched.content,
            )

            save_state(conn, source["name"], source["mtime"])

            return rows

    @task(trigger_rule=TriggerRule.NONE_FAILED)
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
