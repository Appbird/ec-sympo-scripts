from dataclasses import dataclass
from enum import Enum
from logging import info
from pathlib import Path
from typing import Self, TypeVar
from returns.result import safe, ResultE, Success, Failure
from returns.primitives.exceptions import UnwrapFailedError
from returns.maybe import Maybe, Some, Nothing

import re

from pdf2text import pdf2json
from pdf_types import Footnote, Paper, Section
from pymupdf_layout_types import PdfDocument
from util import clean_multiline_literal

T = TypeVar("T")

class TokenType(Enum):
    PICTURE = 'picture'
    TEXT = 'text',
    LIST_ITEM = 'list-item',
    FOOTNOTE = 'footnote',
    TABLE = 'table',
    PAGE_FOOTER = 'page-footer',
    CAPTION = 'caption',
    TITLE = 'title',
    SECTION_HEADER = 'section-header',
    PAGE_HEADER = 'page-header'
    END_OF_LINE = 'end-of-line'
    BOX_SENTINEL = 'box-sentinel'

def str_to_token_types(s:str) -> TokenType:
    match s:
        case 'picture': return TokenType.PICTURE
        case 'text': return TokenType.TEXT
        case 'list-item': return TokenType.LIST_ITEM
        case 'footnote': return TokenType.FOOTNOTE
        case 'table': return TokenType.TABLE
        case 'page-footer': return TokenType.PAGE_FOOTER
        case 'caption': return TokenType.CAPTION
        case 'title': return TokenType.TITLE
        case 'section-header': return TokenType.SECTION_HEADER
        case 'page-header': return TokenType.PAGE_HEADER
        case 'end-of-line': return TokenType.END_OF_LINE
        case 'box-sentinel': return TokenType.BOX_SENTINEL
        case _:             raise ValueError(f"Unknown token type: {s}")

@dataclass
class Token:
    type:TokenType
    content:str
    def __str__(self):
        return self.content
    

def doc_to_tokens(doc:PdfDocument):
    tokens:list[Token] = []
    for page in doc.pages:
        for box in page.boxes:
            tokentype = str_to_token_types(box.boxclass)
            if box.textlines is None: continue
            for textline in box.textlines:
                for span in textline.spans:
                    tokens.append(Token(tokentype, span.text))
                tokens.append(Token(TokenType.END_OF_LINE, "\n"))
            tokens.append(Token(TokenType.BOX_SENTINEL, ""))
    return tokens

def dump_token(tokens:list[Token]) -> str:
    dumped = ""
    head_of_box = True
    head_of_line = True
    for token in tokens:
        if head_of_box:
            dumped += f"[box {token.type}]\n"
            head_of_box = False
        if head_of_line:
            dumped += "\t"
            head_of_line = False
        
        if token.type == TokenType.END_OF_LINE:
            dumped += "\n"
            head_of_line = True
        if token.type == TokenType.BOX_SENTINEL:
            dumped += "\n"
            head_of_box = True
            head_of_line = True
        else:
            dumped += f"{token.content} "
    return dumped
        
        
    

class TokenStream:
    filename:str
    tokens: list[Token]
    at:int = 0
    def __init__(self, filename:Path):
        doc = pdf2json(filename).unwrap()
        tokens = doc_to_tokens(doc)
        tokens = filter(lambda t: t.type not in {TokenType.PAGE_HEADER, TokenType.PAGE_FOOTER}, tokens)
        self.tokens = list(tokens)
    def __str__(self):
        return dump_token(self.tokens)
                        
    def surroundings(self, r:int) -> tuple[list[Token], int]:
        return (self.tokens[self.at - r : self.at + r], r - max(r - self.at, 0))
    
    def location(self) -> int: return self.at

    def pop(self:Self, what_expect:str = "") -> Maybe[Token]:
        result:Maybe[Token] = Nothing
        if self.at == len(self.tokens):
            info(f"Expect = {what_expect}, actual = end")
        else:
            info(f"Expect = {what_expect}, actual = {self.tokens[self.at]}")
            result = Some(self.tokens[self.at])
        self.at += 1
        return result
    def next(self:Self) -> Maybe[Token]:
        if self.at + 1 != len(self.tokens):
            return Some(self.tokens[self.at + 1])
        else:
            return Nothing
    def end_of_line(self) -> bool:
        next_token = self.next()
        if next_token == Nothing: return True
        return next_token.unwrap().type == TokenType.END_OF_LINE
    def end_of_box(self) -> bool:
        next_token = self.next()
        if next_token == Nothing: return True
        return next_token.unwrap().type == TokenType.BOX_SENTINEL

    def expect(self, pattern:TokenType, what_expect:str) -> ResultE[Token]:
        match self.pop(what_expect):
            case Some(tested):
                if pattern != tested.type: return Failure(exception_report(self, f"`{what_expect}として{pattern}`にマッチする行が来るはずなのに、トークン`{tested.type}`が来てしもうたね。"))
                else: return Success(tested)
            case Nothing:
                return Failure(exception_report(self, f"`{what_expect}として{pattern}`にマッチする行が来るはずなのに、もう行切れしてもうたね。"))
    def expect_box(self, patterns:set[TokenType], what_expect:str) -> ResultE[str]:
        next_token = self.next()
        if next_token is Nothing:
            return Failure(exception_report(self, f"`{what_expect}として{patterns}`にマッチする行が来るはずなのに、切れてしまったね。"))
        if next_token.unwrap().type in patterns: 
            return Failure(exception_report(self, f"`{what_expect}として{patterns}`にマッチする行が来るはずなのに、トークン`{next_token}`が来てしもうたね。"))

        content = ""
        # FIXME: 一回もループしないのはなぜ？
        while not self.end_of_box():
            popped = self.pop(what_expect).unwrap()
            content += popped.content
        return Success(content)
    def expect_line(self, patterns:set[TokenType], what_expect:str) -> ResultE[str]:
        next_token = self.next()
        if next_token is Nothing:
            return Failure(exception_report(self, f"`{what_expect}として{patterns}`にマッチする行が来るはずなのに、切れてしまったね。"))
        if next_token.unwrap().type in patterns: 
            return Failure(exception_report(self, f"`{what_expect}として{patterns}`にマッチする行が来るはずなのに、トークン`{next_token}`が来てしもうたね。"))
        
        content = ""
        while not self.end_of_line():
            popped = self.pop(what_expect).unwrap()
            content += popped.content
        return Success(content)
    def skip(self, what_expect:str) -> ResultE[None]:
        match self.pop(what_expect):
            case Some(popped):
                info(f"ignore line `{popped}` as {what_expect}")
                return Success(None)
            case Nothing:      return Failure(exception_report(self, f"`{what_expect}が来るはずなのに、もう行切れしてもうたね。"))
    
    def empty(self:Self) -> bool:
        return self.at >= len(self.tokens) - 1

