"""Tests for src.ingestion.load.

Unit tests only — FakeConnection/FakeCursor stand in for psycopg, so no
real Postgres is touched.
"""

import hashlib
import json
import logging

import pytest

from src.ingestion import load as load_module
from src.ingestion.load import already_loaded, load


class FakeCursor:
    """Stands in for psycopg's cursor."""

    def __init__(self, fetchone_result=None):
        self.fetchone_result = fetchone_result
        self.executed = []
        self.executemany_calls = []

    def execute(self, query, params):
        self.executed.append((query, params))

    def executemany(self, query, params_seq):
        self.executemany_calls.append((query, list(params_seq)))

    def fetchone(self):
        return self.fetchone_result

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class FakeConnection:
    """Stands in for psycopg's connection."""

    def __init__(self, fetchone_result=None, raise_on_executemany=False):
        self.cursor_obj = FakeCursor(fetchone_result=fetchone_result)
        self.committed = False
        self.rolled_back = False

        if raise_on_executemany:

            def broken_executemany(query, params_seq):
                raise RuntimeError("insert failed")

            self.cursor_obj.executemany = broken_executemany

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


ATP_CSV = (
    b"winner_name,loser_name,score\nAlcaraz,Sinner,6-4 6-2\nSwiatek,Gauff,7-5 6-3\n"
)


def test_load_returns_row_count_matching_csv_rows():
    conn = FakeConnection()

    inserted = load(conn, "atp", False, "2024.csv", ATP_CSV)

    assert inserted == 2


def test_load_inserts_one_row_per_csv_row():
    conn = FakeConnection()

    load(conn, "atp", False, "2024.csv", ATP_CSV)

    [(_, params)] = conn.cursor_obj.executemany_calls
    assert len(params) == 2


def test_load_skips_rows_already_loaded():
    conn = FakeConnection(fetchone_result=(1,))  # already_loaded() finds a match

    inserted = load(conn, "atp", False, "2024.csv", ATP_CSV)

    assert inserted == 0
    assert conn.cursor_obj.executemany_calls == []


@pytest.mark.parametrize(
    ("tour", "ongoing", "expected_table"),
    [
        ("atp", False, "bronze.atp_history"),
        ("atp", True, "bronze.atp_ongoing"),
        ("wta", False, "bronze.wta_history"),
        ("wta", True, "bronze.wta_ongoing"),
    ],
)
def test_load_targets_the_table_for_its_tour_and_ongoing_flag(
    monkeypatch, tour, ongoing, expected_table
):
    tables = []

    def spy_already_loaded(conn, table, source_file, source_file_hash):
        tables.append(table)
        return False

    monkeypatch.setattr(load_module, "already_loaded", spy_already_loaded)

    load(FakeConnection(), tour, ongoing, "2024.csv", ATP_CSV)

    assert tables == [expected_table]


@pytest.mark.parametrize("content", [b"", b"winner_name,loser_name,score\n"])
def test_load_raises_and_inserts_nothing_for_a_file_with_no_data_rows(content):
    conn = FakeConnection()

    with pytest.raises(ValueError, match="2024.csv"):
        load(conn, "atp", False, "2024.csv", content)

    assert conn.cursor_obj.executemany_calls == []
    assert not conn.committed


def test_load_payload_schema_matches_csv_header():
    conn = FakeConnection()

    load(conn, "atp", False, "2024.csv", ATP_CSV)

    [(_, params)] = conn.cursor_obj.executemany_calls
    payload = json.loads(params[0][0])
    assert set(payload.keys()) == {"winner_name", "loser_name", "score"}


def test_load_never_inserts_null_source_file_or_hash():
    conn = FakeConnection()

    load(conn, "atp", False, "2024.csv", ATP_CSV)

    [(_, params)] = conn.cursor_obj.executemany_calls
    for _payload, source_file, source_file_hash in params:
        assert source_file is not None
        assert source_file_hash is not None


def test_load_source_file_hash_is_sha256_of_content():
    conn = FakeConnection()
    expected_hash = hashlib.sha256(ATP_CSV).hexdigest()

    load(conn, "atp", False, "2024.csv", ATP_CSV)

    [(_, params)] = conn.cursor_obj.executemany_calls
    assert all(source_file_hash == expected_hash for _, _, source_file_hash in params)


def test_load_preserves_extra_fields_from_ragged_row():
    ragged_csv = b"a,b\n1,2,3\n"  # one extra field beyond the header

    conn = FakeConnection()
    load(conn, "atp", False, "2024.csv", ragged_csv)

    [(_, params)] = conn.cursor_obj.executemany_calls
    payload = json.loads(params[0][0])
    assert payload["_extra_fields"] == ["3"]


def test_load_fills_missing_trailing_fields_with_none():
    short_row_csv = b"a,b,c\n1,2\n"  # row is missing the trailing "c" value

    conn = FakeConnection()
    load(conn, "atp", False, "2024.csv", short_row_csv)

    [(_, params)] = conn.cursor_obj.executemany_calls
    payload = json.loads(params[0][0])
    assert payload == {"a": "1", "b": "2", "c": None}


def test_load_rolls_back_and_reraises_on_insert_failure():
    conn = FakeConnection(raise_on_executemany=True)

    with pytest.raises(RuntimeError):
        load(conn, "atp", False, "2024.csv", ATP_CSV)

    assert conn.rolled_back is True
    assert conn.committed is False


def test_already_loaded_queries_with_source_file_and_hash():
    conn = FakeConnection(fetchone_result=(1,))

    result = already_loaded(conn, "bronze.atp_history", "2024.csv", "somehash")

    assert result is True
    [(_, params)] = conn.cursor_obj.executed
    assert params == ("2024.csv", "somehash")


def test_already_loaded_returns_false_when_no_match():
    conn = FakeConnection(fetchone_result=None)

    result = already_loaded(conn, "bronze.atp_history", "2024.csv", "somehash")

    assert result is False


def _record(caplog, message):
    return next(r for r in caplog.records if r.message == message)


@pytest.mark.parametrize("ongoing", [True, False])
def test_load_logs_the_ongoing_flag_when_rows_are_inserted(caplog, ongoing):
    with caplog.at_level(logging.INFO):
        load(FakeConnection(), "atp", ongoing, "2024.csv", ATP_CSV)

    record = _record(caplog, "rows_inserted")
    assert record.ongoing is ongoing
    assert record.rows == 2


@pytest.mark.parametrize("ongoing", [True, False])
def test_load_logs_the_ongoing_flag_when_the_file_was_already_loaded(caplog, ongoing):
    conn = FakeConnection(fetchone_result=(1,))

    with caplog.at_level(logging.INFO):
        load(conn, "atp", ongoing, "2024.csv", ATP_CSV)

    assert _record(caplog, "skip_already_loaded").ongoing is ongoing


@pytest.mark.parametrize("ongoing", [True, False])
def test_load_logs_the_ongoing_flag_when_the_insert_fails(caplog, ongoing):
    conn = FakeConnection(raise_on_executemany=True)

    with caplog.at_level(logging.INFO), pytest.raises(RuntimeError):
        load(conn, "atp", ongoing, "2024.csv", ATP_CSV)

    assert _record(caplog, "insert_failed").ongoing is ongoing
