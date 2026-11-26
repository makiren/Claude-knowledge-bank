---
name: kb-save
description: 開発・投資で得た知見を個人 knowledge bank (D:\Claude-knowledge-bank の OKF v0.2 bundle) に保存する。ユーザーが「ナレッジ保存」「これ記録して」「knowledge bank に入れて」と言ったとき、またはセッションで得た再利用価値のある知見 (設計判断・実装パターン・解決したエラー・調査結果・企業分析・IR 由来の知見・銘柄比較) を永続化するときに使う。
---

# kb-save — 知見を knowledge bank に保存する

bundle root: `D:\Claude-knowledge-bank\knowledge\` (OKF v0.2 準拠)

この文書のパスとコマンドは Windows (デスクトップ) のものである。Macbook では次のように読み替える。

- bundle root は `~/Claude-knowledge-bank/knowledge/`。`D:\Claude-knowledge-bank` は `~/Claude-knowledge-bank` に、パス区切りの `\` は `/` に読み替える。
- 時刻は `Get-Date -Format o` の代わりに
  `python3 -c "import datetime; print(datetime.datetime.now().astimezone().isoformat(timespec='seconds'))"` で取得する。

## 手順

1. **最新化 (必須)**: `git -C D:\Claude-knowledge-bank\knowledge pull --no-rebase` で bundle を最新にしてから始める。
   もう一方の拠点で保存された知見を取り込み、重複確認を最新の内容で行うためである。
   - 前のセッションの未コミットの変更が残っていて pull が止まる場合は、内容を確かめてその分だけ先にコミットし、もう一度 pull する。
   - 競合したら両方の行を残す (`log.md` は新しい日付を上に、各 `index.md` は行を足す)。
   - ネットワークに繋がらないなどで pull できない場合は、そのまま保存を続け、最新でない状態から始めたことを報告する。
2. **重複確認 (必須)**: `knowledge\index.md` → 該当エリアの index.md を読み、Grep で本文・tags も検索する。
   既存概念が同じ主題を扱っていれば、新規作成せず**その概念を更新**して `generated.at` を今の時刻にする。
3. **置き場所と type を決める**:

   | ディレクトリ | type | 内容 |
   |---|---|---|
   | projects/ | Project | プロジェクト固有の文脈・制約・現状 |
   | decisions/ | Decision | 技術選定・設計判断と理由 |
   | patterns/ | Pattern | 再利用可能な実装パターン・手順 |
   | troubleshooting/ | Troubleshooting | 解決済みエラーの原因と対処 |
   | references/ | Reference | 外部リソースの要約と評価 (両ドメイン共通) |
   | companies/ | Company | 企業ごとの理解 (事業構造・企業理念・IR 由来の知見) |
   | analyses/ | Analysis / Thesis / Earnings / Factor | 比較分析・投資仮説・決算メモ・ファクター知見 |

   どれにも合わなければ新しい type 値を使ってよい (OKF は type を固定しない)。
4. **概念ファイルを書く**: ファイル名は kebab-case。時刻は `Get-Date -Format o` で取得する。

   ```markdown
   ---
   type: <上の表から>
   title: <表示名>
   description: <一文の要約。index とグラフ検索結果に載る>
   tags: [<小文字 kebab-case>]
   status: stable            # 未確定の内容なら draft
   generated: { by: claude-code/<自分の model id>, at: <ISO 8601> }
   sources:                  # 外部情報から導出した場合のみ
     - id: <安定キー>
       resource: <URL または bundle 相対パス>
       title: <ラベル>
   stale_after: <YYYY-MM-DD> # 時間経過で陳腐化する内容のみ
   ---

   # <本文。見出し・表・コードフェンスで構造化。生ログではなく圧縮した知見を書く>
   ```

   `generated.by` の接頭辞には、実行しているハーネスの名前を書く。Claude Code は `claude-code/<model id>`、
   OpenCode は `opencode/<model id>` とする。

5. **リンクを張る**: 関連する既存概念へ bundle 相対リンク (`[title](/decisions/xxx.md)` 形式) を本文に入れる。
   未執筆だが関連するはずの概念へのリンクも許容される (知識ギャップとしてグラフに現れる)。
6. **index.md 更新**: 置いたディレクトリの index.md に `* [title](file.md) - description` を追加。
7. **log.md 更新**: bundle root の `log.md` の今日の日付セクション (無ければ新設、新しい日付が上) に
   `* **Creation**: ...` / `* **Update**: ...` を追記。
8. **同期**: `uv run D:\Claude-knowledge-bank\scripts\kb_sync.py`
   Neo4j 未起動で失敗しても、概念ファイルの保存はできている。「後で /kb-maintain で同期」と伝えて手順 9 に進む。
9. **commit & push (必須)**: knowledge 側 (親リポジトリとは別の repo) で、今回追加・更新した概念ファイルと `index.md`・`log.md` を
   コミットして push する。コミットメッセージには、何を追加・更新したかを一文で書く。手順 8 の同期に失敗していても行う。
   push が拒否されたら、手順 1 と同じように pull してからもう一度 push する。
   push できなかった場合は、未 push のコミットが残っていることを報告する。

## 固有知識と汎用知識の切り分け (重要)

- 判定基準は「**別のプロジェクトでもそのまま役立つか**」。
  - Yes → patterns/ decisions/ troubleshooting/ references/ (汎用側)。**本文の主語をプロジェクト名にしない**。
  - No (製品・システム固有の文脈・構成・経緯) → projects/ の該当概念へ。
- 両方の性質を持つ知見は **1 概念にせず分割**し、汎用概念からリンクで projects/ 概念を
  出典参照する (「どこで学んだか」はリンクとして残り、グラフで辿れる)。
- プロジェクト固有の設計判断の正は各リポジトリの docs/DESIGN.md (グローバル CLAUDE.md §2)。
  KB の projects/ はその要約・横断参照用ポインタに留め、二重管理しない。
- 投資ドメインも同型: 銘柄固有の事実 → companies/、横断的な手法・比較・仮説 → analyses/。

## 品質規則

- 1概念 = 1主題。独立した知見が複数あれば複数ファイルに分ける。
- What (コードの写し) ではなく Why (判断理由・落とし穴・制約) を書く。
- 次のセッションの自分が3分で読める密度に圧縮する。会話ログを貼らない。
- ユーザーが確認・承認した事実には `verified: { by: human:makishima, at: <ISO 8601> }` を付ける。
- 相対日付 (「先週」等) は絶対日付に変換して書く。

## 投資知見の追加規則

- 銘柄概念は `companies/<証券コード>-<社名ローマ字>.md` (例: `7203-toyota.md`)。
  frontmatter に拡張キー `ticker: "7203"` (必要なら `market: TSE-Prime`) を付ける (グラフに写る)。
- IR・決算由来の事実は `sources` 必須。決算短信・説明資料・有報の URL (EDINET / TDnet リンク推奨) を記録する。
- 業績・バリュエーションに依存する知見 (割安判断・目標株価・PER 比較等) には
  `stale_after` を付ける (目安: 次回決算発表日)。企業理念・事業構造など長寿命の知見には不要。
- 事実 (数値・開示内容) と解釈 (自分の分析・仮説) を本文の見出しで分ける。
  解釈は `status: draft` から始め、検証されたら stable に上げる。
- 比較分析は analyses/ に置き、対象の companies/ 概念へリンクする (グラフで銘柄→分析を逆引きできる)。
