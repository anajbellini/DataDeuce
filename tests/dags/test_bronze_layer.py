"""Tests for the bronze_layer DAG.

Integrity tests parse the DAG file; task tests call each task's plain Python
function with fakes standing in for fetch, load and the database.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest
from airflow.dag_processing.dagbag import DagBag

from ingestion.fetch import FetchResult, SourceFile

DAGS_DIR = Path(__file__).parents[2] / "infra" / "airflow" / "dags"
MTIME = datetime(2026, 10, 8, 12, 50, 5, tzinfo=UTC)
NEWER_MTIME = datetime(2026, 10, 8, 13, 10, 0, tzinfo=UTC)


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


def test_summarize_runs_even_when_fetch_load_was_skipped(dag):
    assert dag.get_task("summarize").trigger_rule == "none_failed"


def test_dag_runs_one_at_a_time_without_backfilling(dag):
    assert dag.catchup is False
    assert dag.max_active_runs == 1


def _source_file(name, mtime=MTIME):
    return SourceFile(name=name, url=f"https://x/{name}", mtime=mtime)


def _listed(tour, ongoing, name, mtime=MTIME):
    return {
        "tour": tour,
        "ongoing": ongoing,
        "name": name,
        "url": f"https://x/{name}",
        "mtime": mtime,
    }


FILES_BY_KIND = {
    ("atp", True): [_source_file("ongoing_tourneys.csv")],
    ("atp", False): [_source_file("2025.csv")],
    ("wta", True): [_source_file("wta_ongoing_tourneys.csv")],
    ("wta", False): [_source_file("2025_wta.csv")],
}


def _patch_list_files(monkeypatch, dag, state, files_by_kind=FILES_BY_KIND):
    task = dag.get_task("list_files")
    patch_in_dag(
        monkeypatch,
        task,
        list_source_files=lambda tour, ongoing: files_by_kind[tour, ongoing],
        get_connection=FakeConnection,
        get_state=lambda conn: state,
    )
    return task


def test_list_files_returns_one_plain_dict_per_new_file_across_tours_and_kinds(
    dag, monkeypatch
):
    task = _patch_list_files(monkeypatch, dag, state={})

    assert task.python_callable() == [
        _listed("atp", True, "ongoing_tourneys.csv"),
        _listed("atp", False, "2025.csv"),
        _listed("wta", True, "wta_ongoing_tourneys.csv"),
        _listed("wta", False, "2025_wta.csv"),
    ]


def test_list_files_skips_files_whose_mtime_did_not_change(dag, monkeypatch):
    state = {"2025.csv": MTIME, "wta_ongoing_tourneys.csv": MTIME}
    task = _patch_list_files(monkeypatch, dag, state)

    names = [item["name"] for item in task.python_callable()]

    assert names == ["ongoing_tourneys.csv", "2025_wta.csv"]


def test_list_files_returns_files_whose_mtime_changed(dag, monkeypatch):
    updated = {
        **FILES_BY_KIND,
        ("atp", True): [_source_file("ongoing_tourneys.csv", NEWER_MTIME)],
    }
    task = _patch_list_files(
        monkeypatch, dag, {"ongoing_tourneys.csv": MTIME}, files_by_kind=updated
    )

    assert _listed("atp", True, "ongoing_tourneys.csv", NEWER_MTIME) in (
        task.python_callable()
    )


def test_list_files_logs_how_many_files_changed_and_how_many_were_skipped(
    dag, monkeypatch, caplog
):
    state = {"2025.csv": MTIME, "wta_ongoing_tourneys.csv": MTIME}
    task = _patch_list_files(monkeypatch, dag, state)

    with caplog.at_level(logging.INFO):
        task.python_callable()

    record = next(r for r in caplog.records if r.message == "source_files_filtered")
    assert record.files == 4
    assert record.files_changed == 2
    assert record.files_unchanged == 2


def test_list_files_returns_nothing_when_no_file_changed(dag, monkeypatch):
    state = {
        source_file.name: MTIME
        for source_files in FILES_BY_KIND.values()
        for source_file in source_files
    }
    task = _patch_list_files(monkeypatch, dag, state)

    assert task.python_callable() == []


def _patch_fetch_load(monkeypatch, dag, conn, calls, load_result=1):
    def fake_fetch(source_file):
        calls.append(("fetch", source_file))
        return FetchResult(content=b"a,b\n1,2\n", source_file=source_file.name)

    def fake_load(connection, tour, ongoing, source_file, content):
        calls.append(("load", connection, tour, ongoing, source_file, content))
        if isinstance(load_result, Exception):
            raise load_result
        return load_result

    def fake_save_state(connection, source_file, source_mtime):
        calls.append(("save_state", connection, source_file, source_mtime))

    task = dag.get_task("fetch_load")
    patch_in_dag(
        monkeypatch,
        task,
        fetch=fake_fetch,
        load=fake_load,
        save_state=fake_save_state,
        get_connection=lambda: conn,
    )
    return task


def test_fetch_load_fetches_loads_then_saves_the_state_for_its_file(dag, monkeypatch):
    conn = FakeConnection()
    calls = []
    task = _patch_fetch_load(monkeypatch, dag, conn, calls)

    rows = task.python_callable(_listed("wta", True, "wta_ongoing_tourneys.csv"))

    assert rows == 1
    assert calls == [
        ("fetch", _source_file("wta_ongoing_tourneys.csv")),
        ("load", conn, "wta", True, "wta_ongoing_tourneys.csv", b"a,b\n1,2\n"),
        ("save_state", conn, "wta_ongoing_tourneys.csv", MTIME),
    ]
    assert conn.closed


def test_fetch_load_saves_the_state_even_when_the_file_was_already_loaded(
    dag, monkeypatch
):
    conn = FakeConnection()
    calls = []
    task = _patch_fetch_load(monkeypatch, dag, conn, calls, load_result=0)

    rows = task.python_callable(_listed("atp", False, "2025.csv"))

    assert rows == 0
    assert ("save_state", conn, "2025.csv", MTIME) in calls


def test_fetch_load_does_not_save_the_state_when_the_load_fails(dag, monkeypatch):
    calls = []
    task = _patch_fetch_load(
        monkeypatch, dag, FakeConnection(), calls, load_result=RuntimeError("boom")
    )

    with pytest.raises(RuntimeError, match="boom"):
        task.python_callable(_listed("atp", False, "2025.csv"))

    assert [call[0] for call in calls] == ["fetch", "load"]


def test_summarize_logs_file_and_row_totals(dag, caplog):
    task = dag.get_task("summarize")

    with caplog.at_level(logging.INFO):
        task.python_callable([5, 0, 3])

    record = next(r for r in caplog.records if r.message == "bronze_load_summary")
    assert record.files == 3
    assert record.files_loaded == 2  # the 0 is a file that was already loaded
    assert record.rows_inserted == 8
