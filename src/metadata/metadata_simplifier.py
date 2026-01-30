from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, TypeGuard

from returns.maybe import Maybe, Nothing, Some
from returns.result import Failure, Result, Success

from .json_tools import first_failure as _first_failure
from .json_tools import first_present as _first_present
from .json_tools import required as _required
from .metadata_types import AffiliationEntry, Author, Bibliographic, PATHS, SimplifiedMetadata

def _is_affiliation_entry(entry: Any) -> TypeGuard[AffiliationEntry]:
    """Check if an entry has a valid affiliation shape."""
    return isinstance(entry, dict) and isinstance(entry.get("subitem_text_value"), str)


def _biblio_path(suffix: str) -> str:
    """Build a standard path for bibliographic metadata fields."""
    return f"_item_metadata.item_18_biblio_info_10.attribute_value_mlt[0].{suffix}"


def _bibliographic(metadata: dict[str, Any], warnings:list[str]) -> Result[Bibliographic, str]:
    """Extract required bibliographic fields."""
    title = _required(
        data=metadata,
        candidate_paths=[
            _biblio_path("bibliographic_titles[0].bibliographic_title"),
            "sourceTitle[0]",
        ],
        field_name="bibliographic.title",
    )
    page_start = _required(
        data=metadata,
        candidate_paths=[
            _biblio_path("bibliographicPageStart"),
            "pageStart[0]",
        ],
        field_name="bibliographic.page_start",
    )
    page_end = _required(
        data=metadata,
        candidate_paths=[
            _biblio_path("bibliographicPageEnd"),
            "pageEnd[0]",
        ],
        field_name="bibliographic.page_end",
    )
    volume_number = _required(
        data=metadata,
        candidate_paths=[
            _biblio_path("bibliographicVolumeNumber"),
            "volume[0]",
        ],
        field_name="bibliographic.volume_number",
    )
    failure = _first_failure([title, page_start, page_end, volume_number])
    if isinstance(failure, Failure):
        return failure
    return Success(
        {
            "title": title.unwrap(),
            "page_start": page_start.unwrap(),
            "page_end": page_end.unwrap(),
            "volume_number": volume_number.unwrap(),
        }
    )


def _parse_date(value: str) -> Result[date, str]:
    """Parse an ISO date string into a date Result."""
    try:
        return Success(date.fromisoformat(value))
    except ValueError:
        return Failure(f"invalid date: {value}")


def _author_names_from_item_metadata(metadata: dict[str, Any], warnings:list[str]) -> Maybe[list[str]]:
    """Extract author names from item metadata entries."""
    value = _first_present(metadata, PATHS.authors_item_metadata)
    match value:
        case Some(entries):
            if not isinstance(entries, list):
                return Nothing
            names: list[str] = []
            for entry in entries:
                if not isinstance(entry, dict):
                    return Nothing
                name = entry.get("creatorNames", {}).get("creatorName")
                if not isinstance(name, str):
                    return Nothing
                names.append(name)
            return Some(names) if names else Nothing
        case _:
            return Nothing


def _author_names_from_creator(metadata: dict[str, Any], warnings:list[str]) -> Maybe[list[str]]:
    """Extract author names from creator name lists."""
    value = _first_present(metadata, PATHS.authors_creator)
    match value:
        case Some(entries):
            if not isinstance(entries, list) or not entries:
                return Nothing
            if not all(isinstance(entry, str) for entry in entries):
                return Nothing
            return Some(list(entries))
        case _:
            return Nothing


def _author_names(metadata: dict[str, Any], warnings:list[str]) -> Result[list[str], str]:
    """Resolve author names from supported metadata shapes."""
    for extractor in (_author_names_from_item_metadata, _author_names_from_creator):
        result = extractor(metadata, warnings)
        if isinstance(result, Some):
            return Success(result.unwrap())
    return Failure("missing authors")


def _authors(metadata: dict[str, Any], warnings:list[str]) -> Result[list[Author], str]:
    """Extract authors and align optional affiliations by index."""
    names_result = _author_names(metadata, warnings)
    if isinstance(names_result, Failure):
        return names_result
    names = names_result.unwrap()

    affiliations_value_maybe = _first_present(metadata, PATHS.affiliations)
    if affiliations_value_maybe is Nothing:
        return Failure("missing affiliations")
    affiliations_value = affiliations_value_maybe.unwrap()
    if not isinstance(affiliations_value, list):
        return Failure("invalid affiliations")
    affiliations = [
        entry["subitem_text_value"]
        for entry in affiliations_value
        if _is_affiliation_entry(entry)
    ]
    if len(affiliations) < len(names):
        authors: list[Author] = []
        for index, name in enumerate(names):
            authors.append({"name": name, "affiliation": affiliations[index] if index < len(affiliations) else "Missing"})
        warnings.append("メタデータの著者の数と所属の数があっていませんでした。所属をMissingと記録します。")
        return Success(authors)    

    authors: list[Author] = []
    for index, name in enumerate(names):
        authors.append({"name": name, "affiliation": affiliations[index]})
    return Success(authors)


def simplify_metadata(payload: dict[str, Any], warnings:list[str]) -> Result[SimplifiedMetadata, str]:
    """Simplify a metadata payload into a normalized structure."""
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return Failure("missing metadata")

    title_result = _required(data=metadata, candidate_paths=PATHS.title, field_name="title")
    abstract_result = _required(
        data=metadata,
        candidate_paths=PATHS.abstract,
        field_name="abstract",
    )
    date_value_result = _required(
        data=metadata,
        candidate_paths=PATHS.publication_date,
        field_name="publication date",
    )
    authors_result = _authors(metadata, warnings)
    language_result = _required(
        data=metadata,
        candidate_paths=PATHS.language,
        field_name="language",
    )
    file_url_result = _required(
        data=metadata,
        candidate_paths=PATHS.file_url,
        field_name="file url",
    )
    self_url_result = _required(
        data=payload,
        candidate_paths=["links.self"],
        field_name="links.self",
    )

    if isinstance(date_value_result, Failure):  return date_value_result
    parsed_date_result = _parse_date(date_value_result.unwrap())
    if isinstance(parsed_date_result, Failure): return parsed_date_result

    failure = _first_failure(
        [
            title_result,
            abstract_result,
            authors_result,
            language_result,
            file_url_result,
            self_url_result,
        ]
    )
    if isinstance(failure, Failure): return failure

    bibliographic_result = _bibliographic(metadata, warnings)
    if isinstance(bibliographic_result, Failure):
        return bibliographic_result
    bibliographic = bibliographic_result.unwrap()

    parsed_date = parsed_date_result.unwrap()
    return Success(
        {
            "title": title_result.unwrap(),
            "abstract": abstract_result.unwrap(),
            "publication_date": {
                "year": parsed_date.year,
                "month": parsed_date.month,
                "day": parsed_date.day,
            },
            "authors": authors_result.unwrap(),
            "bibliographic": bibliographic,
            "language": language_result.unwrap(),
            "urls": {
                "file": file_url_result.unwrap(),
                "self": self_url_result.unwrap(),
            },
        }
    )

def simplify_metadata_of_paper(paper_pdf: Path):
    recid = paper_pdf.parent.name
    json_path = paper_pdf.parent/f"{recid}_metadata.json"
    txt = json_path.read_text(encoding="utf-8")
    metadata_json = json.loads(txt)
    warnings:list[str] = []
    result = simplify_metadata(metadata_json, warnings)
    return result, warnings
