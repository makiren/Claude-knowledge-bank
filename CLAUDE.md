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
| Cypher 実行 | `docker exec kb-neo4j cypher-shell -u neo4j -p <NEO4J_PASSWORD> --format plain "<query>"` |
| EDINET 検索/取得 | `uv run scripts/edinet.py search 7203 --days 30` / `... get <docID> --type pdf` |

`NEO4J_PASSWORD` と `EDINET_API_KEY` は `.env` にある (gitignore 済み。無ければ `.env.example` からコピー)。

## 規約

- `knowledge/` 配下は OKF v0.2 準拠を維持する: 全概念に `type` 必須、予約名は `index.md` / `log.md`
- 概念の追加・更新時は該当ディレクトリの `index.md` と bundle root の `log.md` も同時更新する
- actor 規約: Claude Code は `claude-code/<model-id>`、ユーザーは `human:makishima`
- `skills/` 配下が Skills の実体。`~/.claude/skills/kb-*` は junction なので編集はこのリポジトリ側で行う
- Neo4j 内のデータは使い捨て。グラフスキーマの変更は `scripts/kb_sync.py` を書き換えて全再構築する
