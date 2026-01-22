from dataclasses import dataclass
from enum import Enum
from logging import info
import logging
from pathlib import Path
from typing import Any, Self, TypeVar
from returns.result import safe, ResultE, Success, Failure
from returns.primitives.exceptions import UnwrapFailedError
from returns.maybe import Maybe, Some, Nothing

import re

from pdf2text import pdf2json
from pdf_types import Figure, Footnote, Paper, Paragraph, Section, Table
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
        case _:             raise ValueError(f"Unknown token type: {s}")

@dataclass
class Token:
    type:TokenType
    content:str
    lines:list[str]
    spans:list[str]
    def __str__(self):
        return f"{self.type}, {self.content}"
    

def doc_to_tokens(doc:PdfDocument):
    tokens:list[Token] = []
    for page in doc.pages:
        for box in page.boxes:
            tokentype = str_to_token_types(box.boxclass)
            if box.textlines is None: continue
            content = ""
            lines:list[str] = []
            spans:list[str] = []
            for textline in box.textlines:
                line = ""
                for span in textline.spans:
                    line += span.text
                    spans.append(span.text)
                content += line
                spans.append("\n")
                lines.append(line)
            tokens.append(Token(tokentype, content, lines, spans))
    return tokens

def dump_token(tokens:list[Token]) -> str:
    dumped = ""
    head_of_box = True
    for token in tokens:
        if head_of_box:
            dumped += f"[box {token.type}]\n"
            for line in token.spans:
                dumped += f"\t{line}\n"
    return dumped
        
        
    

class TokenStream:
    """
    PDFの行単位で書かれている文字内容をストリームする。
    スパン単位ではなく、行単位とするのは、分割がTeX, Wordsのどちらでも一意な方法で分割されるとは限らないため。
    """
    filename:Path
    tokens: list[Token]
    at:int = 0

    def __init__(self, filename:Path):
        doc = pdf2json(filename).unwrap()
        tokens = doc_to_tokens(doc)
        self.filename = filename
        self.tokens = list(tokens)
    def __str__(self):
        return dump_token(self.tokens)
                        
    def surroundings(self, r:int) -> tuple[list[Token], int]:
        return (self.tokens[self.at - r : self.at + r], r - max(r - self.at, 0))
    
    def location(self) -> int: return self.at

    def pop(self:Self, what_expect:str) -> Maybe[Token]:
        result:Maybe[Token] = Nothing
        if self.at == len(self.tokens):
            info(f"Expect = {what_expect}, actual = end")
        else:
            info(f"Expect = {what_expect}, actual = {self.tokens[self.at]}")
            result = Some(self.tokens[self.at])
        self.at += 1
        return result
    
    def next(self:Self) -> Maybe[Token]:
        if self.at < len(self.tokens):
            return Some(self.tokens[self.at])
        else:
            return Nothing
    def is_next(self:Self, tokentypes:TokenType) -> bool:
        if self.at + 1 != len(self.tokens):
            return self.tokens[self.at + 1].type == tokentypes
        else:
            return False
    
    def expect(self, what_expect:str, tokentypes:set[TokenType] = set()) -> ResultE[Token]:
        popped = self.pop(what_expect)
        if popped is Nothing:
            return Failure(exception_report(self, f"`{what_expect}として{tokentypes}`にマッチする行が来るはずなのに、切れてしまったね。"))
        popped = popped.unwrap()
        if len(tokentypes) != 0 and popped.type not in tokentypes:
            return Failure(exception_report(self, f"`{what_expect}として{tokentypes}`にマッチする行が来るはずなのに、トークン`{popped}`が来てしもうたね。"))
        return Success(popped)

    def expect_pattern(self, what_expect:str, patterns:str, tokentypes:set[TokenType] = set()) -> ResultE[re.Match]:
        popped = self.pop(what_expect)
        if popped is Nothing:
            return Failure(exception_report(self, f"`{what_expect}として{tokentypes}`にマッチする行が来るはずなのに、切れてしまったね。"))
        popped = popped.unwrap()
        if len(tokentypes) != 0 and popped.type not in tokentypes:
            return Failure(exception_report(self, f"`{what_expect}として{tokentypes}`にマッチする行が来るはずなのに、トークン`{popped}`が来てしもうたね。"))
        content = popped.content
        matching = re.match(patterns, content)
        if matching == None:  return Failure(exception_report(self, f"`{what_expect}として{patterns}`にマッチする行が来るはずなのに、実際には`{content}`が来たね"))
        return Success(matching)
    
    def skip(self, tokentypes:set[TokenType], what_expect:str) -> ResultE[None]:
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
        str(lines.filename),
        lines.location(),
        lines.surroundings(2)[0],
        err
    )

@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_list_item(paper:Paper, tokens:TokenStream) -> None:
    # FIXME: 一つのアイテムに二つ以上入っている場合があるので注意する
    assert len(paper.sections) > 0, "セクションがまだ一つも追加されていません。セクションを追加してください。"
    paragraphs = paper.sections[-1].paragraphs_below
    # 一度もまだ段落が構成されていないか、前の段落が段落ではなかった場合には新しく箇条書きの段落を作る
    if len(paragraphs) == 0 or not paragraphs[-1].is_enumrated:
        paragraphs.append(Paragraph("", [], True))
    last_paragraph = paragraphs[-1]
    while not tokens.empty() and tokens.next().unwrap().type == TokenType.LIST_ITEM:
        list_item = tokens.expect("リスト", tokentypes={TokenType.LIST_ITEM}).unwrap()
        last_paragraph.content += list_item.content
        last_paragraph.list_items.append(list_item.content)

