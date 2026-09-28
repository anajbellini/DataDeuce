from dataclasses import dataclass

import requests


@dataclass
class SourceFile:
    name: str
    url: str


@dataclass
class FetchResult:
    content: bytes
    source_file: str


def list_source_files(tour: str, source_url: str) -> list[SourceFile]:
    response = requests.get(source_url).json()
    response.raise_for_status()

    return [SourceFile(name=file["name"], url=file["url"]) for file in response]
