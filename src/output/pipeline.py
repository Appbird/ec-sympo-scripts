"""PDF/メタデータを処理して出力フォルダに整形保存する。"""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from returns.primitives.exceptions import UnwrapFailedError
from returns.result import safe

from metadata.metadata_simplifier import simplify_metadata_of_paper
from metadata.metadata_types import SimplifiedMetadata
from parsing.paper_parser import parse_paper
from parsing.stream import TokenStream, exception_report_prior
from parsing.pdf2text import pdf2json
from parsing.pdf_types import Paper


@safe(exceptions=(UnwrapFailedError,))
def parse_paper_in_ec_sympo(path: Path):
    (simplified_result, warnings) = simplify_metadata_of_paper(path)
    metadata = simplified_result.unwrap()

    paper = Paper()
    for warning in warnings:
        paper.warnings.append(exception_report_prior(metadata["title"], warning))
    pdf_document = pdf2json(path).unwrap()
    tokenstream = TokenStream(path, pdf_document)

    parse_paper(paper, tokenstream).unwrap()
    return (metadata, paper)


def metadata_decode_json(out: Path, metadata: SimplifiedMetadata):
    return out.write_text(json.dumps(metadata, ensure_ascii=False, indent=4), encoding="utf-8")


def tidy_up_paper_folder(path_pdf: Path, out_path: Path):
    target_folder = out_path / path_pdf.name
    os.makedirs(target_folder, exist_ok=True)
    metadata_path = target_folder / "metadata.json"
    content_path = target_folder / "content.json"
    warning_path = target_folder / "fallbacks.json"
    pdf_path = target_folder / "paper.pdf"

    (metadata, paper) = parse_paper_in_ec_sympo(path_pdf).unwrap()
    metadata_decode_json(metadata_path, metadata)
    paper.warn()
    paper.decode_json(content_path, warning_path)
    shutil.copy(path_pdf, pdf_path)

    return metadata, paper
