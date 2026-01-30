"""CLI引数の解析と全体フローの実行を担当する。"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from tqdm import tqdm

from output.overview import (
    summarize_references,
    summarize_segments,
    summarize_warnings,
    write_overview_csv,
)
from output.pipeline import tidy_up_paper_folder


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Entertainment Computing 論文PDFとメタデータを整理して出力します。"
    )
    parser.add_argument("root_path", type=Path, help="data/recid_* を含むルートディレクトリ。")
    parser.add_argument("-o", "--out_path", type=Path, help="出力先ディレクトリ。", default="./result")
    parser.add_argument("-v", "--verbose", type=bool, help="詳細ログを出力します。", default=False)
    args = parser.parse_args()
    root_path = args.root_path
    out_path = args.out_path
    logging.basicConfig(level=logging.INFO if args.verbose else logging.ERROR)
    assert isinstance(root_path, Path)
    assert isinstance(out_path, Path)
    paths = list(root_path.glob("./data/recid_*/*.pdf"))
    overview_rows: list[dict[str, str | int]] = []

    for path in tqdm(paths):
        if path.is_dir():
            continue
        metadata, paper = tidy_up_paper_folder(path, out_path)
        warning_summary = summarize_warnings(paper)
        segment_summary = summarize_segments(paper)
        reference_summary = summarize_references(paper)
        overview_rows.append(
            {
                "paper_title": metadata.get("title", ""),
                "pdf_path": str(path),
                **segment_summary,
                **reference_summary,
                **warning_summary,
            }
        )
    write_overview_csv(out_path, overview_rows)
