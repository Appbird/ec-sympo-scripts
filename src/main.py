from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from returns.result import Failure

from metadata_simplifier import simplify_metadata

PATTERN = re.compile(r"recid_(\d+)/recid_(\d+)_metadata\.json$")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _iter_metadata_files(root: Path) -> list[tuple[Path, str, str]]:
    matches: list[tuple[Path, str, str]] = []
    for path in root.rglob("recid_*_metadata.json"):
        rel_path = path.as_posix()
        match = PATTERN.search(rel_path)
        if match:
            matches.append((path, match.group(1), match.group(2)))
    return matches


def main() -> None:
    """Run simplify_metadata for all matching metadata JSON files."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate metadata JSON files.")
    parser.add_argument("root_path", type=Path, help="Root path to scan.")
    args = parser.parse_args()

    matches = _iter_metadata_files(args.root_path)
    if not matches:
        print("no matching metadata json files found")
        raise SystemExit(1)

    failures: list[str] = []
    for path, dir_id, file_id in matches:
        if dir_id != file_id:
            failures.append(f"id mismatch: {path}")
            continue
        payload = _load_json(path)
        result = simplify_metadata(payload)
        if isinstance(result, Failure):
            failures.append(f"{path}: {result.failure()}")

    if failures:
        print("failed:")
        for message in failures:
            print(message)
        raise SystemExit(1)

    print(f"ok: {len(matches)} files")


if __name__ == "__main__":
    main()
