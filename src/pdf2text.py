import json
from pathlib import Path
from returns.result import safe
import pymupdf.layout as _
import pymupdf4llm
import argparse

from parse.pymupdf_layout_types import PdfDocument, list_span_texts

@safe
def pdf2txt(
    path_pdf:Path,
    cached:bool = True
) -> str:
    """`path_pdf`に与えられたPDFをpymupdf4llmによってテキスト化する。"""
    path_txt = path_pdf.with_name(f"{path_pdf.name}.txt")
    if path_txt.exists() and cached:
        return path_txt.read_text(encoding="utf-8")
    txt = pymupdf4llm.to_markdown(path_pdf)
    if not isinstance(txt, str):
        raise Exception("pymupdf4llm exported list[dict].")
    if cached:
        path_txt.write_text(txt, encoding="utf-8")
    return txt

@safe
def pdf2json(
    path_pdf:Path,
    cached:bool = True
) -> PdfDocument:
    """`path_pdf`に与えられたPDFをpymupdf4llmによってJSON化する。"""
    path_json = path_pdf.with_name(f"{path_pdf.name}.json")
    if path_json.exists() and cached:
        return PdfDocument.model_validate_json(path_json.read_text(encoding="utf-8"))
    txt = pymupdf4llm.to_json(path_pdf, )
    ob = json.loads(txt)
    txt = json.dumps(ob, ensure_ascii=False)
    path_json.write_text(txt, encoding="utf-8")
    return PdfDocument.model_validate_json(txt)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='pdf2text',
        description='convert pdf to text, json.',
    )
    parser.add_argument("filename", type=Path)
    args= parser.parse_args()
    pdf_document = pdf2json(args.filename).unwrap()
    list_span_texts(pdf_document)
    