# macOS (Macbook) セットアップと 2 拠点同期の運用

デスクトップ (Windows) と Macbook で同じ knowledge bank を使うための手順。
構成の背景は DESIGN.md D10 を参照。

## 構成の要点

- 同期するのは **`knowledge/` (private repo) のテキストだけ**。Neo4j と `kb_graph.html` は
  各マシンのローカル派生物で、pull 後に再構築する
- 親リポジトリ (本リポジトリ、public) は仕組み (scripts / skills / docs / compose) を運ぶ
- `.env` の秘密情報は git に載せない。マシン間はパスワードマネージャ等で手動受け渡し

## 初回セットアップ

前提: git / gh / uv / Docker 互換のコンテナランタイム / Claude Code をインストール済み。

コンテナランタイムについて、当初この欄には「OrbStack 推奨」と書いていたが、この Macbook では OrbStack を使っていない。
実際には Docker Desktop で運用し、2026-11-26 に Kiri へ移行した (docker context は `kiri`)。
以下の `docker compose up -d` などのコマンドは、Kiri でもそのまま使える。
移行の経緯と運用ルールは `knowledge/decisions/local-container-runtime-kiri.md` に書いてある。

```sh
# 1. 仕組み (public) と知識 (private) を clone — knowledge/ は親が gitignore 済みなのでネストして良い
git clone https://github.com/makiren/Claude-knowledge-bank.git
cd Claude-knowledge-bank
git clone https://github.com/makiren/Claude-knowledge-bundle.git knowledge

# 2. 秘密情報 (NEO4J_PASSWORD / EDINET_API_KEY / EDINETDB_API_KEY をデスクトップと同値で)
cp .env.example .env && $EDITOR .env

# 3. Neo4j 起動と派生インデックス構築
docker compose up -d
uv run scripts/kb_sync.py
uv run scripts/kb_check.py

# 4. Skills をグローバル配置 (Windows の junction に相当)
mkdir -p ~/.claude/skills
for s in kb-save kb-search kb-maintain; do
  ln -s "$(pwd)/skills/$s" ~/.claude/skills/$s
done
```

残りの Claude Code 側設定 (マシンごとに再登録が必要):

- **EDINET DB MCP**: user scope (`~/.claude.json`) に `edinetdb` を登録。手順とキーの扱いは
  `knowledge/references/edinetdb.md` を参照
- **memory→kb-save nudge hook (D8)**: `~/.claude/settings.json` の hooks に
  `scripts/kb_memory_nudge.py` を PostToolUse で登録 (パスはこのリポジトリの絶対パスに読み替え)

## 日常の運用 (両マシン共通)

1. **知識を触る作業の開始時**: `git -C knowledge pull` → 変化があれば `uv run scripts/kb_sync.py`
2. **知識を更新したら**: knowledge/ 側で commit & push (親リポジトリとは別の repo であることに注意)
3. 仕組み (scripts/skills) を変えたときだけ親リポジトリも commit & push

1 と 2 は `/kb-save` の手順に、1 は `/kb-search` の手順にも入っている (DESIGN.md D11)。
スキルを使わずに `knowledge/` を直接触るときは、手で行う。

競合したら普通の git マージで解決する。`log.md` と各 `index.md` は両拠点で同日に触ると
衝突しやすいが、いずれも行追加が主なので union 的に両方残せばよい。

## 入れてはいけないもの

- **bundle repo にバイナリを入れない** (PDF・画像・HTML)。決算資料等は `sources` の URL 参照、
  ローカルに欲しければ `downloads/` (gitignore 済み)。容量と機密の両面の規約 (D10)
- `.env`・`kb_graph.html` は従来どおり git 外

## 同期されないもの (仕様)

- Claude Code の auto-memory はマシン・パス固有で同期されない。マシンを跨いで使いたい知見は
  KB 側に置く (グローバル CLAUDE.md §6 の切り分け通り)
- Neo4j の中身。pull 後の `kb_sync.py` で常に再現できる (D1/D2)
