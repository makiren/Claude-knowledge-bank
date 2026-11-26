<!-- PROFILE: poc -->

# Claude Knowledge Bank

個人開発ナレッジを OKF v0.2 bundle (`knowledge/`) として蓄積し、Neo4j を派生グラフ
インデックスとして使うリポジトリ。**設計の正は `docs/DESIGN.md`** — 設計に触れる前に必ず読む。

## コマンド

| 操作 | コマンド |
|---|---|
| Neo4j 起動 | `docker compose up -d` |
| 同期 (bundle → Neo4j) | `uv run scripts/kb_sync.py` |
| 健全性検査 | `uv run scripts/kb_check.py` |
| グラフ可視化 (HTML 生成) | `uv run scripts/kb_viz.py` → `kb_graph.html` をブラウザで開く |
| Cypher 実行 | `docker exec kb-neo4j cypher-shell -u neo4j -p <NEO4J_PASSWORD> --format plain "<query>"` |
| EDINET 検索/取得 | `uv run scripts/edinet.py search 7203 --days 30` / `... get <docID> --type pdf` |

`NEO4J_PASSWORD` と `EDINET_API_KEY` は `.env` にある (gitignore 済み。無ければ `.env.example` からコピー)。

## 規約

- `knowledge/` は独立した **private repo** ([Claude-knowledge-bundle](https://github.com/makiren/Claude-knowledge-bundle)) としてネストしており、親リポジトリ (public、仕組みのみ) とは別管理。**知識を検索・編集する作業の開始時に `git -C knowledge pull`、編集したら終了時に knowledge 側で commit & push** して 2 拠点 (デスクトップ/Macbook) を同期する (`/kb-save` と `/kb-search` の手順に含まれる。DESIGN.md D11)。bundle repo にバイナリを入れない (PDF 等は URL 参照か `downloads/`)。Mac 側セットアップは `docs/SETUP-MACOS.md`
- `knowledge/` 配下は OKF v0.2 準拠を維持する: 全概念に `type` 必須、予約名は `index.md` / `log.md`
- 概念の追加・更新時は該当ディレクトリの `index.md` と bundle root の `log.md` も同時更新する
- actor 規約: Claude Code は `claude-code/<model-id>`、OpenCode は `opencode/<model-id>`、ユーザーは `human:makishima`
- `skills/` 配下が Skills の実体。`~/.claude/skills/kb-*` は junction なので編集はこのリポジトリ側で行う
- Neo4j 内のデータは使い捨て。グラフスキーマの変更は `scripts/kb_sync.py` を書き換えて全再構築する
