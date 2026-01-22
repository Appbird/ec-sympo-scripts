
from dataclasses import dataclass
from typing import Optional
from metadata_types import SimplifiedMetadata
from util import clean_multiline_literal


@dataclass
class Figure:
    stringize_content:str
    number:int
    title:str
    etitle:Optional[str]

@dataclass
class Table:
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
class Paper:
    # metadata:SimplifiedMetadata
    title:str
    abstract:str
    keywords:list[str]
    sections:list[Section]
    figures:list[Figure]
    tables:list[Table]
    footnotes:list[Footnote]

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
        
    