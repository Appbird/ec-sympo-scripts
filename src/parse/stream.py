from __future__ import annotations

from dataclasses import dataclass
from logging import info
from pathlib import Path
from typing import Self

import re
from returns.maybe import Maybe, Nothing, Some
from returns.result import Failure, ResultE, Success

from pdf2text import pdf2json
from util import clean_multiline_literal

from .tokens import Token, TokenType, doc_to_tokens, dump_tokens


class TokenStream:
    """
    PDFの行単位で書かれている文字内容をストリームする。
    スパン単位ではなく、行単位とするのは、分割がTeX, Wordsのどちらでも一意な方法で分割されるとは限らないため。
    """

    filename: Path
    tokens: list[Token]
    at: int = 0

    def __init__(self, filename: Path):
        doc = pdf2json(filename).unwrap()
        tokens = doc_to_tokens(doc)
        self.filename = filename
        self.tokens = list(tokens)

    def __str__(self) -> str:  # pragma: no cover - debugging aid
        return dump_tokens(self.tokens)

    def surroundings(self, radius: int) -> tuple[list[Token], int]:
        return (self.tokens[self.at - radius : self.at + radius], radius - max(radius - self.at, 0))

    def location(self) -> int:
        return self.at

    def pop(self: Self, what_expect: str) -> Maybe[Token]:
        result: Maybe[Token] = Nothing
        if self.at == len(self.tokens):
            info(f"Expect = {what_expect}, actual = end")
        else:
            info(f"Expect = {what_expect}, actual = {self.tokens[self.at]}")
            result = Some(self.tokens[self.at])
        self.at += 1
        return result

    def next(self: Self, delta:int = 0) -> Maybe[Token]:
        if self.at + delta < len(self.tokens):
            return Some(self.tokens[self.at + delta])
        return Nothing

    def expect(self, what_expect: str, tokentypes: set[TokenType] | None = None) -> ResultE[Token]:
        types = tokentypes or set()
        popped = self.pop(what_expect)
        if popped is Nothing:
            return Failure(
                exception_report(
                    self,
                    f"`{what_expect}として{types}`にマッチする行が来るはずなのに、切れてしまったね。",
                )
            )
        popped = popped.unwrap()
        if types and popped.type not in types:
            return Failure(
                exception_report(
                    self,
                    f"`{what_expect}として{types}`にマッチする行が来るはずなのに、トークン`{popped}`が来てしもうたね。",
                )
            )
        return Success(popped)

    def expect_pattern(
        self, what_expect: str, patterns: str, tokentypes: set[TokenType] | None = None
    ) -> ResultE[re.Match[str]]:
        popped = self.expect(what_expect, tokentypes)
        if isinstance(popped, Failure):
            return popped
        content = popped.unwrap().content
        matching = re.match(patterns, content)
        if matching is None:
            self.at -= 1
            return Failure(
                exception_report(
                    self,
                    f"`{what_expect}として{patterns}`にマッチする行が来るはずなのに、実際には`{content}`が来たね",
                )
            )
        return Success(matching)

    def skip(self, what_expect: str) -> ResultE[None]:
        match self.pop(what_expect):
            case Some(popped):
                info(f"ignore line `{popped}` as {what_expect}")
                return Success(None)
            case Nothing:
                return Failure(
                    exception_report(self, f"`{what_expect}が来るはずなのに、もう行切れしてもうたね。")
                )

    def empty(self: Self) -> bool:
        return self.at >= len(self.tokens) - 1


@dataclass
class ExceptionReport(Exception):
    filename: str
    current_position: int
    surroundings: list[Token]
    exception: str

    def __str__(self) -> str:  # pragma: no cover - formatting only
        return clean_multiline_literal(
            f"""
        ❗️Exception: {self.exception}
        at {self.filename}:{self.current_position + 1}

        ========================
        {dump_tokens(self.surroundings)}
        ========================
        """
        )


def exception_report(tokens: TokenStream, err: str) -> ExceptionReport:
    return ExceptionReport(
        str(tokens.filename),
        tokens.location(),
        tokens.surroundings(2)[0],
        err,
    )
