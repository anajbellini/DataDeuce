"""Fetch ATP/WTA raw match data from the TennisMyLife API."""

import re
from dataclasses import dataclass

import requests

SOURCE_URL = "https://stats.tennismylife.org/api/data-files"
_ATP_REGEX = re.compile(r"\d{4}\.csv")
_WTA_REGEX = re.compile(r"\d{4}_wta\.csv")


@dataclass
class SourceFile:
    """A single source file listed by the TennisMyLife API."""

    name: str
    url: str


@dataclass
class FetchResult:
    """The raw content of a fetched source file, with its origin."""

    content: bytes
    source_file: str


def list_source_files(tour: str, source_url: str = SOURCE_URL) -> list[SourceFile]:
    """List the per-year raw match CSVs available for a tour.

    Args:
        tour: Either "atp" or "wta".
        source_url: The TennisMyLife data-files API endpoint.

    Returns:
        One SourceFile per matching year, excluding non-year files
        (e.g. Challenger, Qualifying, rankings snapshots).
    """
    pattern = _WTA_REGEX if tour == "wta" else _ATP_REGEX

    response = requests.get(source_url)
    response.raise_for_status()
    data = response.json()

    return [
        SourceFile(name=item["name"], url=item["url"])
        for item in data["files"]
        if pattern.fullmatch(item["name"])
    ]


def fetch(source_file: SourceFile) -> FetchResult:
    """Download a single source file's raw content.

    Args:
        source_file: The file to download, as returned by list_source_files.

    Returns:
        The raw CSV bytes and the originating file name.

    Raises:
        requests.HTTPError: If the download request fails.
    """
    response = requests.get(source_file.url)
    response.raise_for_status()
    content = response.content

    return FetchResult(content=content, source_file=source_file.name)
