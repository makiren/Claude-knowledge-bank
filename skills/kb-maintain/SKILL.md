---
name: kb-maintain
description: knowledge bank (D:\Claude-knowledge-bank) のメンテナンス。Neo4j の起動、OKF bundle の健全性検査 (準拠性・リンク切れ・staleness)、グラフの再同期を行う。「KB 同期して」「knowledge bank のメンテ」「グラフ更新」で使う。
---

# kb-maintain — 検査と同期

作業ディレクトリ: `D:\Claude-knowledge-bank`

この文書のパスとコマンドは Windows (デスクトップ) のものである。Macbook では次のように読み替える。

- 作業ディレクトリは `~/Claude-knowledge-bank`。
- コンテナランタイムは Docker Desktop ではなく Kiri (2026-11-26 に移行)。`docker` が応答しないときは、
  手順 1 の `Start-Process` の代わりに、Kiri が起動しているかを確かめる (ログは `~/.kiri/daemon.log`)。

## 手順

1. **Neo4j 起動確認**: `docker exec kb-neo4j cypher-shell -u neo4j -p <pw> "RETURN 1"` が通るか。
   パスワードは `.env` の `NEO4J_PASSWORD`。落ちていれば `docker compose up -d`
   (Docker Desktop 自体が未起動なら `Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"`
   して engine が応答するまで待つ)。bolt が開くまで数十秒かかる。
2. **健全性検査**: `uv run scripts/kb_check.py` — 結果は severity で分類して報告する:
   - frontmatter / type 欠落 → [DEFECT] (OKF 非準拠。修正する)
   - リンク切れ → 報告のみ (OKF では未執筆知識として許容。ただしタイポ起因でないか確認する)
   - stale_after 超過 → 内容を再検証し、更新するか stale_after を延長するかユーザーに提案
3. **同期**: `uv run scripts/kb_sync.py` — Concept/Tag/Source サブグラフを全再構築 (冪等)。
4. **報告**: 概念数 / リンク数 / ギャップ数 / 検査結果を結論から報告。

## 補足

- グラフの可視化はブラウザで http://localhost:7474 (ユーザー向け案内)。
- グラフスキーマを変えたいときは `scripts/kb_sync.py` を修正して再実行するだけでよい
  (Neo4j 側のデータは使い捨て。設計は `docs/DESIGN.md` D1–D2 参照)。
