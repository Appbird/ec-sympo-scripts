from dataclasses import dataclass
from logging import info
from pathlib import Path
from typing import Any, Self, TypeVar
from returns.result import safe, ResultE, Success, Failure
from returns.primitives.exceptions import UnwrapFailedError
from returns.maybe import Maybe, Some, Nothing

import re

from pdf_types import Figure, Footnote, Paper, Section, Table
from util import clean_multiline_literal

T = TypeVar("T")

@dataclass
class LineStream:
    filename:str
    lines:list[str]
    at:int = 0
    
    def surroundings(self, r:int) -> list[str]:
        return self.lines[(self.at - r):(self.at + 1 + r)]
    
    def location(self) -> int: return self.at

    def _skip_empty_lines(self):
        while self.at < len(self.lines) and len(self.lines[self.at]) == 0:
            self.at += 1

    def pop(self:Self, what_expect:str = "") -> Maybe[str]:
        self._skip_empty_lines()
        result:Maybe[str] = Nothing
        if self.at == len(self.lines):
            info(f"Expect = {what_expect}, actual = end")
        else:
            info(f"Expect = {what_expect}, actual = {self.lines[self.at]}")
            result = Some(self.lines[self.at])
        self.at += 1
        return result
    def next(self:Self, what_expect:str = "") -> Maybe[str]:
        self._skip_empty_lines()
        result:Maybe[str] = Nothing
        if self.at != len(self.lines):
            result = Some(self.lines[self.at])
        return result

    def expect(self, pattern:str, what_expect:str) -> ResultE[re.Match[str]]:
        match self.pop(what_expect):
            case Some(tested):
                matched = re.match(pattern, tested)
                if matched == None: return Failure(exception_report(self, f"`{what_expect}として{pattern}`にマッチする行が来るはずなのに、`{tested}`という行が来てしもうたね。"))
                else: return Success(matched)
            case Nothing:
                return Failure(exception_report(self, f"`{what_expect}として{pattern}`にマッチする行が来るはずなのに、もう行切れしてもうたね。"))
    

    def skip(self, what_expect:str) -> ResultE[None]:
        match self.pop(what_expect):
            case Some(popped):
                info(f"ignore line `{popped}` as {what_expect}")
                return Success(None)
            case Nothing:      return Failure(exception_report(self, f"`{what_expect}が来るはずなのに、もう行切れしてもうたね。"))
    
    def empty(self:Self) -> bool:
        return self.at >= len(self.lines) - 1

@dataclass
class ExceptionReport(Exception):
    filename:str
    current_posititon:int
    surroundings:list[str]
    exception:str
    def __str__(self):
        return clean_multiline_literal(f"""
        ❗️Exception: {self.exception}
        at {self.filename}:{self.current_posititon + 1}
        
        ========================
        {"\n".join(self.surroundings)}
        ========================
        """)

def exception_report(lines:LineStream, err:str):
    return ExceptionReport(
        lines.filename,
        lines.location(),
        lines.surroundings(2),
        err
    )

def expect(m:Maybe[T], err:str) -> T:
    match m:
        case Some(x): return x
        case Nothing: raise Exception(err)

@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_figure(paper:Paper, lines:LineStream) -> None:
    raise NotImplementedError()


@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_table(paper:Paper, lines:LineStream) -> None:
    raise NotImplementedError()

@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_footnote(paper:Paper, lines:LineStream) -> None:
    footnote = lines.expect(r">\s*(?P<sign>[_*\[\]a-zA-Z0-9()]+)\s+(?P<content>.+)", "節タイトル").unwrap()
    sign = footnote["sign"]
    content = footnote["content"]
    assert isinstance(sign, str) and isinstance(content, str)
    paper.footnotes.append(Footnote(sign, content))


@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_section(paper:Paper, lines:LineStream) -> None:
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
def parse_paper_title(paper:Paper, lines:LineStream) -> None:
    lines.skip("ヘッダ").unwrap()
    
    title = lines.expect(r"#\s*(.+)", "論文タイトル").unwrap().group(1)
    assert isinstance(title, str)
    title= title.replace("*", "")
    paper.title = title
    
    lines.skip("著者名").unwrap()

    abstract = lines.expect(r"概要：\s*(.+)", "概要").unwrap().group(1)
    assert isinstance(abstract, str)
    abstract= abstract.replace("*", "")
    paper.abstract = abstract

    keywords = lines.expect(r"キーワード：\s*(.+)", "キーワード").unwrap().group(1)
    assert isinstance(keywords, str)
    keywords= keywords.split("，")
    paper.keywords = keywords
    return


    
    

@safe(exceptions=(ExceptionReport,UnwrapFailedError))
def parse_paper(paper:Paper, lines:LineStream) -> None:
    parse_paper_title(paper, lines).unwrap()
    while not lines.empty():
        parse_section(paper, lines).unwrap()
    return 
    
    
    

if __name__ == "__main__":
    paper = Paper("", "", [], [], [], [], [])
    testfile = "./test/parser/test2.in"
    text = Path(testfile).read_text(encoding="utf-8")
    lines = text.splitlines()
    lines = map(lambda s: s.strip(), lines)
    lines = list(lines)
    lines = LineStream(filename=testfile, lines=lines)

    parse_paper(paper, lines).unwrap()
    print(paper)