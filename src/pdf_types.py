
from dataclasses import dataclass
from typing import Optional
from metadata_types import SimplifiedMetadata


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
    content:str

@dataclass
class Paper:
    metadata:SimplifiedMetadata
    sections:list[Section]
    tables:list[Figure]
    figures:list[Table]
    footnotes:list[Footnote]
    