from __future__ import annotations

import re
from returns.primitives.exceptions import UnwrapFailedError
from returns.result import safe, Success, Failure

from pdf_types import Figure, Footnote, Paper, Paragraph, Reference, Section, Table

from .stream import ExceptionReport, TokenStream, exception_report
from .tokens import Token, TokenType


def split_list_items(lines: list[str]) -> list[str]:
    """
    list_itemのcontentに複数の箇条書きが含まれてしまっている場合に、
    箇条書きごとにcontentを分割する
    """
    list_items: list[str] = []
    for line in lines:
        if len(line) == 0:
            continue
        if (
            re.match(r"(\(|（|\[|\*)[0-9a-zA-Z]{0,3}(\)|）|\])(.{3,})", line) is not None
            or len(list_items) == 0
        ):
            list_items.append("")
        list_items[-1] += line
    return list_items


def split_footnotes(lines: list[str]) -> list[str]:
    """
    footnotesのcontentに複数の箇条書きが含まれてしまっている場合に、
    箇条書きごとにcontentを分割する
    """
    list_items: list[str] = []
    for line in lines:
        if len(line) == 0:
            continue
        if re.match(r"(\[[0-9a-zA-Z]{0,3}\]|\*|[a-zA-Z]\))", line) is not None or len(list_items) == 0:
            list_items.append("")
        list_items[-1] += line
    return list_items


@safe(exceptions=(ExceptionReport, UnwrapFailedError))
def parse_list_item(paper: Paper, tokens: TokenStream) -> None:
    assert len(paper.sections) > 0, "セクションがまだ一つも追加されていません。セクションを追加してください。"

    paragraphs = paper.sections[-1].paragraphs_below
    # 一度もまだ段落が構成されていないか、前の段落が段落ではなかった場合には新しく箇条書きの段落を作る
    if len(paragraphs) == 0 or not paragraphs[-1].is_enumrated:
        paragraphs.append(Paragraph("", [], True))

    last_paragraph = paragraphs[-1]
    while not tokens.empty() and tokens.next().unwrap().type == TokenType.LIST_ITEM:
        list_item_raw = tokens.expect("リスト", tokentypes={TokenType.LIST_ITEM}).unwrap()
        last_paragraph.content += list_item_raw.content + "\n"
        for item in split_list_items(list_item_raw.lines):
            last_paragraph.list_items.append(item)


@safe(exceptions=(ExceptionReport,))
def extract_fig_caption_from_stringize_content(figure: Figure, tokens: TokenStream):
    match = re.search(r"図[0-9]{1,2}(.*)$", figure.stringize_content)
    if match == None:
        raise exception_report(tokens, "画像のトークンの中に図のキャプションが入っていません")
    (start, end) = match.span()
    return figure.stringize_content[start:end]

@safe(exceptions=(ExceptionReport,))
def extract_tab_caption_from_stringize_content(table: str, tokens: TokenStream):
    match = re.search(r"\|表(\*\*)?[0-9]{1,2}(\*\*)?(\||<br>)?([^|].*)\|", table)
    if match == None:
        raise exception_report(tokens, f"表のトークンの中に表のキャプションが入っていません: {table}")
    (start, end) = match.span()
    return re.sub(r"\*\*|<br>|\|", "", table[start:end])

@safe(exceptions=(ExceptionReport,))
def split_caption_number_title(caption: str, tokens: TokenStream):
    matched = re.match(r"(図|表)(?P<number>[0-9]+)\s*(?P<title>.+)$", caption.strip())
    if matched == None:
        raise exception_report(tokens, f"図・表のキャプションが指定された形式に則っていません。: {caption}")
    number = matched["number"]
    title = matched["title"]
    assert isinstance(number, str) and isinstance(title, str)
    return (int(number), title)


@safe(exceptions=(ExceptionReport, UnwrapFailedError))
def parse_figure(paper: Paper, tokens: TokenStream) -> None:
    figure = Figure("", -1, "unknown", None)
    while not tokens.empty() and tokens.next().unwrap().type == TokenType.PICTURE:
        figure.stringize_content += tokens.pop("図の内容").unwrap().content

    if tokens.empty():
        caption = extract_fig_caption_from_stringize_content(figure, tokens).unwrap()
    else:
        caption_token = tokens.next().unwrap()
        correct_type = caption_token.type in {TokenType.CAPTION, TokenType.LIST_ITEM, TokenType.TEXT, TokenType.SECTION_HEADER}
        is_caption_title = caption_token.content.startswith("図")
        if correct_type and is_caption_title:
            token = tokens.pop("キャプション").unwrap()
            caption = token.content
        else:
            caption = extract_fig_caption_from_stringize_content(figure, tokens).unwrap()
            print(caption)
    (figure.number, figure.title) = split_caption_number_title(caption, tokens).unwrap()
    paper.figures.append(figure)


