"""overview.csv 向けの集計とCSV出力を担当する。"""

from __future__ import annotations

import csv
from pathlib import Path

from parsing.pdf_types import Paper


def summarize_warnings(paper: Paper) -> dict[str, str | int]:
    groups: dict[str, list[str]] = {}
    for warning in paper.warnings:
        message = warning.exception
        key = message[:10]
        groups.setdefault(key, []).append(message)
    group_summaries: list[str] = []
    group_examples: list[str] = []
    for key in sorted(groups.keys()):
        messages = groups[key]
        group_summaries.append(f"{key}({len(messages)})")
        example = next((m for m in messages if m), "")
        group_examples.append(f"{key}: {example}")
    return {
        "warning_count": len(paper.warnings),
        "warning_group_count": len(groups),
        "warning_groups": " ; ".join(group_summaries),
        "warning_examples": " ; ".join(group_examples),
    }


def summarize_segments(paper: Paper) -> dict[str, int]:
    section_count = 0
    paragraph_count = 0
    for segment in paper.segments:
        if segment.type == "SectionTitle":
            section_count += 1
        elif segment.type == "Paragraph":
            paragraph_count += 1
    return {
        "section_count": section_count,
        "paragraph_count": paragraph_count,
    }

def summarize_references(paper: Paper) -> dict[str, int]:
    return {"reference_count": len(paper.references)}


def write_overview_csv(out_path: Path, rows: list[dict[str, str | int]]) -> None:
    out_path.mkdir(parents=True, exist_ok=True)
    overview_path = out_path / "overview.csv"
    fieldnames = [
        "paper_title",
        "pdf_path",
        "section_count",
        "paragraph_count",
        "reference_count",
        "warning_count",
        "warning_group_count",
        "warning_groups",
        "warning_examples",
    ]
    with overview_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
