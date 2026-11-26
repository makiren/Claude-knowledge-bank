# Claude Knowledge Bank — Design

本プロジェクトの設計の正 (source of truth)。設計に関わる変更はまずここを更新する。

## 1. 目的

セッションを跨いで開発知識を蓄積し、次以降の開発に活かす個人ナレッジ基盤。

- **Google OKF (Open Knowledge Format) v0.2** 準拠の markdown bundle を知識の正とする
- **Neo4j** を関連知識の想起・グラフ探索のための派生インデックスとする
- **Claude Code のグローバル Skills** (`/kb-save` `/kb-search` `/kb-maintain`) で
  Hermes Agent 的な「経験 → 知識化 → 再利用」ループを実現する (当面は手動駆動)

## 2. アーキテクチャ

```
[任意のプロジェクトの Claude Code セッション]
    │ /kb-save     知見を OKF 概念として書き込む
    │ /kb-search   index 探索 + Grep + Cypher で想起する
    │ /kb-maintain 検査・同期・Neo4j 起動
    ▼
knowledge/                     ← source of truth (OKF v0.2 bundle, 独立 private repo で 2 拠点同期)
    │ scripts/kb_sync.py       ← 全再構築・冪等
    ▼
Neo4j (Docker, bolt://localhost:7687)  ← 派生インデックス。使い捨て可
```

## 3. 決定事項

