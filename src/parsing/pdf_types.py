"""論文構造データの型定義（Paper/Segment等）。"""

from dataclasses import dataclass
import dataclasses
import json
import logging
from pathlib import Path
from typing import Literal, Optional
from .stream import ExceptionReport, exception_report
from util import clean_multiline_literal

SegmentTypeName = Literal["SectionTitle"] | Literal["Paragraph"] | Literal["ListItems"] | Literal["Figure"] | Literal["Table"] | Literal["FootNote"]

@dataclass
class Segment:
    type:SegmentTypeName
    sign:Optional[str]
    title:Optional[str]
    content:str

@dataclass
class Reference:
    sign:str
    content:str

class Paper:
    title:str
    abstract:str
    keywords:list[str]
    segments:list[Segment]
    references:list[Reference]
    warnings:list[ExceptionReport]

    _queued_segment:list[Segment]
    _last_paragraph:int = -1
    _last_list_items:int = -1
    def __init__(self) -> None:
        self.title = ""
        self.abstract = ""
        self.keywords = []
        self.segments = []
        self.references = []
        self._queued_segment = []
        self.warnings = []
    
    def end_of_the_paper(self):
        self._flush_queue()
    def warn(self):
        if len(self.warnings) == 0: return
        logging.warning(f"There are {len(self.warnings)} warnings in this paper {self.title}.")
        for warning in self.warnings:
            logging.warning(str(warning))
        
    def decode_json(self, out:Path, warning_path:Path):
        obj = {
            "title": self.title,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "segments": [dataclasses.asdict(segment) for segment in self.segments],
            "references": [dataclasses.asdict(reference) for reference in self.references]
        }
        out.write_text(json.dumps(obj, ensure_ascii=False, indent=4))
    
        warnings = {
            "warnings": [warning.decode_dict() for warning in self.warnings]
        }
        warning_path.write_text(json.dumps(warnings, ensure_ascii=False, indent=4))
    def add_section_title(self, title:str, sign:str):
        self.segments.append(Segment("SectionTitle", sign, None, title,))

    def add_listitems(self):
        self._flush_queue()
        self.segments.append(Segment("ListItems", None, None, ""))
        self._last_list_items = len(self.segments) - 1
    def extend_last_listitems(self, appended:str):
        assert self._last_list_items >= 0, f"箇条書き要素を一つ以上追加してください: {appended}"
        self.segments[self._last_list_items].content += appended + "\n"
    def is_last_text_listitem(self):
        return self._last_list_items > self._last_paragraph
    def exists_listitems(self):
        return self._last_list_items != -1


    def add_paragraph(self, appended:str):
        self._flush_queue()
        self.segments.append(Segment("Paragraph", None, None, appended))
        self._last_paragraph = len(self.segments) - 1
    def exists_paragraph(self):
        return self._last_paragraph >= 0
    def extend_last_paragraph(self, appended:str):
        assert self._last_paragraph >= 0, f"パラグラフを一つ以上追加してください。: {appended}"
        self.segments[self._last_paragraph].content += appended
    def exists_interrupted_paragraph(self):
        if self._last_paragraph == -1: return False
        return not self.segments[self._last_paragraph].content.strip().endswith(("．", "。", "."))
    
    def add_figure(self, content:str, sign:str, caption:str):
        self._queued_segment.append(Segment("Figure", sign, caption, content))

    def add_footnote(self, content:str, sign:str):
        self._queued_segment.append(Segment("FootNote", sign, None, content))

    def add_table(self, content:str, sign:str, caption:str):
        self._queued_segment.append(Segment("Table", content, sign, caption))

    def _flush_queue(self):
        self.segments.extend(self._queued_segment)
        self._queued_segment = []
    

@dataclass
class Figure:
    stringize_content:str
    number:int
    title:str
    etitle:Optional[str]

@dataclass
class Table:
    cells:list[list[str|None]]
    content:str
    number:int
    title:str
    etitle:Optional[str]

@dataclass
class Paragraph:
    content:str
    list_items:list[str]
    is_enumrated:bool

@dataclass
class Section:
    number:str
    part_name:str
    paragraphs_below:list[Paragraph]


@dataclass
class Footnote:
    sign:str
    content:str


@dataclass
class StructuredPaper:
    # metadata:SimplifiedMetadata
    title:str
    abstract:str
    keywords:list[str]
    sections:list[Section]
    figures:list[Figure]
    tables:list[Table]
    footnotes:list[Footnote]
    references:list[Reference]
    warnings:list[ExceptionReport]

    def decode_json(self, out:Path):
        out.write_text(json.dumps(dataclasses.asdict(self), ensure_ascii=False, indent=4))

    def __str__(self):
        return clean_multiline_literal(f"""
        # {self.title}
        概要：{self.abstract}
        キーワード：{self.keywords}
        
        ## 本文
        {self.sections}

        ## 表データ
        {self.tables}

        ## 図
        {self.tables}

        ## 脚注
        {self.footnotes}
        """)
        
    
