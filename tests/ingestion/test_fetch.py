"""Tests for src.ingestion.fetch."""

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


FILES_PAYLOAD = {
    "files": [
        {"name": "2023.csv", "url": "https://example.com/2023.csv"},
        {"name": "2024.csv", "url": "https://example.com/2024.csv"},
        {"name": "2024_wta.csv", "url": "https://example.com/2024_wta.csv"},
        {"name": "2024_qual_chall.csv", "url": "https://example.com/qual_chall.csv"},
        {"name": "rankings_2024.csv", "url": "https://example.com/rankings.csv"},
    ]
}


def test_list_source_files_returns_only_atp_year_files(monkeypatch):
    monkeypatch.setattr(
        requests, "get", lambda url: FakeResponse(json_data=FILES_PAYLOAD)
    )

    result = list_source_files("atp")

    assert result == [
        SourceFile(name="2023.csv", url="https://example.com/2023.csv"),
        SourceFile(name="2024.csv", url="https://example.com/2024.csv"),
    ]


def test_list_source_files_returns_only_wta_year_files(monkeypatch):
    monkeypatch.setattr(
        requests, "get", lambda url: FakeResponse(json_data=FILES_PAYLOAD)
    )

    result = list_source_files("wta")

    assert result == [
        SourceFile(name="2024_wta.csv", url="https://example.com/2024_wta.csv"),
    ]


def test_list_source_files_raises_on_http_error(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda url: FakeResponse(status_code=500))

    with pytest.raises(requests.HTTPError):
        list_source_files("atp")


def test_fetch_returns_content_and_source_file(monkeypatch):
    source_file = SourceFile(name="2024.csv", url="https://example.com/2024.csv")
    monkeypatch.setattr(
        requests, "get", lambda url: FakeResponse(content=b"raw,csv,bytes")
    )

    result = fetch(source_file)

    assert result.content == b"raw,csv,bytes"
    assert result.source_file == "2024.csv"


def test_fetch_raises_on_http_error(monkeypatch):
    source_file = SourceFile(name="2024.csv", url="https://example.com/2024.csv")
    monkeypatch.setattr(requests, "get", lambda url: FakeResponse(status_code=404))

    with pytest.raises(requests.HTTPError):
        fetch(source_file)
