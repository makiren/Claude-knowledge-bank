# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""OKF bundle を自己完結のインタラクティブ HTML グラフ (kb_graph.html) に描き出す。

Neo4j 不要・ブラウザで開くだけ。knowledge/ の内容を埋め込むため出力は gitignore 対象。
パース関数は kb_sync.py と重複させている (uv の script 単位環境分離のため import 共有しない)。
"""

import datetime
import json
import os
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
BUNDLE = REPO / "knowledge"
OUT = REPO / "kb_graph.html"
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
    return rel[:-3]


def collect():
    nodes, edges = {}, []
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
        nodes[cid] = {
            "id": cid,
            "dir": cid.split("/")[0] if "/" in cid else "",
            "type": fm.get("type") or "Unknown",
            "title": fm.get("title") or md.stem,
            "description": fm.get("description") or "",
            "status": fm.get("status") or "stable",
            "stale_after": str(fm["stale_after"]) if fm.get("stale_after") else None,
            "generated_at": str(generated["at"]) if generated.get("at") else None,
            "tags": [str(t) for t in fm.get("tags") or []],
            "sources": [
                {"resource": str(s["resource"]), "title": s.get("title")}
                for s in fm.get("sources") or []
                if isinstance(s, dict) and s.get("resource")
            ],
            "ticker": fm.get("ticker"),
            "missing": False,
        }
        for target in sorted(t for t in links if t and t != cid):
            edges.append({"source": cid, "target": target})
    for e in edges:
        t = e["target"]
        if t not in nodes:
            nodes[t] = {
                "id": t, "dir": t.split("/")[0] if "/" in t else "",
                "type": "Gap", "title": t.rsplit("/", 1)[-1], "description": "",
                "status": None, "stale_after": None, "generated_at": None,
                "tags": [], "sources": [], "ticker": None, "missing": True,
            }
    return list(nodes.values()), edges


def main():
    nodes, edges = collect()
    now = datetime.datetime.now().astimezone()
    data = json.dumps(
        {"nodes": nodes, "edges": edges, "today": now.date().isoformat(),
         "generated": now.strftime("%Y-%m-%d %H:%M")},
        ensure_ascii=False,
    ).replace("</", "<\\/")
    OUT.write_text(TEMPLATE.replace("__DATA__", data), encoding="utf-8")
    gaps = sum(1 for n in nodes if n["missing"])
    print(f"{OUT}  concepts={len(nodes) - gaps} gaps={gaps} links={len(edges)}")


TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Knowledge Bank Graph</title>
<style>
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb;
  --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --border: rgba(11,11,11,0.10);
  --warning: #fab219;
  --c-projects: #2a78d6; --c-decisions: #eb6834; --c-patterns: #1baf7a;
  --c-troubleshooting: #eda100; --c-references: #e87ba4; --c-companies: #008300;
  --c-analyses: #4a3aa7; --c-other: #898781;
}
@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19;
    --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --border: rgba(255,255,255,0.10);
    --c-projects: #3987e5; --c-decisions: #d95926; --c-patterns: #199e70;
    --c-troubleshooting: #c98500; --c-references: #d55181; --c-companies: #008300;
    --c-analyses: #9085e9;
  }
}
* { margin: 0; box-sizing: border-box; }
body {
  background: var(--page); color: var(--ink);
  font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
  height: 100vh; display: flex; flex-direction: column; overflow: hidden;
}
header { padding: 14px 20px 10px; display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap; }
header h1 { font-size: 17px; font-weight: 650; }
header .meta { color: var(--muted); font-size: 12px; }
.stats { display: flex; gap: 8px; padding: 0 20px 10px; flex-wrap: wrap; }
.stat {
  background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
  padding: 6px 14px; min-width: 86px;
}
.stat b { display: block; font-size: 20px; font-weight: 650; font-variant-numeric: tabular-nums; }
.stat span { font-size: 11px; color: var(--ink-2); }
.filters { display: flex; gap: 8px; padding: 0 20px 10px; align-items: center; flex-wrap: wrap; }
.filters input[type=search] {
  background: var(--surface); border: 1px solid var(--grid); border-radius: 8px;
  color: var(--ink); padding: 6px 12px; width: 220px; font: inherit; font-size: 13px;
}
.chip {
  display: inline-flex; align-items: center; gap: 6px; cursor: pointer; user-select: none;
  background: var(--surface); border: 1px solid var(--grid); border-radius: 999px;
  padding: 4px 12px; font-size: 12px; color: var(--ink-2);
}
.chip .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--c); }
.chip.gap .dot { background: transparent; border: 1.5px dashed var(--muted); }
.chip.off { opacity: 0.38; }
.chip.off .dot { background: var(--muted); }
#view-graph { margin-left: auto; }
.chip.view.on { border-color: var(--ink-2); color: var(--ink); font-weight: 600; }
main { flex: 1; position: relative; min-height: 0; }
svg#graph { width: 100%; height: 100%; display: block; background: var(--surface); border-top: 1px solid var(--grid); cursor: grab; }
svg#graph.panning { cursor: grabbing; }
.edge { stroke: var(--grid); stroke-width: 1.2; fill: none; }
.edge.hl { stroke: var(--ink-2); }
.edge.dim { opacity: 0.25; }
.node { cursor: pointer; }
.node circle { stroke: var(--surface); stroke-width: 2; }
.node.missing circle { fill: var(--surface); stroke: var(--muted); stroke-dasharray: 3 3; stroke-width: 1.5; }
.node .stale-ring { fill: none; stroke: var(--warning); stroke-width: 2; stroke-dasharray: 2 3; }
.node text {
  font-size: 11px; fill: var(--ink-2); paint-order: stroke;
  stroke: var(--surface); stroke-width: 3px; stroke-linejoin: round; pointer-events: none;
}
.node.missing text { fill: var(--muted); font-style: italic; }
.node.selected circle { stroke: var(--ink); stroke-width: 2.5; }
.node.selected text, .node.hl text { fill: var(--ink); font-weight: 600; }
.node.dim { opacity: 0.22; }
#tooltip {
  position: absolute; pointer-events: none; display: none; max-width: 300px; z-index: 5;
  background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
  padding: 8px 12px; font-size: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.18);
}
#tooltip b { font-size: 13px; }
#tooltip .type { color: var(--ink-2); }
#tooltip .desc { color: var(--ink-2); margin-top: 3px; }
#panel {
  position: absolute; top: 12px; right: 12px; bottom: 12px; width: 320px; z-index: 4;
  background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
  padding: 16px; overflow-y: auto; display: none; box-shadow: 0 6px 24px rgba(0,0,0,0.15);
}
#panel.open { display: block; }
#panel .close { float: right; cursor: pointer; color: var(--muted); font-size: 16px; border: 0; background: none; padding: 0 2px; }
#panel h2 { font-size: 15px; margin-bottom: 2px; padding-right: 20px; }
#panel .id { font-size: 11px; color: var(--muted); word-break: break-all; }
#panel .badges { margin: 8px 0; display: flex; gap: 6px; flex-wrap: wrap; }
.badge {
  font-size: 11px; padding: 2px 9px; border-radius: 999px;
  border: 1px solid var(--grid); color: var(--ink-2);
}
.badge.type { border-color: transparent; color: #fff; background: var(--c); }
.badge.stale { border-color: var(--warning); color: var(--ink); }
#panel .desc { font-size: 13px; color: var(--ink-2); margin: 8px 0; }
#panel dl { font-size: 12px; margin: 10px 0; }
#panel dt { color: var(--muted); margin-top: 7px; }
#panel dd { margin: 1px 0 0; }
#panel a { color: var(--c-projects); text-decoration: none; word-break: break-all; }
#panel a:hover { text-decoration: underline; }
#panel .link-item { display: block; cursor: pointer; padding: 2px 0; }
.tag { font-size: 11px; background: var(--page); border: 1px solid var(--grid); border-radius: 4px; padding: 1px 6px; margin: 0 4px 4px 0; display: inline-block; }
#table-wrap { position: absolute; inset: 0; overflow: auto; background: var(--surface); border-top: 1px solid var(--grid); display: none; padding: 0 20px 20px; }
#table-wrap.on { display: block; }
table { border-collapse: collapse; width: 100%; font-size: 13px; margin-top: 12px; }
th { text-align: left; color: var(--muted); font-size: 11px; font-weight: 600; padding: 6px 12px 6px 0; border-bottom: 1px solid var(--grid); position: sticky; top: 0; background: var(--surface); }
td { padding: 7px 12px 7px 0; border-bottom: 1px solid var(--grid); vertical-align: top; }
td.title { cursor: pointer; font-weight: 550; white-space: nowrap; }
td.title .dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: var(--c); margin-right: 7px; }
td .muted { color: var(--muted); }
td.desc { color: var(--ink-2); max-width: 480px; }
.hidden { display: none !important; }
</style>
</head>
<body>
<header>
  <h1>Knowledge Bank Graph</h1>
  <span class="meta">OKF bundle: knowledge/ — 生成 <span id="gen-at"></span></span>
</header>
<div class="stats" id="stats"></div>
<div class="filters">
  <input type="search" id="search" placeholder="タイトル・タグ・説明で検索…">
  <span id="chips"></span>
  <span class="chip view on" id="view-graph">グラフ</span>
  <span class="chip view" id="view-table">一覧</span>
</div>
<main>
  <svg id="graph"><defs>
    <marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0.5 L7.5,4 L0,7.5" fill="none" stroke="var(--grid)" stroke-width="1.4"/>
    </marker>
  </defs><g id="zoom-layer"><g id="edges"></g><g id="nodes"></g></g></svg>
  <div id="table-wrap"><table>
    <thead><tr><th>概念</th><th>type</th><th>説明</th><th>タグ</th><th>状態</th></tr></thead>
    <tbody id="tbody"></tbody>
  </table></div>
  <div id="tooltip"></div>
  <div id="panel"></div>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const DIRS = {
  projects: 'プロジェクト', decisions: '設計判断', patterns: 'パターン',
  troubleshooting: 'トラブルシュート', references: 'リファレンス',
  companies: '企業', analyses: '分析',
};
const dirVar = d => DIRS[d] ? `--c-${d}` : '--c-other';
const dirLabel = d => DIRS[d] || 'その他';
const today = DATA.today;
const isStale = n => n.stale_after && n.stale_after < today;

const nodes = DATA.nodes.map(n => ({...n, x: 0, y: 0, vx: 0, vy: 0, deg: 0}));
const byId = new Map(nodes.map(n => [n.id, n]));
const edges = DATA.edges.map(e => ({s: byId.get(e.source), t: byId.get(e.target)}));
edges.forEach(e => { e.s.deg++; e.t.deg++; });
nodes.forEach(n => { n.r = n.missing ? 6 : 7 + Math.sqrt(n.deg) * 3.2; });

// 初期配置: ディレクトリごとに円環上へ (収束を速く・群を作りやすく)
const dirKeys = [...new Set(nodes.map(n => n.dir))];
nodes.forEach((n, i) => {
  const a = (dirKeys.indexOf(n.dir) / dirKeys.length) * Math.PI * 2;
  n.x = Math.cos(a) * 220 + (i % 7) * 14 - 42;
  n.y = Math.sin(a) * 220 + Math.floor(i / 7) * 14 - 42;
});

document.getElementById('gen-at').textContent = DATA.generated;

const nReal = nodes.filter(n => !n.missing).length;
const nStale = nodes.filter(isStale).length;
const allTags = new Set(nodes.flatMap(n => n.tags));
document.getElementById('stats').innerHTML = [
  [nReal, '概念'], [edges.length, 'リンク'],
  [nodes.length - nReal, '未執筆 (gap)'], [nStale, 'stale'], [allTags.size, 'タグ'],
].map(([v, l]) => `<div class="stat"><b>${v}</b><span>${l}</span></div>`).join('');

// ---- filter chips ----
const activeDirs = new Set(dirKeys);
let showGaps = true;
const chipsEl = document.getElementById('chips');
chipsEl.innerHTML = dirKeys.filter(d => DIRS[d]).map(d =>
  `<span class="chip" data-dir="${d}" style="--c: var(${dirVar(d)})"><span class="dot"></span>${dirLabel(d)}</span>`
).join('') + `<span class="chip gap" data-gap><span class="dot"></span>未執筆</span>`;
chipsEl.addEventListener('click', ev => {
  const chip = ev.target.closest('.chip');
  if (!chip) return;
  chip.classList.toggle('off');
  if ('gap' in chip.dataset) showGaps = !chip.classList.contains('off');
  else {
    const d = chip.dataset.dir;
    chip.classList.contains('off') ? activeDirs.delete(d) : activeDirs.add(d);
  }
  applyFilter();
});

let query = '';
document.getElementById('search').addEventListener('input', ev => {
  query = ev.target.value.trim().toLowerCase();
  applyFilter();
});

const matches = n => {
  if (n.missing && !showGaps) return false;
  if (!activeDirs.has(n.dir)) return false;
  if (!query) return true;
  return (n.title + ' ' + n.description + ' ' + n.tags.join(' ') + ' ' + n.id + ' ' + (n.ticker || ''))
    .toLowerCase().includes(query);
};

function applyFilter() {
  nodes.forEach(n => { n.visible = matches(n); });
  nodes.forEach(n => n.el.classList.toggle('hidden', !n.visible));
  edges.forEach(e => e.el.classList.toggle('hidden', !(e.s.visible && e.t.visible)));
  document.querySelectorAll('#tbody tr').forEach(tr =>
    tr.classList.toggle('hidden', !byId.get(tr.dataset.id).visible));
  reheat(0.4);
}

// ---- SVG build ----
const svg = document.getElementById('graph');
const zoomLayer = document.getElementById('zoom-layer');
const edgesG = document.getElementById('edges');
const nodesG = document.getElementById('nodes');
const NS = 'http://www.w3.org/2000/svg';

edges.forEach(e => {
  const el = document.createElementNS(NS, 'line');
  el.setAttribute('class', 'edge');
  el.setAttribute('marker-end', 'url(#arrow)');
  edgesG.appendChild(el);
  e.el = el;
});
nodes.forEach(n => {
  const g = document.createElementNS(NS, 'g');
  g.setAttribute('class', 'node' + (n.missing ? ' missing' : ''));
  const c = document.createElementNS(NS, 'circle');
  c.setAttribute('r', n.r);
  if (!n.missing) c.setAttribute('fill', `var(${dirVar(n.dir)})`);
  g.appendChild(c);
  if (isStale(n)) {
    const ring = document.createElementNS(NS, 'circle');
    ring.setAttribute('class', 'stale-ring');
    ring.setAttribute('r', n.r + 4);
    g.appendChild(ring);
  }
  const label = document.createElementNS(NS, 'text');
  label.setAttribute('y', n.r + 13);
  label.setAttribute('text-anchor', 'middle');
  label.textContent = n.title.length > 22 ? n.title.slice(0, 21) + '…' : n.title;
  g.appendChild(label);
  nodesG.appendChild(g);
  n.el = g;
});

// ---- force simulation ----
let alpha = 1;
const reheat = a => { alpha = Math.max(alpha, a); };
function tick() {
  if (alpha > 0.005) {
    const vis = nodes.filter(n => n.visible !== false);
    for (let i = 0; i < vis.length; i++) for (let j = i + 1; j < vis.length; j++) {
      const a = vis[i], b = vis[j];
      let dx = b.x - a.x, dy = b.y - a.y;
      let d2 = dx * dx + dy * dy;
      if (d2 < 1) { dx = (Math.random() - 0.5); dy = (Math.random() - 0.5); d2 = 1; }
      const f = Math.min(3400 / d2, 6) * alpha;
      const d = Math.sqrt(d2), fx = dx / d * f, fy = dy / d * f;
      if (!a.fixed) { a.vx -= fx; a.vy -= fy; }
      if (!b.fixed) { b.vx += fx; b.vy += fy; }
    }
    edges.forEach(e => {
      if (e.s.visible === false || e.t.visible === false) return;
      const dx = e.t.x - e.s.x, dy = e.t.y - e.s.y;
      const d = Math.sqrt(dx * dx + dy * dy) || 1;
      const f = (d - 150) * 0.02 * alpha;
      const fx = dx / d * f, fy = dy / d * f;
      if (!e.s.fixed) { e.s.vx += fx; e.s.vy += fy; }
      if (!e.t.fixed) { e.t.vx -= fx; e.t.vy -= fy; }
    });
    vis.forEach(n => {
      if (n.fixed) return;
      n.vx -= n.x * 0.004 * alpha; n.vy -= n.y * 0.004 * alpha;
      n.vx *= 0.82; n.vy *= 0.82;
      n.x += n.vx; n.y += n.vy;
    });
    alpha *= 0.985;
    render();
  }
  requestAnimationFrame(tick);
}
function render() {
  edges.forEach(e => {
    // 矢印がノード円周で止まるよう終端を半径分手前に
    const dx = e.t.x - e.s.x, dy = e.t.y - e.s.y;
    const d = Math.sqrt(dx * dx + dy * dy) || 1;
    const pad = e.t.r + 3;
    e.el.setAttribute('x1', e.s.x); e.el.setAttribute('y1', e.s.y);
    e.el.setAttribute('x2', e.t.x - dx / d * pad); e.el.setAttribute('y2', e.t.y - dy / d * pad);
  });
  nodes.forEach(n => n.el.setAttribute('transform', `translate(${n.x},${n.y})`));
}

// ---- pan / zoom ----
let view = {x: 0, y: 0, k: 1};
function applyView() {
  const {width, height} = svg.getBoundingClientRect();
  zoomLayer.setAttribute('transform',
    `translate(${width / 2 + view.x},${height / 2 + view.y}) scale(${view.k})`);
}
new ResizeObserver(applyView).observe(svg);
svg.addEventListener('wheel', ev => {
  ev.preventDefault();
  const k2 = Math.min(4, Math.max(0.25, view.k * (ev.deltaY < 0 ? 1.15 : 0.87)));
  const rect = svg.getBoundingClientRect();
  const mx = ev.clientX - rect.left - rect.width / 2 - view.x;
  const my = ev.clientY - rect.top - rect.height / 2 - view.y;
  view.x -= mx * (k2 / view.k - 1); view.y -= my * (k2 / view.k - 1);
  view.k = k2;
  applyView();
}, {passive: false});

let drag = null;
const toGraph = ev => {
  const rect = svg.getBoundingClientRect();
  return [(ev.clientX - rect.left - rect.width / 2 - view.x) / view.k,
          (ev.clientY - rect.top - rect.height / 2 - view.y) / view.k];
};
svg.addEventListener('pointerdown', ev => {
  const g = ev.target.closest('.node');
  svg.setPointerCapture(ev.pointerId);
  if (g) {
    const n = nodes.find(n => n.el === g);
    drag = {node: n, moved: false, x0: ev.clientX, y0: ev.clientY};
    n.fixed = true;
  } else {
    drag = {pan: [ev.clientX - view.x, ev.clientY - view.y], moved: false, x0: ev.clientX, y0: ev.clientY};
    svg.classList.add('panning');
  }
});
svg.addEventListener('pointermove', ev => {
  if (!drag) { hover(ev); return; }
  if (Math.abs(ev.clientX - drag.x0) + Math.abs(ev.clientY - drag.y0) < 4 && !drag.moved) return;
  drag.moved = true;
  if (drag.node) {
    [drag.node.x, drag.node.y] = toGraph(ev);
    reheat(0.3);
    render();
  } else {
    view.x = ev.clientX - drag.pan[0]; view.y = ev.clientY - drag.pan[1];
    applyView();
  }
});
svg.addEventListener('pointerup', ev => {
  svg.classList.remove('panning');
  if (drag && drag.node) {
    drag.node.fixed = false;
    if (!drag.moved) select(drag.node);
  } else if (drag && !drag.moved) {
    select(null);
  }
  drag = null;
});

// ---- hover tooltip + neighborhood highlight ----
const tooltip = document.getElementById('tooltip');
let hovered = null;
function hover(ev) {
  const g = ev.target.closest('.node');
  const n = g ? nodes.find(n => n.el === g) : null;
  if (n !== hovered) { hovered = n; highlight(); }
  if (!n) { tooltip.style.display = 'none'; return; }
  tooltip.innerHTML = n.missing
    ? `<b>${esc(n.title)}</b> <span class="type">未執筆 (リンクのみ存在)</span>`
    : `<b>${esc(n.title)}</b> <span class="type">${esc(n.type)}${isStale(n) ? ' · ⚠ stale' : ''}</span>` +
      (n.description ? `<div class="desc">${esc(n.description)}</div>` : '');
  tooltip.style.display = 'block';
  const rect = svg.getBoundingClientRect();
  tooltip.style.left = Math.min(ev.clientX - rect.left + 14, rect.width - 310) + 'px';
  tooltip.style.top = (ev.clientY - rect.top + 14) + 'px';
}
function highlight() {
  const focus = hovered || selected;
  if (!focus) {
    nodes.forEach(n => n.el.classList.remove('dim', 'hl'));
    edges.forEach(e => e.el.classList.remove('dim', 'hl'));
    return;
  }
  const near = new Set([focus]);
  edges.forEach(e => {
    if (e.s === focus) near.add(e.t);
    if (e.t === focus) near.add(e.s);
  });
  nodes.forEach(n => {
    n.el.classList.toggle('dim', !near.has(n));
    n.el.classList.toggle('hl', near.has(n));
  });
  edges.forEach(e => {
    const on = e.s === focus || e.t === focus;
    e.el.classList.toggle('hl', on);
    e.el.classList.toggle('dim', !on);
  });
}

// ---- selection + detail panel ----
const panel = document.getElementById('panel');
let selected = null;
function select(n) {
  selected = n;
  nodes.forEach(m => m.el.classList.toggle('selected', m === n));
  highlight();
  if (!n) { panel.classList.remove('open'); return; }
  const outL = edges.filter(e => e.s === n).map(e => e.t);
  const inL = edges.filter(e => e.t === n).map(e => e.s);
  const linkList = (arr) => arr.map(m =>
    `<span class="link-item" data-id="${esc(m.id)}">→ ${esc(m.title)}${m.missing ? ' <span class="muted">(未執筆)</span>' : ''}</span>`
  ).join('') || '<span class="muted">なし</span>';
  panel.innerHTML = `
    <button class="close" title="閉じる">✕</button>
    <h2>${esc(n.title)}</h2>
    <div class="id">${esc(n.id)}.md</div>
    <div class="badges">
      ${n.missing
        ? '<span class="badge">未執筆 (gap)</span>'
        : `<span class="badge type" style="--c: var(${dirVar(n.dir)})">${esc(n.type)}</span><span class="badge">${esc(n.status)}</span>`}
      ${isStale(n) ? `<span class="badge stale">⚠ stale (${esc(n.stale_after)} 期限切れ)</span>`
        : n.stale_after ? `<span class="badge">stale_after ${esc(n.stale_after)}</span>` : ''}
      ${n.ticker ? `<span class="badge">${esc(String(n.ticker))}</span>` : ''}
    </div>
    ${n.description ? `<div class="desc">${esc(n.description)}</div>` : ''}
    ${n.missing ? '<div class="desc">リンク先の概念がまだ書かれていません。知識ギャップ (OKF: not-yet-written knowledge)。</div>' : ''}
    <dl>
      ${n.tags.length ? `<dt>タグ</dt><dd>${n.tags.map(t => `<span class="tag">${esc(t)}</span>`).join('')}</dd>` : ''}
      <dt>リンク先 (${outL.length})</dt><dd>${linkList(outL)}</dd>
      <dt>被リンク (${inL.length})</dt><dd>${linkList(inL)}</dd>
      ${n.sources.length ? `<dt>sources</dt><dd>${n.sources.map(s =>
        `<a href="${esc(s.resource)}" target="_blank" rel="noopener">${esc(s.title || s.resource)}</a>`).join('<br>')}</dd>` : ''}
      ${n.generated_at ? `<dt>generated</dt><dd>${esc(n.generated_at)}</dd>` : ''}
    </dl>`;
  panel.classList.add('open');
}
panel.addEventListener('click', ev => {
  if (ev.target.closest('.close')) { select(null); return; }
  const li = ev.target.closest('.link-item');
  if (li) {
    const n = byId.get(li.dataset.id);
    showView('graph');
    select(n);
    view.x = -n.x * view.k; view.y = -n.y * view.k;
    applyView();
  }
});

// ---- table view (アクセシビリティ: 色に依らない一覧) ----
const tbody = document.getElementById('tbody');
tbody.innerHTML = [...nodes].sort((a, b) => a.id.localeCompare(b.id)).map(n => `
  <tr data-id="${esc(n.id)}">
    <td class="title"><span class="dot" style="--c: var(${dirVar(n.dir)}); ${n.missing ? 'background: transparent; border: 1.5px dashed var(--muted);' : ''}"></span>${esc(n.title)}</td>
    <td>${n.missing ? '<span class="muted">未執筆</span>' : esc(n.type)}</td>
    <td class="desc">${esc(n.description)}</td>
    <td>${n.tags.map(t => `<span class="tag">${esc(t)}</span>`).join('')}</td>
    <td>${n.missing ? '—' : esc(n.status)}${isStale(n) ? ' <b>⚠ stale</b>' : ''}</td>
  </tr>`).join('');
tbody.addEventListener('click', ev => {
  const tr = ev.target.closest('tr');
  if (!tr) return;
  showView('graph');
  document.getElementById('view-graph').classList.add('on');
  document.getElementById('view-table').classList.remove('on');
  select(byId.get(tr.dataset.id));
});

function showView(v) {
  document.getElementById('table-wrap').classList.toggle('on', v === 'table');
  document.getElementById('view-graph').classList.toggle('on', v === 'graph');
  document.getElementById('view-table').classList.toggle('on', v === 'table');
}
document.getElementById('view-graph').addEventListener('click', () => showView('graph'));
document.getElementById('view-table').addEventListener('click', () => showView('table'));

function esc(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}

nodes.forEach(n => { n.visible = true; });
applyView();
tick();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