@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_figure(paper:Paper, tokens:TokenStream) -> None:
    figure = Figure("", -1, "unknown", None)
    while not tokens.empty() and tokens.next().unwrap().type == TokenType.PICTURE:
        figure.stringize_content += tokens.pop("図の内容").unwrap().content
    
    caption_token = tokens.next().unwrap()
    # TODO: 図の内容の方にキャプションが混じってしまっている場合があるので、それを拾う。
    correct_type= caption_token.type in {TokenType.CAPTION, TokenType.LIST_ITEM, TokenType.TEXT}
    is_caption_title = caption_token.content.startswith("図")
    if correct_type and is_caption_title:
        tokens.pop("キャプション")
        figure.number = int(caption_token.spans[1])
        figure.title = "".join(caption_token.spans[2:])
    paper.figures.append(figure)
        

@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_table(paper:Paper, tokens:TokenStream) -> None:
    # TODO: 実装
    content = tokens.pop("表").unwrap().content
    paper.tables.append(Table(content, 0, "", ""))
    raise NotImplementedError()
    

@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_footnote(paper:Paper, tokens:TokenStream) -> None:
    footnote = tokens.pop("脚注").unwrap().content
    assert isinstance(footnote, str)
    matching = re.match(r">\s*(?P<sign>[_*\[\]a-zA-Z0-9()]+)\s+(?P<content>.+)", footnote)
    if matching != None:
        sign = matching["sign"]
        content = matching["content"]
        assert isinstance(sign, str) and isinstance(content, str)
        paper.footnotes.append(Footnote(sign, content))
    else:
        paper.footnotes.append(Footnote("", footnote))
    

@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_section_header(paper:Paper, tokens:TokenStream) -> None:
    header = tokens.pop("節タイトル").unwrap().content
    assert isinstance(header, str)
    header = header.replace("**", "")

    header_pattern = r"(?P<number>([0-9]{1,2}.)+)\s*(?P<title>.+)"
    header_match = re.match(header_pattern, header)
    if header_match is None: raise exception_report(tokens, f"ヘッダの並びは{header_pattern}になるべきだけど、`{header}`だったね。")
    
    title = header_match["number"]
    section_name = header_match["title"]
    assert isinstance(title, str) and isinstance(section_name, str)
    
    section = Section("", "", [])
    section.number = title
    section.part_name = section_name
    paper.sections.append(section)

@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_main_text(paper:Paper, tokens:TokenStream) -> None:
    assert len(paper.sections) > 0, "セクションがまだ一つも追加されていません。セクションを追加してください。"
    last_section = paper.sections[-1]
    popped = tokens.pop("本文").unwrap()
    paragraph = Paragraph(popped.content, [], False)
    last_section.paragraphs_below.append(paragraph)


@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_abstract(paper:Paper, tokens:TokenStream):
    abstract= tokens.expect_pattern("概要", patterns=r"概要\s*(:|：)\s*(.+)").unwrap()[2]
    assert isinstance(abstract, str)
    paper.abstract = abstract[0]

@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_keywords(paper:Paper, tokens:TokenStream):
    keywords= tokens.expect_pattern("キーワード", patterns=r"キーワード\s*(:|：)\s*(.+)").unwrap()[2]
    assert isinstance(keywords, str)
    keywords = re.split(r"，", keywords[0])
    for keyword in keywords: assert isinstance(keyword, str)
    paper.keywords = keywords


@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_paper_head(paper:Paper, tokens:TokenStream) -> None:
    title = tokens.expect("タイトル", tokentypes={TokenType.TITLE}).unwrap()
    paper.title = title.content
    tokens.expect("著者群").unwrap()
    parse_abstract(paper, tokens).unwrap()
    parse_keywords(paper, tokens).unwrap()
    
    

@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_paper(paper:Paper, tokens:TokenStream) -> None:
    tokens.expect("ページヘッダ", tokentypes={TokenType.PAGE_HEADER}).unwrap()
    parse_paper_head(paper, tokens).unwrap()
    while not tokens.empty():
        token = tokens.next().unwrap()
        match token.type:
            case TokenType.PAGE_HEADER:
                tokens.expect("ページヘッダ", {TokenType.PAGE_HEADER}).unwrap()
                continue
            case TokenType.PAGE_FOOTER:
                tokens.expect("ページフッタ", {TokenType.PAGE_FOOTER}).unwrap()
                continue
            case TokenType.SECTION_HEADER:
                parse_section_header(paper, tokens).unwrap()
                continue
            case TokenType.TEXT:
                parse_main_text(paper, tokens).unwrap()
                continue
            case TokenType.FOOTNOTE:
                parse_footnote(paper, tokens).unwrap()
                continue
            case TokenType.PICTURE:
                parse_figure(paper, tokens).unwrap()
            case TokenType.TABLE:
                parse_table(paper, tokens).unwrap()
            case TokenType.LIST_ITEM:
                parse_list_item(paper, tokens).unwrap()
            case _:
                assert 0, token.type
    return 
    
    
    

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    paper = Paper("", "", [], [], [], [], [])
    testfile = Path("pdf/EC2025/data/recid_2003647/IPSJ-EC2025001.pdf")
    ts = TokenStream(testfile)
    parse_paper(paper, ts).unwrap()
    print(paper)
    exit(0)