@safe(exceptions=(ExceptionReport, UnwrapFailedError))
def parse_table(paper: Paper, tokens: TokenStream, with_caption:bool) -> None:
    number:int = -1
    title:str = ""
    if with_caption:    
        caption = tokens.expect("表キャプション", {TokenType.TEXT, TokenType.LIST_ITEM, TokenType.CAPTION}).unwrap().content
        (number, title) = split_caption_number_title(caption, tokens).unwrap()
        table = tokens.expect("表", {TokenType.TABLE}).unwrap()
    else:
        table = tokens.expect("表", {TokenType.TABLE}).unwrap()
        caption= extract_tab_caption_from_stringize_content(table.content, tokens).unwrap()
        (number, title) = split_caption_number_title(caption, tokens).unwrap()
    paper.tables.append(Table(table.cells, table.content, number, title, ""))



@safe(exceptions=(ExceptionReport, UnwrapFailedError))
def parse_footnote(paper: Paper, tokens: TokenStream) -> None:
    footnote = tokens.pop("脚注").unwrap()
    items = split_footnotes(footnote.lines)
    for item in items:
        matching = re.match(
            r"(?P<sign>(\*\[[a-zA-Z0-9]{1,2}\])|[0-9]|((_|\*){1,2})|([a-z]\)))\s*(?P<content>.+)",
            item,
        )
        if matching is not None:
            sign = matching["sign"]
            content = matching["content"]
            assert isinstance(sign, str) and isinstance(content, str)
            paper.footnotes.append(Footnote(sign, content))
        else:
            paper.footnotes.append(Footnote("", item))


def parse_header_line(string: str) -> Section:
    header_pattern = r"(?P<number>([0-9]{1,2}\.)*[0-9]{1,2}\.?)\s*(?P<title>.+)$"
    header_match = re.match(header_pattern, string)
    if header_match is None:
        return Section("", string, [])

    number = header_match["number"]
    part_name = header_match["title"]
    assert isinstance(number, str) and isinstance(part_name, str)
    return Section(number, part_name, [])


@safe(exceptions=(ExceptionReport, UnwrapFailedError))
def parse_section_header(paper: Paper, tokens: TokenStream) -> None:
    header = tokens.pop("節タイトル").unwrap().content
    assert isinstance(header, str)
    paper.sections.append(parse_header_line(header))


def is_new_paragraph(paragraph: Token) -> bool:
    return len(paragraph.line_x0) == 1 or len(set(paragraph.line_x0)) > 1


@safe(exceptions=(ExceptionReport,))
def last_non_list_paragraph(section: Section, tokens: TokenStream) -> Paragraph:
    idx = len(section.paragraphs_below) - 1
    while section.paragraphs_below[idx].is_enumrated:
        idx -= 1
        if idx < 0:
            raise exception_report(tokens, "箇条書きでないパラグラフがこれより前に見つかりませんでした。")
    return section.paragraphs_below[idx]


@safe(exceptions=(ExceptionReport, UnwrapFailedError))
def parse_main_text(paper: Paper, tokens: TokenStream) -> None:
    assert len(paper.sections) > 0, "セクションがまだ一つも追加されていません。セクションを追加してください。"
    last_section = paper.sections[-1]
    popped = tokens.pop("本文").unwrap()
    if len(last_section.paragraphs_below) == 0:
        last_paragraph = Paragraph("", [], False)
        last_section.paragraphs_below.append(last_paragraph)
    else:
        last_paragraph = last_non_list_paragraph(last_section, tokens).unwrap()
        terminated= last_paragraph.content.strip().endswith(("．", "。", ". ", "."))
        if is_new_paragraph(popped) and terminated:
            last_paragraph = Paragraph("", [], False)
            last_section.paragraphs_below.append(last_paragraph)
    for idx, line in enumerate(popped.lines):
        # 誤って別のセクションのタイトルが入り込んでしまっている時
        if re.match(r"[0-9]{1,2}((\.[0-9]{1,2})+|\.)", line) is not None and popped.line_starts_with_bold[idx]:
            last_section = parse_header_line(line)
            paper.sections.append(last_section)
        else:
            last_paragraph.content += line


@safe(exceptions=(ExceptionReport, UnwrapFailedError))
def parse_abstract(paper: Paper, tokens: TokenStream):
    abstract = tokens.expect_pattern("概要", patterns=r"概要\s*(:|：)\s*(.+)").unwrap()[2]
    assert isinstance(abstract, str)
    paper.abstract = abstract


@safe(exceptions=(ExceptionReport, UnwrapFailedError))
def parse_keywords(paper: Paper, tokens: TokenStream):
    keywords_result = tokens.expect_pattern("キーワード", patterns=r"キーワード\s*(:|：)\s*(.+)$")
    match keywords_result:
        case Success(keywords):
            keywords = keywords[2]
            assert isinstance(keywords, str)
            keywords = re.split(r"，", keywords)
            for keyword in keywords:
                assert isinstance(keyword, str)
            paper.keywords = keywords
        case Failure(err):
            paper.keywords = []

@safe(exceptions=(ExceptionReport, UnwrapFailedError))
def parse_paper_head(paper: Paper, tokens: TokenStream) -> None:
    title = tokens.expect("タイトル", tokentypes={TokenType.TITLE}).unwrap()
    paper.title = title.content
    tokens.expect("著者群").unwrap()
    parse_abstract(paper, tokens).unwrap()
    parse_keywords(paper, tokens).unwrap()


