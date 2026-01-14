from pathlib import Path
from returns.result import safe
import pymupdf4llm.layout as _
import pymupdf4llm


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
