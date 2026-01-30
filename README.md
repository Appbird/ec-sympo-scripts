# 目的
情報処理学会電子図書館に掲載されたエンタテインメントコンピューティング・シンポジウム予稿集PDFを解析し、論文ごとの構造化データを生成する。

# 機能（CLI仕様）
コマンドラインから指定したルート配下のPDFを解析し、出力先に整理された成果物を生成する。

```
python -m src.main ROOT_PATH [-o OUT_PATH] [-v]
```

- `ROOT_PATH`（必須）: `data/recid_*` を含むルートディレクトリ
- `-o`, `--out_path`: 出力先ディレクトリ（既定: `./result`）
- `-v`, `--verbose`: 詳細ログの出力（既定: 無効）

出力例:
- `metadata.json`
- `content.json`
- `fallbacks.json`
- `paper.pdf`
- `overview.csv`

# コード構成（実行順）
1. `src/main.py`  
   実行エントリ。`src/cli.py` の `main()` を呼ぶ。
2. `src/cli.py`  
   CLI引数を処理し、PDF一覧を走査して処理フローを進める。
3. `src/output/pipeline.py`  
   PDFとメタデータを読み込み、論文単位の出力を作成する。
4. `src/metadata/metadata_simplifier.py`  
   メタデータJSONを正規化して簡略化する。
5. `src/parsing/pdf2text.py` → `src/parsing/stream.py` → `src/parsing/paper_parser.py`  
   PDFをトークン化し、論文構造（`Paper`）を構築する。
6. `src/output/overview.py`  
   警告・節・段落・参考文献数を集計して `overview.csv` を出力する。
