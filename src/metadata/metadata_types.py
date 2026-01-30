from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from returns.maybe import Maybe

from .json_tools import PathSpec


class PublicationDate(TypedDict):
    year: int
    month: int
    day: int


class Author(TypedDict):
    name: str
    affiliation: str


class Bibliographic(TypedDict):
    title: str
    page_start: str
    page_end: str
    volume_number: str


class Urls(TypedDict):
    file: str
    self: str


class SimplifiedMetadata(TypedDict):
    title: str
    abstract: str
    publication_date: PublicationDate
    authors: list[Author]
    bibliographic: Bibliographic
    language: str
    urls: Urls

def default_simplified_metadata() -> SimplifiedMetadata:
    return {
        "title": "",
        "abstract": "",
        "publication_date": {
            "year": -1, "month": -1, "day": -1
        },
        "authors": [],
        "bibliographic": {
            "title": "",
            "page_start": "",
            "page_end": "",
            "volume_number": ""
        },
        "language": "ja",
        "urls": {
            "file": "",
            "self": ""
        }
    }


class AffiliationEntry(TypedDict):
    subitem_text_value: str


@dataclass(frozen=True)
class CandidatePathsForMetaData:
    """Paths are candidate traversals expressed as dot/index strings."""

    title: list[PathSpec]
    abstract: list[PathSpec]
    publication_date: list[PathSpec]
    language: list[PathSpec]
    file_url: list[PathSpec]
    authors_item_metadata: list[PathSpec]
    authors_creator: list[PathSpec]
    affiliations: list[PathSpec]


PATHS = CandidatePathsForMetaData(
    title=[
        "_item_metadata.item_title",
        "title[0]",
    ],
    abstract=[
        "_item_metadata.item_18_description_7.attribute_value_mlt[0].subitem_description",
        "description[0].value",
    ],
    publication_date=[
        "_item_metadata.pubdate.attribute_value",
        "publish_date",
        "date[0].value",
    ],
    language=[
        "_item_metadata.item_language.attribute_value_mlt[0].subitem_language",
        "language[0]",
    ],
    file_url=[
        "_files_info[0].url",
        "_item_metadata.item_file_price.attribute_value_mlt[0].url.url",
    ],
    authors_item_metadata=[
        "_item_metadata.item_18_creator_5.attribute_value_mlt",
    ],
    authors_creator=[
        "creator.creatorName",
    ],
    affiliations=[
        "_item_metadata.item_18_text_3.attribute_value_mlt",
    ],
)