@dataclass
class ExceptionReport(Exception):
    filename:str
    current_posititon:int
    surroundings:list[Token]
    exception:str
    def __str__(self):
        return clean_multiline_literal(f"""
        ❗️Exception: {self.exception}
        at {self.filename}:{self.current_posititon + 1}
        
        ========================
        {dump_token(self.surroundings)}
        ========================
        """)

def exception_report(lines:TokenStream, err:str):
    return ExceptionReport(
        lines.filename,
        lines.location(),
        lines.surroundings(20)[0],
        err
    )

def expect(m:Maybe[T], err:str) -> T:
    match m:
        case Some(x): return x
        case Nothing: raise Exception(err)

@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_figure(paper:Paper, lines:TokenStream) -> None:
    raise NotImplementedError()


@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_table(paper:Paper, lines:TokenStream) -> None:
    raise NotImplementedError()

@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_footnote(paper:Paper, lines:TokenStream) -> None:
    footnote = lines.expect(r">\s*(?P<sign>[_*\[\]a-zA-Z0-9()]+)\s+(?P<content>.+)", "節タイトル").unwrap()
    sign = footnote["sign"]
    content = footnote["content"]
    assert isinstance(sign, str) and isinstance(content, str)
    paper.footnotes.append(Footnote(sign, content))


@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_section(paper:Paper, lines:TokenStream) -> None:
    # 節タイトルの解釈
    section = Section("", "", [])
    header = lines.expect(r"(#{1,5})\s*(.+)", "節タイトル").unwrap().group(2)
    assert isinstance(header, str)
    header = header.replace("**", "")
    header_pattern = r"(?P<number>([0-9]{1,2}.)+)\s+(?P<title>.+)"
    header_match = re.match(header_pattern, header)
    if header_match is None: raise exception_report(lines, f"ヘッダの並びは{header_pattern}になるべきだけど、`{header}`だったね。")
    title = header_match["number"]
    section_name = header_match["title"]
    assert isinstance(title, str) and isinstance(section_name, str)
    section.number = title
    section.part_name = section_name
    
    # 本文
    is_interrupted = False
    while not lines.empty():
        next_line = lines.next().unwrap()
        if next_line.startswith("#"): return
        elif next_line.startswith(">"): parse_footnote(paper, lines)
        else:
            line = lines.pop().unwrap()
            if is_interrupted:
                section.paragraphs_below[-1] += line
            else:
                section.paragraphs_below.append(line)
            is_interrupted = not line.endswith("．")
    paper.sections.append(section)
    return 


@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_paper_title(paper:Paper, tokens:TokenStream) -> None:
    title = tokens.expect_box({TokenType.TITLE}, "タイトル").unwrap()
    tokens.expect_box({TokenType.TEXT}, "著者群").unwrap()
    abstract = tokens.expect_box({TokenType.TEXT}, "概要").unwrap()
    keywords = tokens.expect_box({TokenType.TEXT}, "キーワード").unwrap()

    print("title", title)
    print("abstract", abstract)
    print("keywords", keywords)
    return


    
    

@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_paper(paper:Paper, tokens:TokenStream) -> None:
    parse_paper_title(paper, tokens).unwrap()
    #while not tokens.empty():
    #    parse_section(paper, tokens).unwrap()
    return 
    
    
    

if __name__ == "__main__":
    paper = Paper("", "", [], [], [], [], [])
    testfile = Path("pdf/EC2025/data/recid_2003647/IPSJ-EC2025001.pdf")
    ts = TokenStream(testfile)
    parse_paper(paper, ts).unwrap()
    exit(0)