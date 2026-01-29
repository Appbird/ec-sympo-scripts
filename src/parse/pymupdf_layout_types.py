from typing import Any, Optional
from pydantic import BaseModel

type Bbox = list[float]
type TocEntry = list[int | str]

class Span(BaseModel):
    size: float
    flags: int
    bidi: int
    char_flags: int
    font: str
    color: int
    alpha: int
    ascender: float
    descender: float
    text: str
    origin: list[float]
    bbox: list[float]
    #line: Optional[int]
    #block: Optional[int]
    #dir: Optional[list[float]]

class TextLine(BaseModel):
    bbox: Bbox
    spans: list[Span]

class Table(BaseModel):
    extract:list[list[str|None]]
    markdown:str

class Box(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float
    boxclass: str
    image: Optional[Any]
    table: Optional[Table]
    textlines: Optional[list[TextLine]]

class FullTextLine(BaseModel):
    spans: list[Span]
    wmode: int
    dir: list[float]
    bbox: Bbox

class FullTextBlock(BaseModel):
    type: int
    number: int
    flags: int
    bbox: Bbox
    lines: list[FullTextLine]

class Page(BaseModel):
    page_number: int
    width: float
    height: float
    boxes: list[Box]
    full_ocred: bool
    text_ocred: bool
    fulltext: list[FullTextBlock]
    words: list[Any]
    links: list[Any]

class Metadata(BaseModel):
    format: str
    title: str
    author: str
    subject: str
    keywords: str
    creator: str
    producer: str
    creationDate: str
    modDate: str
    trapped: str
    encryption: Optional[Any]

class PdfDocument(BaseModel):
    filename: str
    page_count: int
    toc: list[TocEntry]
    pages: list[Page]
    metadata: Metadata
    from_bytes: bool
    image_dpi: int
    image_format: str
    image_path: str
    use_ocr: bool
    form_fields: dict[str, Any]
    force_text: bool
    embed_images: bool
    write_images: bool


def list_span_texts(doc: PdfDocument) -> list[str]:
    texts: list[str] = []
    classes= set()
    for page in doc.pages:
        print(f"Page {page.page_number};")
        for box in page.boxes:
            print(f"\tbox {box.boxclass}")
            classes.add(box.boxclass)
            if box.textlines is None: continue
            for textline in box.textlines:
                print("\t\t", end="")
                for span in textline.spans:
                    print(f"{span.text} / ", end="")
                print("")
    print(classes)
    return texts
