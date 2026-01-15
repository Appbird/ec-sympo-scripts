from typing import Any, Union
from returns.result import safe

import re

from pdf_types import Paper

@safe
def clean(paper_txt:str) -> list[str]:
    lines = re.split(r"\n+", paper_txt)

    span_filter = ParagraphSpanFilter()
    lines = map(assure_str, lines)
    lines = map(lambda s: s.strip(), lines)
    lines = map(lambda s: s.replace("`", ""), lines)
    lines = filter(span_filter.is_paragraph_span, lines)
    lines = filter(is_paragraph_line, lines)
    lines = list(lines)
    paragraphs = merge_interrupted_paragraphs(lines)
    paragraphs = list(map(lambda s: re.sub(r"\s", "", s), paragraphs))
    return list(paragraphs)



def is_completed_paragraph(s:str):
    """その段落が途中で途切れて改行されていないかを判定する。"""
    return s.endswith("．") or s.endswith(".") or s.endswith("。")

def is_section_heading(s:str) -> bool:
    return s.startswith("## ")

def is_picture_omitted_line(s:str) -> bool:
    return s.startswith("**==> picture") and s.endswith("intentionally omitted <==**")

def is_footnote_line(s:str) -> bool:
    return re.match(r"(-\s)?\*?\[[0-9]+\]", s) is not None

def is_table_row(s:str) -> bool:
    return s.startswith("|") and s.endswith("|")

def is_blockquote(s:str) -> bool:
    return s.startswith(">")

def is_figure_or_table_caption(s:str) -> bool:
    return re.match(r"-?\s?(図|表)\s?\*\*[0-9]+\*\*", s) is not None

def is_copyright_line(s:str) -> bool:
    return s.startswith("ⓒ")

def is_page_number_line(s:str) -> bool:
    return re.fullmatch(r"[0-9]+", s) is not None

def assure_str(s:Union[str, Any]) -> str:
    if isinstance(s, str):
        return s
    raise Exception("s is not string.")

def structurized_pymupdf4llm_txt(paper_txt:str) -> Paper:
    paper = Paper()
    lines = re.split(r"\n+", paper_txt)
    for line in lines:



def is_paragraph_line(s:str) -> bool:
    if is_section_heading(s):
        return False
    if is_picture_omitted_line(s):
        return False
    if is_footnote_line(s):
        return False 
    if is_table_row(s):
        return False
    if is_blockquote(s):
        return False
    if is_figure_or_table_caption(s):
        return False
    if is_copyright_line(s):
        return False
    if is_page_number_line(s):
        return False
    return True


def is_first_section_start(s:str) -> bool:
    return s.startswith("##") and "1." in s

def is_reference_section_heading(s:str) -> bool:
    return s == "## 参考文献"

def is_picture_text_start(s:str) -> bool:
    return s.startswith("**----- Start of picture text -----**<br>")

def is_picture_text_end(s:str) -> bool:
    return s.endswith("**----- End of picture text -----**<br>")


class ParagraphSpanFilter:
    def __init__(self) -> None:
        self.in_header = True
        self.in_reference_section = False
        self.in_figure_section = False

    def is_paragraph_span(self, s:str) -> bool:
        # 初めの行の削除
        if is_first_section_start(s):
            self.in_header = False
        if self.in_header:
            return False

        # 参考文献セクションの削除
        if s.startswith("##"):
            self.in_reference_section = False
        if is_reference_section_heading(s):
            self.in_reference_section = True
        if self.in_reference_section:
            return False

        # 写真テキストセクションの削除
        if is_picture_text_start(s):
            self.in_figure_section = True
        if is_picture_text_end(s):
            self.in_figure_section = False
            return False
        if self.in_figure_section:
            return False
        return True


def merge_interrupted_paragraphs(lines:list[str]) -> list[str]:
    # 途切れている部分を結合していく
    paragraphs:list[str] = []
    interrupted = False
    in_bullets_points = False
    for line in lines:
        if not line.startswith("- "):
            in_bullets_points = False 
        if interrupted or in_bullets_points:
            if len(paragraphs) == 0:
                raise Exception("paragraph is empty.")
            paragraphs[-1] = paragraphs[-1] + line
            if is_completed_paragraph(line):
                interrupted = False
            continue
        if not is_completed_paragraph(line):
            interrupted = True
        if line.startswith("- "):
            in_bullets_points = True
        paragraphs.append(line)
    return paragraphs

