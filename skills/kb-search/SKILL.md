---
name: kb-search
description: 個人 knowledge bank (D:\Claude-knowledge-bank) から過去の知見 (開発・投資の両ドメイン) を検索・想起する。ユーザーが「前どうやったっけ」「knowledge bank を調べて」「過去の知見ある？」「この銘柄前に見た？」と言ったとき、または新しいタスク・企業分析の開始時に関連する蓄積知識を確認するときに使う。
---

# kb-search — knowledge bank から想起する

bundle root: `D:\Claude-knowledge-bank\knowledge\` (OKF v0.2 準拠)

## 検索手順 (安い順)

1. **Progressive disclosure**: `knowledge\index.md` → 関連エリアの index.md → 概念ファイル → 本文リンクを辿る。
2. **全文検索**: Grep (path: `D:\Claude-knowledge-bank\knowledge`) でキーワード / `tags:` / `type:` を検索。
3. **グラフ検索** (関連の連鎖・逆参照・ギャップが欲しいとき): Neo4j に Cypher。
   パスワードは `D:\Claude-knowledge-bank\.env` の `NEO4J_PASSWORD`。

   ```
   docker exec kb-neo4j cypher-shell -u neo4j -p <pw> --format plain "<query>"
   ```

   よく使うクエリ:

   ```cypher
   // タグから概念を引く
   MATCH (c:Concept)-[:TAGGED]->(:Tag {name: 'neo4j'}) RETURN c.id, c.description;

   // ある概念の周辺 2 ホップ (関連知識の想起)
   MATCH (c:Concept {id: 'decisions/markdown-sot-neo4j-index'})-[:LINKS_TO*1..2]-(o:Concept)
   WHERE o <> c
   RETURN DISTINCT o.id, o.type, o.description;

   // ある概念を参照している概念 (逆リンク)
   MATCH (o:Concept)-[:LINKS_TO]->(c:Concept {id: 'references/okf-spec'}) RETURN o.id;

   // 未執筆の知識ギャップと、それを欲しがっている概念
   MATCH (g:Concept {missing: true})<-[:LINKS_TO]-(c) RETURN g.id, collect(c.id);

   // ハブ概念 (被リンク数順)
   MATCH (c:Concept)<-[l:LINKS_TO]-() RETURN c.id, count(l) AS refs ORDER BY refs DESC LIMIT 10;
   ```

   Neo4j が落ちていたら手順 1–2 で完結させる (起動待ちでブロックしない)。必要なら /kb-maintain を案内。

## 報告規則

- 見つけた知見は概念ファイルのパス付きで引用する (例: `knowledge/decisions/xxx.md`)。
- `status: deprecated` は「廃止済み」と明示。`stale_after` が過去日なら陳腐化の可能性を注記する。
- 見つからなければそれを明言し、タスク完了後に /kb-save で保存することを提案する。
