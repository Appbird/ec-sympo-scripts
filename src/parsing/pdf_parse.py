"""単体実行用のPDFパースCLI。"""

from __future__ import annotations

from pathlib import Path
from metadata.metadata_types import default_simplified_metadata
from .paper_parser import parse_paper
from .stream import TokenStream
from .pdf2text import pdf2json
from .pdf_types import Paper
import argparse
import logging


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Parse a PDF into ./out.json")
    parser.add_argument("pdf_path", type=Path, help="Path to the input PDF file")
    parser.add_argument("out_path", type=Path, help="Path to the output json file", default=Path("out.json"))
    args = parser.parse_args()
    
    path_pdf = args.path_pdf
    output_path = args.out_path
    assert isinstance(path_pdf, Path)
    assert isinstance(output_path, Path)
    
    paper = Paper()
    doc = pdf2json(path_pdf).unwrap()
    token_stream = TokenStream(args.pdf_path, doc)
    
    parse_paper(paper, token_stream).unwrap()
    paper.warn()
    
    paper.decode_json(output_path)
    print(f"wrote: {output_path}")


if __name__ == "__main__":
    main()
