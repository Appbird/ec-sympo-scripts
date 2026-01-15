
from dataclasses import dataclass
from typing import Optional
from metadata_types import SimplifiedMetadata
from util import clean_multiline_literal


@dataclass
class Figure:
    stringize_content:str
    size:str
    number:int
    title:str
    etitle:Optional[str]

@dataclass
class Table:
    content:str
    width:int
    height:int
    number:int
    title:str
    etitle:Optional[str]

@dataclass
class Paragraph:
    content:str

@dataclass
class Section:
    number:str
    part_name:str
    paragraphs_below:list[str]


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
    tables:list[Figure]
    figures:list[Table]
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
        
    