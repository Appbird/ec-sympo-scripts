"""メタデータJSONの抽出・検証用ユーティリティ。"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from returns.maybe import Maybe, Nothing, Some
from returns.result import Failure, Result, Success

PathToken = str | int
Path = list[PathToken]
PathSpec = str


def parse_path(path: PathSpec) -> Path:
    """Parse a path string like 'date[0].value' into tokens."""
    tokens: list[PathToken] = []
    buffer = ""
    i = 0
    while i < len(path):
        char = path[i]
        if char == ".":
            if buffer:
                tokens.append(buffer)
                buffer = ""
            i += 1
            continue
        if char == "[":
            if buffer:
                tokens.append(buffer)
                buffer = ""
            i += 1
            index_buffer = ""
            while i < len(path) and path[i] != "]":
                index_buffer += path[i]
                i += 1
            if not index_buffer.isdigit():
                raise ValueError(f"invalid path index in {path!r}")
            tokens.append(int(index_buffer))
            if i >= len(path) or path[i] != "]":
                raise ValueError(f"unterminated index in {path!r}")
            i += 1
            continue
        buffer += char
        i += 1
    if buffer:
        tokens.append(buffer)
    return tokens


def get_path(data: Any, path: Sequence[PathToken]) -> Maybe[Any]:
    """Traverse nested dict/list data by a path."""
    current = data
    for key in path:
        if isinstance(key, int):
            if not isinstance(current, list) or key >= len(current):
                return Nothing
            current = current[key]
        else:
            if not isinstance(current, dict) or key not in current:
                return Nothing
            current = current[key]
    return Some(current)


def first_present(data: Any, paths: Iterable[PathSpec]) -> Maybe[Any]:
    """Return the first successful path lookup from a list of paths."""
    for path in paths:
        value = get_path(data, parse_path(path))
        if isinstance(value, Some):
            return value
    return Nothing


def required(data: Any, candidate_paths: Iterable[PathSpec], field_name: str) -> Result[Any, str]:
    """Return the first matching value or a Failure for a missing required field."""
    value = first_present(data, candidate_paths)
    match value:
        case Some(inner):
            return Success(inner)
        case _:
            return Failure(f"missing {field_name}")


def first_failure(results: Iterable[Result[Any, str]]) -> Result[None, str]:
    """Return the first Failure, or Success(None) if all succeed."""
    for result in results:
        if isinstance(result, Failure):
            return result
    return Success(None)
