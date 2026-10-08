"""Tests for src.ingestion.fetch."""

from datetime import UTC, datetime

import pytest
import requests

from src.ingestion.fetch import SourceFile, fetch, list_source_files


class FakeResponse:
    """Stands in for requests.Response, without making a real HTTP call."""

    def __init__(self, json_data=None, content=b"", status_code=200):
        self._json_data = json_data
        self.content = content
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)


def _entry(name):
    return {
        "name": name,
        "url": f"https://example.com/{name}",
        "mtime": "2026-10-08T12:50:05.829Z",
    }


FILES_PAYLOAD = {
    "files": [
        _entry(name)
        for name in [
            "2023.csv",
            "2024.csv",
            "2024_wta.csv",
            "2024_qual_chall.csv",
            "rankings_2024.csv",
            "ongoing_tourneys.csv",
            "wta_ongoing_tourneys.csv",
            "challenger_ongoing_tourneys.csv",
            ".wta_ongoing_before_level_fix_060335.csv",
        ]
    ]
}

MTIME = datetime(2026, 10, 8, 12, 50, 5, 829000, tzinfo=UTC)


@pytest.fixture
def files_api(monkeypatch):
    monkeypatch.setattr(
        requests, "get", lambda url: FakeResponse(json_data=FILES_PAYLOAD)
    )


def _names(source_files):
    return [source_file.name for source_file in source_files]


def test_list_source_files_returns_only_atp_history_files(files_api):
    result = list_source_files("atp", ongoing=False)

    assert _names(result) == ["2023.csv", "2024.csv"]


def test_list_source_files_returns_only_wta_history_files(files_api):
    result = list_source_files("wta", ongoing=False)

    assert _names(result) == ["2024_wta.csv"]


def test_list_source_files_returns_only_atp_ongoing_file(files_api):
    result = list_source_files("atp", ongoing=True)

    assert _names(result) == ["ongoing_tourneys.csv"]


def test_list_source_files_returns_only_wta_ongoing_file(files_api):
    result = list_source_files("wta", ongoing=True)

    assert _names(result) == ["wta_ongoing_tourneys.csv"]


@pytest.mark.parametrize("tour", ["atp", "wta"])
def test_list_source_files_ongoing_excludes_lookalike_files(files_api, tour):
    names = _names(list_source_files(tour, ongoing=True))

    assert "challenger_ongoing_tourneys.csv" not in names
    assert ".wta_ongoing_before_level_fix_060335.csv" not in names


@pytest.mark.parametrize("tour", ["atp", "wta"])
def test_list_source_files_ongoing_flag_switches_between_ongoing_and_history(
    files_api, tour
):
    ongoing = set(_names(list_source_files(tour, ongoing=True)))
    history = set(_names(list_source_files(tour, ongoing=False)))

    assert ongoing
    assert history
    assert ongoing.isdisjoint(history)


def test_list_source_files_builds_source_file_with_url_and_utc_mtime(files_api):
    result = list_source_files("atp", ongoing=True)

    assert result == [
        SourceFile(
            name="ongoing_tourneys.csv",
            url="https://example.com/ongoing_tourneys.csv",
            mtime=MTIME,
        )
    ]


def test_list_source_files_raises_on_http_error(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda url: FakeResponse(status_code=500))

    with pytest.raises(requests.HTTPError):
        list_source_files("atp", ongoing=False)


def test_fetch_returns_content_and_source_file(monkeypatch):
    source_file = SourceFile(
        name="2024.csv", url="https://example.com/2024.csv", mtime=MTIME
    )
    monkeypatch.setattr(
        requests, "get", lambda url: FakeResponse(content=b"raw,csv,bytes")
    )

    result = fetch(source_file)

    assert result.content == b"raw,csv,bytes"
    assert result.source_file == "2024.csv"


def test_fetch_raises_on_http_error(monkeypatch):
    source_file = SourceFile(
        name="2024.csv", url="https://example.com/2024.csv", mtime=MTIME
    )
    monkeypatch.setattr(requests, "get", lambda url: FakeResponse(status_code=404))

    with pytest.raises(requests.HTTPError):
        fetch(source_file)
