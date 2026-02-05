# 目的
情報処理学会電子図書館に掲載されたエンタテインメントコンピューティング・シンポジウム予稿集PDFを解析し、論文ごとの構造化データを生成する。

# 動機
ECシンポジウムでどのような研究が行われ、どのような評価がなされているかについて体系的な整理がまだ進んでいない。整理を試みるには、これまでEC学術領域に投稿された論文データを解析する必要がある。例えば、段落・節ごとに読み取れる区分けはトピック分析などで重要となる一方、それらをPDFから読み取るのは必ずしも自明な課題ではない。そこで本リポジトリでは、論文PDFを読み取り、段落・節の構造をJSON形式で記述されたデータへ変換するスクリプトを提供する。

# 機能（CLI仕様）
コマンドラインから指定したルート配下のPDFを解析し、出力先に整理された成果物を生成する。

```sh
uv tool install https://github.com/Appbird/ec-sympo-scripts.git
ec_scripts ROOT_PATH [-o OUT_PATH] [-v]
```

```py
from ec_scripts import tidy_up_paper_folder, parse_metadata_and_paper, parse_paper_only, simplify_metadata_of_paper
```

ROOT_PATH には `data/recid_*` を含むルートディレクトリを指定する。`-o` / `--out_path` は出力先ディレクトリで、既定は `./result`。`-v` / `--verbose` を付けると詳細ログを出力する。

出力例として、論文単位のフォルダには `metadata.json`（メタデータの簡略化結果）、`content.json`（本文構造とセグメント情報）、`fallbacks.json`（警告やフォールバック情報）、`paper.pdf`（元PDFのコピー）が生成される。加えて、全体集計の `overview.csv` が出力先のルートに作成される。

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
