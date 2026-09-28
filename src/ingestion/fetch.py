import re
from dataclasses import dataclass

import requests

SOURCE_URL = "https://stats.tennismylife.org/api/data-files"
_ATP_REGEX = re.compile(r"\d{4}\.csv")
_WTA_REGEX = re.compile(r"\d{4}_wta\.csv")


@dataclass
class SourceFile:
    name: str
    url: str


@dataclass
class FetchResult:
    content: bytes
    source_file: str


def list_source_files(tour: str, source_url: str) -> list[SourceFile]:
    pattern = _WTA_REGEX if tour == "wta" else _ATP_REGEX

    response = requests.get(source_url).json()
    response.raise_for_status()

    return [
        SourceFile(name=item["name"], url=item["url"])
        for item in response["files"]
        if pattern.fullmatch(item["name"])
    ]