@safe(exceptions=(ExceptionReport, UnwrapFailedError))
def parse_references(paper: Paper, tokens: TokenStream) -> None:
    tokens.expect("参考文献", {TokenType.SECTION_HEADER}).unwrap()
    while not tokens.empty():
        next_token = tokens.next().unwrap()
        if next_token.type in {TokenType.LIST_ITEM, TokenType.TEXT}:
            popped = tokens.pop("参考文献リスト").unwrap()
            for line in popped.lines:
                matched = re.match(r"(?P<number>\[[0-9]{1,4}\])(?P<content>.+)", line)
                if matched is None:
                    paper.references[-1].content += line
                else:
                    assert isinstance(matched["number"], str) and isinstance(matched["content"], str)
                    paper.references.append(Reference(matched["number"], matched["content"]))
        elif next_token.type == TokenType.SECTION_HEADER:
            return
        else:
            tokens.pop("読み捨て").unwrap()
            continue


def is_actually_table_caption(tokens: TokenStream) -> bool:
    token1 = tokens.next().unwrap()
    token2 = tokens.next(1).unwrap()
    return re.match(r"表[0-9]{1,2}(.*)", token1.content) != None and token1.line_starts_with_bold[0] and token2.type == TokenType.TABLE


def is_actually_footnote(token: Token) -> bool:
    return re.match(r"\*\[", token.content) != None or re.fullmatch(r"[0-9]{1,2}[^\)\]].{1,7}", token.content) != None


def is_actually_section_header(token: Token) -> bool:
    return re.match(r"[0-9]{1,2}\.([0-9]{1,2})?\.?", token.content) != None and token.line_starts_with_bold[0]

def is_actually_table(token: Token) -> bool:
    return re.match(r"表[0-9]{1,2}(.+)$", token.content) != None 

@safe(exceptions=(ExceptionReport, UnwrapFailedError))
def parse_table_from_picture_fallback(paper:Paper, tokens:TokenStream) -> None:
    token = tokens.pop("表（図に対するフォールバック）").unwrap()
    token_content = "\n".join(token.lines)
    matches= re.match(r"表(?P<number>[0-9０-９]{1,2})(?P<title>.*)", token.lines[0])
    if matches == None: 
        raise exception_report(tokens, "図に対する表のパース処理中に、表タイトルが見つかりませんでした。")
    number = matches["number"]
    title = matches["title"]
    assert isinstance(number, str) and isinstance(title, str)
    cells:list[list[str | None]] = [[line] for line in token.lines]
    content = "|".join("".join(map(lambda cell: cell if cell != None else "", row)) for row in cells)
    paper.tables.append(Table(cells, content, int(number), title, None))



@safe(exceptions=(ExceptionReport, UnwrapFailedError))
def parse_paper(paper: Paper, tokens: TokenStream) -> None:
    tokens.expect("ページヘッダ", tokentypes={TokenType.PAGE_HEADER}).unwrap()
    parse_paper_head(paper, tokens).unwrap()
    while not tokens.empty():
        next_token = tokens.next().unwrap()
        match next_token.type:
            case TokenType.PAGE_HEADER:
                tokens.expect("ページヘッダ", {TokenType.PAGE_HEADER}).unwrap()
                continue
            case TokenType.PAGE_FOOTER:
                tokens.expect("ページフッタ", {TokenType.PAGE_FOOTER}).unwrap()
                continue
            case TokenType.SECTION_HEADER:
                if next_token.content != "参考文献":
                    parse_section_header(paper, tokens).unwrap()
                else:
                    parse_references(paper, tokens).unwrap()
                continue
            case TokenType.TEXT:
                # SECTION_HEADER, FOOTNOTEが誤ってこれと判別されているケースがあるのでその対処
                if is_actually_footnote(next_token):
                    parse_footnote(paper, tokens).unwrap()
                elif is_actually_table_caption(tokens):
                    parse_table(paper, tokens, True).unwrap()
                elif is_actually_section_header(next_token):
                    parse_section_header(paper, tokens).unwrap()
                else:
                    parse_main_text(paper, tokens).unwrap()
                continue
            case TokenType.FOOTNOTE:
                parse_footnote(paper, tokens).unwrap()
                continue
            case TokenType.PICTURE:
                if is_actually_table(next_token):
                    parse_table_from_picture_fallback(paper, tokens).unwrap()
                else:
                    parse_figure(paper, tokens).unwrap()
            case TokenType.TABLE:
                parse_table(paper, tokens, False).unwrap()
            case TokenType.LIST_ITEM:
                if is_actually_footnote(next_token):
                    parse_footnote(paper, tokens).unwrap()
                elif is_actually_table_caption(tokens):
                    parse_table(paper, tokens, True).unwrap()
                else:
                    parse_list_item(paper, tokens).unwrap()
            case TokenType.CAPTION:
                parse_table(paper, tokens, True).unwrap()
            case _:
                assert 0, next_token.type
    return
