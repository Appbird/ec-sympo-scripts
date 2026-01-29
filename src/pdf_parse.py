"""Backward-compatible imports for the new parse package.

When executed as a script, parse a PDF and emit ./out.json.
"""

from __future__ import annotations

from pathlib import Path

from parse import (  # noqa: F401
    ExceptionReport,
    Token,
    TokenStream,
    TokenType,
    doc_to_tokens,
    dump_tokens,
    exception_report,
    parse_paper,
    str_to_token_type,
)
from pdf_types import Paper, StructuredPaper
from returns.result import Failure

__all__ = [
    "ExceptionReport",
    "Token",
    "TokenStream",
    "TokenType",
    "doc_to_tokens",
    "dump_tokens",
    "exception_report",
    "parse_paper",
    "str_to_token_type",
]


def main() -> None:
    import argparse
    import logging

    parser = argparse.ArgumentParser(description="Parse a PDF into ./out.json")
    parser.add_argument("pdf_path", type=Path, help="Path to the input PDF file")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    paper = Paper()
    token_stream = TokenStream(args.pdf_path)
    result = parse_paper(paper, token_stream).unwrap()
    if isinstance(result, Failure):
        print(result.failure())
        raise SystemExit(1)

    output_path = Path("./out.json")
    paper.decode_json(output_path)
    print(f"wrote: {output_path}")


if __name__ == "__main__":
    main()
