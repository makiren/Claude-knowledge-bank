# /// script
# requires-python = ">=3.11"
# dependencies = ["neo4j>=5.20", "pyyaml>=6"]
# ///
"""OKF bundle を Neo4j に同期する。Concept/Tag/Source ラベルのサブグラフを全再構築する (冪等)。"""

import os
import re
import sys
from pathlib import Path

import yaml
from neo4j import GraphDatabase

REPO = Path(__file__).resolve().parent.parent
BUNDLE = REPO / "knowledge"
RESERVED = {"index.md", "log.md"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+?)(?:#[^)]*)?\)")
SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*:")
STRUCTURED_KEYS = {
    "type", "title", "description", "resource", "tags", "status", "stale_after",
    "generated", "verified", "sources", "usage_window", "okf_version",
    "id", "path", "missing",
}


def load_env():
    env = {}
    env_file = REPO / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    return env


def split_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            try:
                fm = yaml.safe_load("\n".join(lines[1:i]))
            except yaml.YAMLError:
                return None, text
            return (fm if isinstance(fm, dict) else {}), "\n".join(lines[i + 1 :])
    return None, text


def resolve_link(target, file_dir):
    """markdown リンク先を Concept ID に解決する。概念ファイル以外 (URL, 画像, 予約名, bundle 外) は None。"""
    if SCHEME_RE.match(target):
        return None
    path = BUNDLE / target.lstrip("/") if target.startswith("/") else file_dir / target
    path = Path(os.path.normpath(path))
    try:
        rel = path.relative_to(BUNDLE).as_posix()
    except ValueError:
        return None
    if not rel.endswith(".md") or Path(rel).name in RESERVED:
        return None
    return rel[:-3]


def collect_concepts():
    concepts = []
    for md in sorted(BUNDLE.rglob("*.md")):
        if md.name in RESERVED:
            continue
        fm, body = split_frontmatter(md.read_text(encoding="utf-8"))
        rel = md.relative_to(BUNDLE).as_posix()
        if fm is None:
            print(f"[WARNING] frontmatter なし (OKF 非準拠): {rel}", file=sys.stderr)
            fm, body = {}, ""
        cid = rel[:-3]
        generated = fm.get("generated") or {}
        links = {resolve_link(m, md.parent) for m in LINK_RE.findall(body)}
        # ticker 等のドメイン固有スカラーキーもプロパティに写す (OKF の producer 拡張キー)
        extra = {
            k: v for k, v in fm.items()
            if k not in STRUCTURED_KEYS and isinstance(v, (str, int, float, bool))
        }
        concepts.append(
            {
                "id": cid,
                "props": extra | {
                    "type": fm.get("type") or "Unknown",
                    "title": fm.get("title") or md.stem,
                    "description": fm.get("description"),
                    "resource": fm.get("resource"),
                    "status": fm.get("status") or "stable",
                    "stale_after": str(fm["stale_after"]) if fm.get("stale_after") else None,
                    "generated_by": generated.get("by"),
                    "generated_at": str(generated["at"]) if generated.get("at") else None,
                    "path": rel,
                },
                "tags": [str(t) for t in fm.get("tags") or []],
                "links": sorted(t for t in links if t and t != cid),
                "sources": [s for s in fm.get("sources") or [] if isinstance(s, dict) and s.get("resource")],
            }
        )
    return concepts


def sync(concepts):
    env = load_env()
    uri = os.environ.get("NEO4J_URI", env.get("NEO4J_URI", "bolt://localhost:7687"))
    user = os.environ.get("NEO4J_USER", env.get("NEO4J_USER", "neo4j"))
    password = os.environ.get("NEO4J_PASSWORD", env.get("NEO4J_PASSWORD", ""))
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as s:
        for stmt in (
            "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT tag_name IF NOT EXISTS FOR (t:Tag) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT source_resource IF NOT EXISTS FOR (s:Source) REQUIRE s.resource IS UNIQUE",
        ):
            s.run(stmt)
        s.run("MATCH (n) WHERE n:Concept OR n:Tag OR n:Source DETACH DELETE n")
        for c in concepts:
            s.run(
                "MERGE (c:Concept {id: $id}) SET c += $props, c.missing = false",
                id=c["id"],
                props={k: v for k, v in c["props"].items() if v is not None},
            )
        for c in concepts:
            for tag in c["tags"]:
                s.run(
                    "MATCH (c:Concept {id: $id}) MERGE (t:Tag {name: $tag}) MERGE (c)-[:TAGGED]->(t)",
                    id=c["id"], tag=tag,
                )
            for target in c["links"]:
                s.run(
                    "MATCH (c:Concept {id: $id}) "
                    "MERGE (o:Concept {id: $target}) ON CREATE SET o.missing = true, o.title = $target "
                    "MERGE (c)-[:LINKS_TO]->(o)",
                    id=c["id"], target=target,
                )
            for src in c["sources"]:
                s.run(
                    "MATCH (c:Concept {id: $id}) MERGE (s:Source {resource: $resource}) "
                    "SET s.title = coalesce($title, s.title), s.author = coalesce($author, s.author) "
                    "MERGE (c)-[:DERIVED_FROM]->(s)",
                    id=c["id"], resource=str(src["resource"]),
                    title=src.get("title"), author=src.get("author"),
                )
        counts = s.run(
            "RETURN count { (:Concept) } AS concepts, count { (:Concept {missing: true}) } AS gaps, "
            "count { ()-[:LINKS_TO]->() } AS links, count { (:Tag) } AS tags, count { (:Source) } AS sources"
        ).single()
    driver.close()
    return counts


def main():
    concepts = collect_concepts()
    print(f"bundle: {BUNDLE}  concepts: {len(concepts)}")
    c = sync(concepts)
    print(
        f"Neo4j: Concept={c['concepts']} (gap={c['gaps']}) LINKS_TO={c['links']} "
        f"Tag={c['tags']} Source={c['sources']}"
    )


if __name__ == "__main__":
    main()
