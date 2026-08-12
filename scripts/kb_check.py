# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""OKF bundle の健全性検査: 準拠性 / リンク切れ / staleness を報告する。

kb_sync.py と数関数が重複しているのは意図的 (uv script は環境が分離され、
import 共有すると本スクリプトにも neo4j driver が必要になるため)。
"""

import datetime
import os
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
BUNDLE = REPO / "knowledge"
RESERVED = {"index.md", "log.md"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+?)(?:#[^)]*)?\)")
SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*:")


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
    return rel


def main():
    errors, gaps, stale, drafts = [], [], [], []
    today = datetime.date.today()
    concept_count = 0
    for md in sorted(BUNDLE.rglob("*.md")):
        if md.name in RESERVED:
            continue
        concept_count += 1
        rel = md.relative_to(BUNDLE).as_posix()
        fm, body = split_frontmatter(md.read_text(encoding="utf-8"))
        if fm is None:
            errors.append(f"{rel}: frontmatter が無い、または YAML として不正")
            continue
        if not fm.get("type"):
            errors.append(f"{rel}: 必須フィールド type が無い")
        if fm.get("status") == "draft":
            drafts.append(rel)
        stale_after = fm.get("stale_after")
        if stale_after:
            try:
                if isinstance(stale_after, str):
                    stale_after = datetime.date.fromisoformat(stale_after)
                if today >= stale_after:
                    stale.append(f"{rel}: stale_after={stale_after}")
            except ValueError:
                errors.append(f"{rel}: stale_after が YYYY-MM-DD でない: {stale_after!r}")
        for m in LINK_RE.findall(body):
            target = resolve_link(m, md.parent)
            if target and not (BUNDLE / target).exists():
                gaps.append(f"{rel} -> /{target}")

    print(f"concepts: {concept_count}")
    if errors:
        print(f"\n[DEFECT] OKF 非準拠 ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    if stale:
        print(f"\nstale (stale_after 超過, 要再検証) ({len(stale)}):")
        for s in stale:
            print(f"  - {s}")
    if gaps:
        print(f"\n未執筆の知識 (リンク先が存在しない。OKF では許容) ({len(gaps)}):")
        for g in gaps:
            print(f"  - {g}")
    if drafts:
        print(f"\ndraft ({len(drafts)}): " + ", ".join(drafts))
    if not (errors or stale or gaps or drafts):
        print("問題なし")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