| # | 決定 | 理由 |
|---|---|---|
| D1 | markdown (OKF bundle) を正、Neo4j は派生インデックス | OKF の思想通りファイルが可読・diffable・可搬。グラフは `MATCH` で欲しいときだけ使い、壊れても `kb_sync.py` で再生成できる |
| D2 | 同期は差分でなく full rebuild (Concept/Tag/Source ラベルのみ削除→再構築) | 個人 KB の規模では差分同期の複雑さに見合わない。冪等で失敗時のリカバリも「再実行」のみ |
| D3 | Skills の実体は本リポジトリ `skills/`、`~/.claude/skills/kb-*` へは junction | 全プロジェクトから使えるグローバル配置と、一元管理・git 履歴を両立 |
| D4 | フルループ自動化 (SessionStart リコール / Stop nudge) は初期スコープ外 | まず知識の書式と運用を手動コマンドで安定させる。§7 参照 |
| D5 | スクリプトは uv の PEP 723 single-file script | venv 管理不要。`uv run scripts/kb_sync.py` だけで動く |
| D6 | リンク切れは「未執筆の知識」としてグラフに `missing: true` ノードで残す | OKF 仕様がリンク切れを not-yet-written knowledge として許容。知識ギャップの可視化に転用する |
| D7 | Neo4j は Docker Compose (`neo4j:5.26-community`)、認証情報は `.env` (gitignore) | 再現性。5.26 は LTS |
| D8 | auto-memory 書き込みを trigger に kb-save を nudge する hook (2026-08-13 追加、ユーザー承認済) | memory を書く瞬間 = 知見の永続化を判断している瞬間。PostToolUse hook がリマインダーを注入し、保存判断自体は Claude が行うので KB は汚れない。D4 のフルループとは別の、ピンポイント自動化 |
| D9 | リポジトリは仕組みのみ公開 (GitHub public)、`knowledge/` は gitignore でローカル専用 (2026-08-13、ユーザー指示。置き場所は D10 で改訂 — 公開リポジトリに知識を置かない原則は不変) | 個人の分析・投資仮説を外に出さない。知識の更新履歴は git でなく bundle 内の log.md が担う (OKF の規約通り)。公開履歴に知識が残らないよう初回コミットは作り直した |
| D10 | `knowledge/` を独立した **private repo** ([Claude-knowledge-bundle](https://github.com/makiren/Claude-knowledge-bundle)) としてネストし、GitHub 経由でデスクトップ (Windows) / Macbook の 2 拠点を同期する (2026-08-17、ユーザー承認済) | 知識の正が markdown (D1) なので同期は git 問題に還元でき、Neo4j と kb_graph.html は各マシンで `kb_sync.py` / `kb_viz.py` により再構築すればよい (使い捨て派生の帰結)。親リポジトリは `knowledge/` を ignore 済みなのでネストは無干渉。**bundle repo はテキストのみ** — PDF 等のバイナリは `sources` の URL 参照か `downloads/` (ローカル) に置く。容量 (現状 64KB、GitHub 推奨上限 1GB) と機密の両面でこの規約を維持する。知識レベルの更新履歴は引き続き log.md が正、git 履歴は同期・競合解決・復元用 |
| D11 | `/kb-save` と `/kb-search` は、開始時に `git -C knowledge pull` で bundle を最新にする。`/kb-save` は終了時に knowledge 側で commit & push する (2026-11-26、ユーザー指示) | D10 の同期手順は CLAUDE.md と SETUP-MACOS.md にだけ書いてあり、スキルの手順には無かった。スキルは他のプロジェクトのセッションからも呼ばれるので、これらの文書が読まれないまま保存されることがある。2026-11-26 には、2026-10-08 の保存分が未コミットで残り、リモートが 15 コミット先行していた。スキルの手順に入れておけば、どのセッションから呼んでも同期の手順が読まれる。pull できないときも検索と保存は止めず、最新でない状態から始めたことを報告する |

## 4. OKF bundle 規約

- bundle root は `knowledge/`。root の `index.md` に `okf_version: "0.2"` を宣言
- 予約ファイル: `index.md` (各ディレクトリの目次)、`log.md` (bundle root の更新履歴)
- タクソノミ (ディレクトリ = 概念の種類。OKF は type を固定しないので必要なら追加可):

| ディレクトリ | type | 内容 |
|---|---|---|
| `projects/` | Project | プロジェクト固有の文脈・制約・現状 |
| `decisions/` | Decision | 技術選定・設計判断とその理由 |
| `patterns/` | Pattern | 再利用可能な実装パターン・手順 |
| `troubleshooting/` | Troubleshooting | 解決済みエラーの原因と対処 |
| `references/` | Reference | 外部リソースの要約と評価 (両ドメイン共通) |
| `companies/` | Company | 企業ごとの理解 (事業構造・企業理念・IR 由来の知見)。1社 = 1概念、ファイル名 `<証券コード>-<社名>.md` |
| `analyses/` | Analysis | 投資の比較分析・バリュエーション・セクター横断の知見。対象 companies へリンクする |

- 投資系概念の規約 (2026-08-13 追加、ユーザー承認済):
  - `analyses/` の type は `Analysis` のほか、QuantMind の card taxonomy と整合する
    `Thesis` (投資仮説) / `Earnings` (決算メモ) / `Factor` (ファクター知見) を使い分ける
  - 証券コードは frontmatter 拡張キー `ticker` (必要なら `market` も) で持つ。OKF は未知キーを許容する
  - IR・決算由来の事実は `sources` に資料 URL (決算短信・説明資料・有報。EDINET / TDnet リンク推奨) を必ず記録
  - 業績・バリュエーションに依存する知見には `stale_after` を付ける (目安: 次回決算発表日)
  - 開発知見と同一 bundle に同居させ、リンク・タグで横断可能にする (分離しない)
- 固有知識と汎用知識の切り分け (2026-08-13 追加、ユーザー指示):
  製品・システム固有の知見は `projects/` (投資なら `companies/`) に、プロジェクトを跨いで再利用できる
  開発フロー・手法・パターンは `patterns/` `decisions/` `troubleshooting/` に置く。判定基準は
  「別プロジェクトでそのまま役立つか」。両性質を持つ知見は分割して相互リンクする。
  プロジェクト固有の設計の正は各リポジトリの docs/DESIGN.md であり、KB 側は要約ポインタに留める
- actor 規約 (OKF §7): Claude Code は `claude-code/<model-id>`、ユーザーは `human:makishima`。
  OpenCode は `opencode/<model-id>` (2026-11-26 追加。OpenCode のセッションで保存した概念に合わせた事後記録)
- 時刻は ISO 8601 (+09:00)。日付のみのフィールド (`stale_after` 等) は `YYYY-MM-DD`
- 概念の追加・更新時は該当ディレクトリの `index.md` と root の `log.md` を必ず同時更新

## 5. Neo4j グラフモデル

| 要素 | 内容 |
|---|---|
| `(:Concept {id, path, type, title, description, status, stale_after, generated_by, generated_at, missing})` | 概念。`id` = bundle 相対パスから `.md` を除いたもの (OKF Concept ID)。`missing: true` はリンクだけ存在する未執筆概念 |
| `(:Tag {name})` | frontmatter `tags` の各値 |
| `(:Source {resource, title, author})` | frontmatter `sources` の各エントリ |
| `(Concept)-[:LINKS_TO]->(Concept)` | 本文中の markdown リンク (untyped、OKF §6.1 準拠) |
| `(Concept)-[:TAGGED]->(Tag)` | タグ付け |
| `(Concept)-[:DERIVED_FROM]->(Source)` | provenance (OKF §5.1) |

一意性制約: `Concept.id`, `Tag.name`, `Source.resource`。

## 6. コンポーネント

| パス | 役割 |
|---|---|
| `knowledge/` | OKF bundle (source of truth)。独立 private repo としてネスト (D10)、2 拠点同期。運用手順は docs/SETUP-MACOS.md |
| `compose.yml` + `.env` | Neo4j (container 名 `kb-neo4j`, ports 7474/7687, named volume で永続化) |
| `scripts/kb_sync.py` | bundle → Neo4j 全再構築。deps: neo4j, pyyaml |
| `scripts/kb_check.py` | 健全性検査 (OKF 準拠性 / リンク切れ / staleness)。deps: pyyaml のみ (kb_sync と数関数重複させている: uv の script 単位環境分離のため import 共有しない) |
| `scripts/kb_viz.py` | bundle → 自己完結インタラクティブ HTML グラフ (`kb_graph.html`、gitignore)。Neo4j 不要・ブラウザで開くだけの派生ビュー (D1 と同じ位置づけで使い捨て可)。force-directed グラフ + 一覧テーブル、type 別配色・検索・タグ/リンク/sources の詳細パネル、stale/未執筆 (gap) の可視化。deps: pyyaml のみ (kb_sync と数関数重複、kb_check と同じ理由) |
| `scripts/kb_memory_nudge.py` | D8 の PostToolUse hook 本体。`~/.claude/settings.json` の hooks から呼ばれる (memory ディレクトリへの Write/Edit を検知、MEMORY.md は除外)。判断基準はグローバル CLAUDE.md §6 |
| `scripts/edinet.py` | EDINET API v2 クライアント (list / search / get)。キーは `.env` の `EDINET_API_KEY`。書類は `downloads/edinet/` (gitignore) へ。deps: requests |
| `D:\quant-mind` (外部) | QuantMind の checkout。arXiv 論文・米国ニュースの知識精錬に使う agent-native ワークベンチ (`cd D:\quant-mind && claude` で開く)。精錬結果は本 bundle に OKF 概念として保存する — bundle が常に source of truth |
| EDINET DB MCP (外部) | 日本株の構造化財務データの主経路。`~/.claude.json` (user scope) に `edinetdb` として登録、17 ツール。キーは `.env` の `EDINETDB_API_KEY` (REST 用)。詳細は knowledge/references/edinetdb.md |
| `skills/kb-save` `skills/kb-search` `skills/kb-maintain` | Skills の実体。`~/.claude/skills/` から junction |

## 7. 将来拡張 (未実装・提案のみ)

- SessionStart hook で knowledge bank の index を自動注入 (自動リコール)
- Stop hook で「保存すべき知見はないか」を nudge (Hermes フルループ。memory 書き込み時の nudge は D8 で実装済み)
- ベクトル検索 (Neo4j vector index or 別モジュール) による曖昧想起
- QuantMind flows を使った定常収集 (PaperFlow / collect_news)。SEC filings flow が出荷されたら米国開示もカバー可能
- OKF Attested Computation の運用 (公認クエリ + attester)
- `verified` の運用ルール整備 (人間レビューの trust tier 活用)
