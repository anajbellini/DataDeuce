"""Tests for the bronze_layer DAG.

Integrity tests parse the DAG file; task tests call each task's plain Python
function with fakes standing in for fetch, load and the database.
"""

import logging
from pathlib import Path

import pytest
from airflow.dag_processing.dagbag import DagBag

from ingestion.fetch import FetchResult, SourceFile

DAGS_DIR = Path(__file__).parents[2] / "infra" / "airflow" / "dags"


@pytest.fixture(scope="module")
def dagbag():
    return DagBag(dag_folder=str(DAGS_DIR))


@pytest.fixture(scope="module")
def dag(dagbag):
    return dagbag.dags["bronze_layer"]


class FakeConnection:
    """Stands in for psycopg's connection, tracking that it was closed."""

    def __init__(self):
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.closed = True
        return False


def patch_in_dag(monkeypatch, task, **replacements):
    """Replace names used by a task's function, in the DAG module's namespace."""
    for name, replacement in replacements.items():
        monkeypatch.setitem(task.python_callable.__globals__, name, replacement)


def test_dag_file_has_no_import_errors(dagbag):
    assert dagbag.import_errors == {}


def test_dag_has_the_expected_tasks(dag):
    assert set(dag.task_ids) == {"list_files", "fetch_load", "summarize"}


def test_tasks_run_in_order(dag):
    assert dag.get_task("list_files").downstream_task_ids == {"fetch_load"}
    assert dag.get_task("fetch_load").downstream_task_ids == {"summarize"}


def test_fetch_load_is_mapped_once_per_file(dag):
    assert dag.get_task("fetch_load").is_mapped


def test_dag_runs_one_at_a_time_without_backfilling(dag):
    assert dag.catchup is False
    assert dag.max_active_runs == 1


def test_list_files_returns_one_plain_dict_per_file_across_both_tours(dag, monkeypatch):
    files_by_tour = {
        "atp": [SourceFile(name="2025.csv", url="https://x/2025.csv")],
        "wta": [SourceFile(name="2025_wta.csv", url="https://x/2025_wta.csv")],
    }
    task = dag.get_task("list_files")
    patch_in_dag(monkeypatch, task, list_source_files=files_by_tour.__getitem__)

    assert task.python_callable() == [
        {"tour": "atp", "name": "2025.csv", "url": "https://x/2025.csv"},
        {"tour": "wta", "name": "2025_wta.csv", "url": "https://x/2025_wta.csv"},
    ]


def test_fetch_load_fetches_the_file_and_loads_it_for_its_tour(dag, monkeypatch):
    conn = FakeConnection()
    fetch_calls, load_calls = [], []

    def fake_fetch(source_file):
        fetch_calls.append(source_file)
        return FetchResult(content=b"a,b\n1,2\n", source_file=source_file.name)

    def fake_load(connection, tour, source_file, content):
        load_calls.append((connection, tour, source_file, content))
        return 1

    task = dag.get_task("fetch_load")
    patch_in_dag(
        monkeypatch,
        task,
        fetch=fake_fetch,
        load=fake_load,
        get_connection=lambda: conn,
    )

    rows = task.python_callable(
        {"tour": "wta", "name": "2025_wta.csv", "url": "https://x/2025_wta.csv"}
    )

    assert rows == 1
    assert fetch_calls == [
        SourceFile(name="2025_wta.csv", url="https://x/2025_wta.csv")
    ]
    assert load_calls == [(conn, "wta", "2025_wta.csv", b"a,b\n1,2\n")]
    assert conn.closed


def test_summarize_logs_file_and_row_totals(dag, caplog):
    task = dag.get_task("summarize")

    with caplog.at_level(logging.INFO):
        task.python_callable([5, 0, 3])

    record = next(r for r in caplog.records if r.message == "bronze_load_summary")
    assert record.files == 3
    assert record.files_loaded == 2  # the 0 is a file that was already loaded
    assert record.rows_inserted == 8
