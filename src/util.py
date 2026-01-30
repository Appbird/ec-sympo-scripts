"""共通ユーティリティ関数を提供する。"""

from returns.result import safe

def clean_multiline_literal(literal:str):
    txt = map(lambda s:s.strip(), literal.splitlines())
    txt = list(txt)
    txt = "\n".join(txt)
    return txt
