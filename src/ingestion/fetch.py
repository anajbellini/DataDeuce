"""Fetch ATP/WTA raw match data from the TennisMyLife API."""

import logging
import re
from dataclasses import dataclass

import requests
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

SOURCE_URL = "https://stats.tennismylife.org/api/data-files"
_ATP_REGEX = re.compile(r"\d{4}\.csv")
_WTA_REGEX = re.compile(r"\d{4}_wta\.csv")
_RETRYABLE_STATUS_CODES = {408, 429}


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

    source_files = [
        SourceFile(name=item["name"], url=item["url"])
        for item in data["files"]
        if pattern.fullmatch(item["name"])
    ]
    logger.info("source_files_listed", extra={"tour": tour, "count": len(source_files)})

    return source_files


def _is_transient(exc: BaseException) -> bool:
    """Decide whether a fetch failure is worth retrying.

    True for connection drops, timeouts, 5xx, and _RETRYABLE_STATUS_CODES;
    false for other 4xx, which retrying won't fix.

    Args:
        exc: The exception raised by the failed request.

    Returns:
        True if the request should be retried.
    """
    if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
        return True
    if not isinstance(exc, requests.HTTPError) or exc.response is None:
        return False
    status_code = exc.response.status_code
    return status_code >= 500 or status_code in _RETRYABLE_STATUS_CODES


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(_is_transient),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def fetch(source_file: SourceFile) -> FetchResult:
    """Download a single source file's raw content.

    Args:
        source_file: The file to download, as returned by list_source_files.

    Returns:
        The raw CSV bytes and the originating file name.

    Raises:
        requests.HTTPError: If the download request fails.
    """
    logger.info("fetch_started", extra={"source_file": source_file.name})

    response = requests.get(source_file.url)
    response.raise_for_status()
    content = response.content

    return FetchResult(content=content, source_file=source_file.name)
