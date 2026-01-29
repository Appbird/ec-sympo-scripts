from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from parse.pymupdf_layout_types import PdfDocument, Span


class TokenType(Enum):
    PICTURE = "picture"
    TEXT = "text"
    LIST_ITEM = "list-item"
    FOOTNOTE = "footnote"
    TABLE = "table"
    PAGE_FOOTER = "page-footer"
    CAPTION = "caption"
    TITLE = "title"
    SECTION_HEADER = "section-header"
    FORMULA = "formula"
    PAGE_HEADER = "page-header"


def str_to_token_type(value: str) -> TokenType:
    match value:
        case "picture":
            return TokenType.PICTURE
        case "text":
            return TokenType.TEXT
        case "list-item":
            return TokenType.LIST_ITEM
        case "footnote":
            return TokenType.FOOTNOTE
        case "table":
            return TokenType.TABLE
        case "page-footer":
            return TokenType.PAGE_FOOTER
        case "caption":
            return TokenType.CAPTION
        case "title":
            return TokenType.TITLE
        case "section-header":
            return TokenType.SECTION_HEADER
        case "page-header":
            return TokenType.PAGE_HEADER
        case "formula":
            return TokenType.FORMULA
        case _:
            raise ValueError(f"Unknown token type: {value}")


@dataclass
class Token:
    type: TokenType
    content: str
    lines: list[str]
    line_x0: list[int]
    line_starts_with_bold: list[bool]
    cells: list[list[str|None]]

    def __str__(self) -> str:  # pragma: no cover - debugging aid
        return f"{self.type}, {' / '.join(self.lines)}"


def is_span_bold(span: Span) -> bool:
    return (((span.flags >> 4) & 1) == 1) or span.font.endswith("Medium")


def doc_to_tokens(doc: PdfDocument) -> list[Token]:
    tokens: list[Token] = []
    for page in doc.pages:
        for box in page.boxes:
            tokentype = str_to_token_type(box.boxclass)
            if tokentype == TokenType.TABLE:
                assert box.table is not None, "Table is not found in box data."
                lines = box.table.markdown.splitlines()
                content = box.table.markdown
                token = Token(
                    tokentype,
                    content,
                    lines,
                    [0 for _ in lines],
                    [False for _ in lines],
                    box.table.extract,
                )
                tokens.append(token)
                continue
            if box.textlines is None:
                continue
            content = ""
            lines: list[str] = []
            lines_x0: list[int] = []
            list_line_starts_with_bold: list[bool] = []
            for textline in box.textlines:
                line = ""
                is_bold = len(textline.spans) > 0 and is_span_bold(textline.spans[0])
                for span in textline.spans:
                    line += span.text
                content += line
                lines.append(line)
                lines_x0.append(int(textline.bbox[0]))
                list_line_starts_with_bold.append(is_bold)
            tokens.append(
                Token(tokentype, content, lines, lines_x0, list_line_starts_with_bold, [])
            )
    return tokens


def dump_tokens(tokens: Iterable[Token]) -> str:
    dumped = ""
    head_of_box = True
    for token in tokens:
        if head_of_box:
            dumped += f"[box {token.type}]\n"
            for line in token.lines:
                dumped += f"\t{line}\n"
    return dumped
