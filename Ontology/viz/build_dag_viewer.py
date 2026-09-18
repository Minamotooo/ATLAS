"""
build_dag_viewer.py
-------------------
Generate a standalone, interactive HTML viewer for an ATLAS skill ontology.

Reads the JSON pair that every ontology in this repo is defined by:

    <source-dir>/tuples.json    [ {bloom, skillId, skillFull, topicKey, topicLabel, subject}, ... ]
    <source-dir>/prereqs.json   { dependentSkillId: [ {id, full, depth}, ... ], ... }

and writes one self-contained HTML file.

Usage
-----
    # the full-corpus rebuild (Chemistry only, 843 skills)
    python Ontology/viz/build_dag_viewer.py \
        --source-dir Ontology/full_corpus_rebuild \
        --subject Chemistry \
        --out Ontology/viz/chemistry_rebuild.html \
        --title "Chemistry Skill Ontology - Full-Corpus Rebuild"

    # the legacy ontology the live app runs on, Chemistry slice (117 skills)
    python Ontology/viz/build_dag_viewer.py \
        --source-dir Ontology \
        --subject Chemistry \
        --out Ontology/viz/chemistry_legacy.html \
        --title "Chemistry Skill Ontology - Legacy (live)"

    # no --subject: every subject in the source
    python Ontology/viz/build_dag_viewer.py --source-dir Ontology --out Ontology/viz/all_legacy.html

WHY THE OUTPUT IS NEVER NAMED skill_ontology_dag.html
-----------------------------------------------------
`Backend/tree_data/build_from_ontology.py::load_source()` treats a file named
exactly `skill_ontology_dag.html` inside its `--source-dir` as the *authoritative*
ontology source, preferring it over tuples.json/prereqs.json. Dropping a generated
viewer under that name into `Ontology/full_corpus_rebuild/` would silently change
what the documented validation command in that directory's STATUS.md reads. So:

  * output goes to Ontology/viz/, which is never passed as a --source-dir, and
  * the generated file is never named skill_ontology_dag.html.

This script only ever READS its source directory. It never writes there.

Encoding decisions (see Ontology/viz/README.md for the rationale)
-----------------------------------------------------------------
  colour  : structural role - root / intermediate / leaf / isolated
  size    : degree (prerequisite + dependent count)
  Bloom   : text badge + filter, not colour (6 ordered levels do not fit the
            validated 5-step ordinal ramp)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


# --------------------------------------------------------------------------- load

def load_ontology(source_dir: Path, subject: str | None) -> dict:
    """Read tuples.json + prereqs.json, filter to `subject`, derive graph facts."""
    tuples_path = source_dir / "tuples.json"
    prereqs_path = source_dir / "prereqs.json"

    if not tuples_path.is_file():
        sys.exit(f"error: {tuples_path} not found")
    if not prereqs_path.is_file():
        sys.exit(f"error: {prereqs_path} not found")

    tuples = json.loads(tuples_path.read_text(encoding="utf-8"))
    prereqs = json.loads(prereqs_path.read_text(encoding="utf-8"))

    if subject:
        tuples = [t for t in tuples if t.get("subject") == subject]
        if not tuples:
            sys.exit(f"error: no skills with subject={subject!r} in {tuples_path}")

    skills = {}
    for t in tuples:
        sid = t.get("skillId")
        if not sid or sid in skills:
            continue
        skills[sid] = {
            "id": sid,
            "full": t.get("skillFull", ""),
            "bloom": t.get("bloom", ""),
            "topic": t.get("topicKey", "UNASSIGNED"),
            "topicLabel": t.get("topicLabel", t.get("topicKey", "Unassigned")),
            "subject": t.get("subject", ""),
        }

    # prereqs.json maps dependent -> [ancestors]; an edge runs ancestor -> dependent.
    # Keep only edges whose BOTH ends survived the subject filter, and record the
    # ones that did not so the viewer can report them honestly.
    edges, dropped = [], 0
    seen_edges = set()
    for dependent, ancestors in prereqs.items():
        for anc in ancestors or []:
            src = anc.get("id") if isinstance(anc, dict) else None
            if not src:
                continue
            if src in skills and dependent in skills:
                key = (src, dependent)
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append({"source": src, "target": dependent})
            else:
                dropped += 1

    indeg = defaultdict(int)   # number of prerequisites a skill has
    outdeg = defaultdict(int)  # number of skills that depend on it
    for e in edges:
        outdeg[e["source"]] += 1
        indeg[e["target"]] += 1

    for sid, s in skills.items():
        has_prereq, has_dependent = indeg[sid] > 0, outdeg[sid] > 0
        if has_prereq and has_dependent:
            role = "intermediate"
        elif has_dependent:
            role = "root"
        elif has_prereq:
            role = "leaf"
        else:
            role = "isolated"
        s["role"] = role
        s["prereqCount"] = indeg[sid]
        s["dependentCount"] = outdeg[sid]
        s["degree"] = indeg[sid] + outdeg[sid]

    # Topic rollup + aggregated cross-topic prerequisite edges.
    topics = {}
    for s in skills.values():
        tk = s["topic"]
        t = topics.setdefault(tk, {
            "key": tk, "label": s["topicLabel"], "subject": s["subject"],
            "count": 0, "connected": 0, "blooms": defaultdict(int),
        })
        t["count"] += 1
        if s["role"] != "isolated":
            t["connected"] += 1
        t["blooms"][s["bloom"] or "Unspecified"] += 1

    topic_pairs = defaultdict(int)
    for e in edges:
        a, b = skills[e["source"]]["topic"], skills[e["target"]]["topic"]
        if a != b:
            topic_pairs[(a, b)] += 1

    topic_list = sorted(topics.values(), key=lambda t: (-t["count"], t["key"]))
    for t in topic_list:
        t["blooms"] = dict(t["blooms"])

    # Weakly-connected components, ignoring isolated nodes.
    adj = defaultdict(set)
    for e in edges:
        adj[e["source"]].add(e["target"])
        adj[e["target"]].add(e["source"])
    comp_of, comps, seen = {}, [], set()
    for sid in skills:
        if sid in seen or skills[sid]["role"] == "isolated":
            continue
        stack, comp = [sid], []
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            comp.append(cur)
            stack.extend(adj[cur] - seen)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    for i, comp in enumerate(comps):
        for sid in comp:
            comp_of[sid] = i
    for sid, s in skills.items():
        s["component"] = comp_of.get(sid, -1)

    bloom_counts = defaultdict(int)
    for s in skills.values():
        bloom_counts[s["bloom"] or "Unspecified"] += 1
    role_counts = defaultdict(int)
    for s in skills.values():
        role_counts[s["role"]] += 1

    isolated = role_counts.get("isolated", 0)
    return {
        "nodes": sorted(skills.values(), key=lambda s: s["id"]),
        "edges": edges,
        "topics": topic_list,
        "topicEdges": [{"source": a, "target": b, "weight": w}
                       for (a, b), w in sorted(topic_pairs.items(), key=lambda kv: -kv[1])],
        "stats": {
            "skills": len(skills),
            "edges": len(edges),
            "topics": len(topic_list),
            "isolated": isolated,
            "isolatedPct": round(100.0 * isolated / len(skills), 1) if skills else 0.0,
            "components": len(comps),
            "largestComponent": len(comps[0]) if comps else 0,
            "droppedEdgeRefs": dropped,
            "blooms": dict(bloom_counts),
            "roles": dict(role_counts),
        },
    }


# --------------------------------------------------------------------------- template

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<style>
:root{
  color-scheme: light;
  --surface-0:#f4f4f2; --surface-1:#fcfcfb; --surface-2:#eceae5;
  --border:#d9d7d0; --border-strong:#b9b7ae;
  --text-primary:#0b0b0b; --text-secondary:#52514e; --text-muted:#7a7873;
  --role-root:#2a78d6; --role-intermediate:#eb6834; --role-leaf:#1baf7a;
  --role-isolated:#b9b7ae;
  --accent:#2a78d6; --edge:#b9b7ae; --edge-strong:#52514e;
}
:root:not([data-theme="light"]) { }
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --surface-0:#121211; --surface-1:#1a1a19; --surface-2:#252523;
    --border:#383835; --border-strong:#4f4f4a;
    --text-primary:#ffffff; --text-secondary:#c3c2b7; --text-muted:#8e8d84;
    --role-root:#3987e5; --role-intermediate:#d95926; --role-leaf:#199e70;
    --role-isolated:#5b5b55;
    --accent:#3987e5; --edge:#4f4f4a; --edge-strong:#c3c2b7;
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --surface-0:#121211; --surface-1:#1a1a19; --surface-2:#252523;
  --border:#383835; --border-strong:#4f4f4a;
  --text-primary:#ffffff; --text-secondary:#c3c2b7; --text-muted:#8e8d84;
  --role-root:#3987e5; --role-intermediate:#d95926; --role-leaf:#199e70;
  --role-isolated:#5b5b55;
  --accent:#3987e5; --edge:#4f4f4a; --edge-strong:#c3c2b7;
}

*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{
  font:13px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
  background:var(--surface-0); color:var(--text-primary);
  display:flex; flex-direction:column; overflow:hidden;
}

/* ---------- top bar ---------- */
#top{
  display:flex; align-items:center; gap:14px; flex-wrap:wrap;
  padding:10px 16px; background:var(--surface-1);
  border-bottom:1px solid var(--border); flex-shrink:0;
}
#top h1{font-size:13px;font-weight:650;letter-spacing:-.1px;white-space:nowrap}
#top .src{font-size:11px;color:var(--text-muted);white-space:nowrap}
#stats{display:flex;gap:14px;flex-wrap:wrap;margin-left:auto;align-items:center}
.stat{display:flex;flex-direction:column;line-height:1.25}
.stat b{font-size:14px;font-weight:650;font-variant-numeric:tabular-nums}
.stat span{font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.4px}
.btn{
  background:var(--surface-2); border:1px solid var(--border); color:var(--text-secondary);
  padding:5px 11px; border-radius:6px; cursor:pointer; font:inherit; font-size:11.5px;
  white-space:nowrap;
}
.btn:hover{background:var(--surface-0);color:var(--text-primary)}
.btn.on{background:var(--accent);border-color:var(--accent);color:#fff}
.seg{display:flex;border:1px solid var(--border);border-radius:6px;overflow:hidden}
.seg .btn{border:0;border-radius:0}
.seg .btn+.btn{border-left:1px solid var(--border)}

/* ---------- layout ---------- */
#main{display:flex;flex:1;min-height:0}
#side{
  width:262px; flex-shrink:0; background:var(--surface-1);
  border-right:1px solid var(--border); display:flex; flex-direction:column; min-height:0;
}
#side .sec{padding:11px 13px;border-bottom:1px solid var(--border)}
#side .sec h2{
  font-size:10px;text-transform:uppercase;letter-spacing:.5px;
  color:var(--text-muted);font-weight:650;margin-bottom:8px;
}
#search{
  width:100%;padding:6px 9px;border:1px solid var(--border);border-radius:6px;
  background:var(--surface-0);color:var(--text-primary);font:inherit;font-size:12px;
}
#search::placeholder{color:var(--text-muted)}
#topicwrap{flex:1;overflow-y:auto;min-height:0;padding:6px}
.topic{
  display:flex;align-items:center;gap:8px;padding:5px 8px;border-radius:6px;
  cursor:pointer;font-size:12px;color:var(--text-secondary);
}
.topic:hover{background:var(--surface-2);color:var(--text-primary)}
.topic.on{background:var(--accent);color:#fff}
.topic .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.topic .n{font-size:10.5px;font-variant-numeric:tabular-nums;opacity:.75}
.topic .bar{height:3px;border-radius:2px;background:var(--accent);opacity:.5;flex-shrink:0}
.topic.on .bar{background:#fff;opacity:.8}

.chips{display:flex;flex-wrap:wrap;gap:5px}
.chip{
  font-size:10.5px;padding:3px 8px;border-radius:99px;cursor:pointer;
  border:1px solid var(--border);background:var(--surface-0);color:var(--text-secondary);
  display:flex;align-items:center;gap:5px;
}
.chip:hover{border-color:var(--border-strong);color:var(--text-primary)}
.chip.off{opacity:.4}
.chip .sw{width:8px;height:8px;border-radius:2px;flex-shrink:0}
.chip .cnt{font-variant-numeric:tabular-nums;opacity:.7}
label.opt{display:flex;align-items:center;gap:7px;font-size:11.5px;color:var(--text-secondary);cursor:pointer;padding:3px 0}
label.opt input{cursor:pointer;accent-color:var(--accent)}

/* ---------- canvas ---------- */
#stage{flex:1;position:relative;min-width:0;background:var(--surface-0)}
#cy{position:absolute;inset:0}
#empty{
  position:absolute;inset:0;display:none;align-items:center;justify-content:center;
  text-align:center;color:var(--text-muted);font-size:12.5px;padding:32px;
}
#hint{
  position:absolute;left:12px;bottom:12px;font-size:10.5px;color:var(--text-muted);
  background:var(--surface-1);border:1px solid var(--border);border-radius:6px;
  padding:5px 9px;pointer-events:none;max-width:60%;
}

/* ---------- detail ---------- */
#detail{
  width:308px;flex-shrink:0;background:var(--surface-1);border-left:1px solid var(--border);
  overflow-y:auto;display:none;
}
#detail.show{display:block}
#detail .pad{padding:14px}
#detail .close{float:right;cursor:pointer;color:var(--text-muted);font-size:16px;line-height:1;border:0;background:none}
#detail .close:hover{color:var(--text-primary)}
#detail .sid{font-size:11px;font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--accent);word-break:break-all}
#detail h3{font-size:13.5px;font-weight:600;margin:7px 0 11px;line-height:1.45}
#detail dl{display:grid;grid-template-columns:auto 1fr;gap:5px 11px;font-size:11.5px;margin-bottom:14px}
#detail dt{color:var(--text-muted)}
#detail dd{color:var(--text-primary)}
#detail h4{
  font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:var(--text-muted);
  font-weight:650;margin:13px 0 6px;
}
#detail ul{list-style:none;display:flex;flex-direction:column;gap:4px}
#detail li{
  font-size:11.5px;padding:6px 8px;background:var(--surface-2);border-radius:5px;cursor:pointer;
  border-left:2px solid var(--border-strong);
}
#detail li:hover{border-left-color:var(--accent)}
#detail li code{
  font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10px;color:var(--accent);
  display:block;margin-bottom:2px;
}
#detail .none{font-size:11.5px;color:var(--text-muted);font-style:italic}

.badge{
  display:inline-block;font-size:9.5px;font-weight:650;letter-spacing:.3px;
  padding:2px 6px;border-radius:4px;background:var(--surface-2);
  color:var(--text-secondary);border:1px solid var(--border);
}
#tip{
  position:absolute;display:none;pointer-events:none;z-index:50;max-width:330px;
  background:var(--surface-1);border:1px solid var(--border-strong);border-radius:7px;
  padding:9px 11px;font-size:11.5px;line-height:1.45;
  box-shadow:0 6px 20px rgba(0,0,0,.18);
}
#tip .t{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10px;color:var(--accent);margin-bottom:4px}
#tip .m{color:var(--text-muted);font-size:10.5px;margin-top:5px}

@media (max-width:900px){
  #side{width:210px}
  #detail{width:250px}
  #stats{width:100%;margin-left:0;order:3}
}
</style>
</head>
<body>

<div id="top">
  <h1>__TITLE__</h1>
  <span class="src">__SUBTITLE__</span>
  <div class="seg">
    <button class="btn on" id="m-topics">Topic map</button>
    <button class="btn" id="m-skills">Skill DAG</button>
  </div>
  <button class="btn" id="fit">Fit</button>
  <button class="btn" id="theme">Theme</button>
  <div id="stats"></div>
</div>

<div id="main">
  <aside id="side">
    <div class="sec"><input id="search" type="search" placeholder="Search skill id or text..." autocomplete="off"></div>
    <div class="sec">
      <h2>Structural role</h2>
      <div class="chips" id="roles"></div>
    </div>
    <div class="sec">
      <h2>Bloom level</h2>
      <div class="chips" id="blooms"></div>
    </div>
    <div class="sec">
      <label class="opt"><input type="checkbox" id="hide-iso"> Hide unconnected skills</label>
      <label class="opt"><input type="checkbox" id="show-ext" checked> Show cross-topic prerequisites</label>
    </div>
    <div class="sec" style="border-bottom:0;padding-bottom:4px">
      <h2 id="topichead">Topics</h2>
    </div>
    <div id="topicwrap"></div>
  </aside>

  <div id="stage">
    <div id="cy"></div>
    <div id="empty"></div>
    <div id="hint"></div>
  </div>

  <aside id="detail"><div class="pad" id="detailbody"></div></aside>
</div>

<div id="tip"></div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dagre@0.8.5/dist/dagre.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5.0/cytoscape-dagre.min.js"></script>
<script>
const DATA = __DATA__;
</script>
<script>
cytoscape.use(cytoscapeDagre);

const BLOOM_ORDER = ["Remember","Understand","Apply","Analyze","Evaluate","Create","Unspecified"];
const BLOOM_ABBR  = {Remember:"B1",Understand:"B2",Apply:"B3",Analyze:"B4",Evaluate:"B5",Create:"B6",Unspecified:"--"};
const ROLE_ORDER  = ["root","intermediate","leaf","isolated"];
const ROLE_LABEL  = {
  root:"Foundational", intermediate:"Intermediate", leaf:"Terminal", isolated:"Unconnected"
};
const ROLE_DESC = {
  root:"other skills depend on it; it has no prerequisite of its own",
  intermediate:"has prerequisites and dependents",
  leaf:"has prerequisites, nothing depends on it yet",
  isolated:"no prerequisite edge in either direction"
};

const byId = new Map(DATA.nodes.map(n => [n.id, n]));
const prereqsOf = new Map(), dependentsOf = new Map();
DATA.edges.forEach(e => {
  if(!prereqsOf.has(e.target)) prereqsOf.set(e.target, []);
  if(!dependentsOf.has(e.source)) dependentsOf.set(e.source, []);
  prereqsOf.get(e.target).push(e.source);
  dependentsOf.get(e.source).push(e.target);
});

const state = {
  mode: "topics",
  topic: null,
  roles: new Set(ROLE_ORDER),
  blooms: new Set(BLOOM_ORDER),
  hideIso: false,
  showExt: true,
  query: "",
  selected: null
};

function cssVar(n){ return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
function roleColor(r){ return cssVar("--role-" + r) || cssVar("--role-isolated"); }

/* ---------------- header stats ---------------- */
function renderStats(){
  const s = DATA.stats;
  document.getElementById("stats").innerHTML = [
    ["skills", s.skills],
    ["topics", s.topics],
    ["prereq edges", s.edges],
    ["unconnected", s.isolatedPct + "%"],
    ["fragments", s.components]
  ].map(([k,v]) => '<div class="stat"><b>'+v+'</b><span>'+k+'</span></div>').join("");
}

/* ---------------- sidebar ---------------- */
function renderChips(){
  document.getElementById("roles").innerHTML = ROLE_ORDER.map(r => {
    const n = DATA.stats.roles[r] || 0;
    return '<div class="chip'+(state.roles.has(r)?"":" off")+'" data-role="'+r+'" title="'+ROLE_DESC[r]+'">'
         + '<span class="sw" style="background:'+roleColor(r)+'"></span>'+ROLE_LABEL[r]
         + '<span class="cnt">'+n+'</span></div>';
  }).join("");
  document.querySelectorAll("[data-role]").forEach(el => el.onclick = () => {
    const r = el.dataset.role;
    state.roles.has(r) ? state.roles.delete(r) : state.roles.add(r);
    renderChips(); draw();
  });

  document.getElementById("blooms").innerHTML = BLOOM_ORDER
    .filter(b => DATA.stats.blooms[b])
    .map(b => '<div class="chip'+(state.blooms.has(b)?"":" off")+'" data-bloom="'+b+'">'
            + '<span class="badge" style="padding:1px 4px">'+BLOOM_ABBR[b]+'</span>'+b
            + '<span class="cnt">'+DATA.stats.blooms[b]+'</span></div>').join("");
  document.querySelectorAll("[data-bloom]").forEach(el => el.onclick = () => {
    const b = el.dataset.bloom;
    state.blooms.has(b) ? state.blooms.delete(b) : state.blooms.add(b);
    renderChips(); draw();
  });
}

function renderTopics(){
  const max = Math.max.apply(null, DATA.topics.map(t => t.count));
  const head = document.getElementById("topichead");
  head.textContent = state.mode === "skills"
    ? "Topics - pick one to draw" : "Topics (" + DATA.topics.length + ")";
  document.getElementById("topicwrap").innerHTML =
    (state.mode === "skills"
      ? '<div class="topic'+(state.topic===null?" on":"")+'" data-topic="__ALL__">'
        + '<span class="nm">All topics (slow)</span><span class="n">'+DATA.stats.skills+'</span></div>'
      : "")
    + DATA.topics.map(t =>
        '<div class="topic'+(state.topic===t.key?" on":"")+'" data-topic="'+t.key+'" title="'+t.key+'">'
      + '<span class="bar" style="width:'+Math.max(4, Math.round(30*t.count/max))+'px"></span>'
      + '<span class="nm">'+t.label+'</span><span class="n">'+t.count+'</span></div>').join("");

  document.querySelectorAll("[data-topic]").forEach(el => el.onclick = () => {
    const k = el.dataset.topic;
    state.topic = (k === "__ALL__") ? null : (state.topic === k ? null : k);
    if(state.topic && state.mode === "topics") setMode("skills");
    else { renderTopics(); draw(); }
  });
}

/* ---------------- filtering ---------------- */
function passes(n){
  if(!state.roles.has(n.role)) return false;
  if(!state.blooms.has(n.bloom || "Unspecified")) return false;
  if(state.hideIso && n.role === "isolated") return false;
  if(state.query){
    const q = state.query.toLowerCase();
    if(!(n.id.toLowerCase().includes(q) || n.full.toLowerCase().includes(q))) return false;
  }
  return true;
}

/* ---------------- drawing ---------------- */
let cy = null;

function baseStyle(){
  return [
    { selector:"node", style:{
        "background-color":"data(color)", "label":"data(label)",
        "font-size":"9px", "font-family":"ui-monospace,Menlo,Consolas,monospace",
        "color":cssVar("--text-primary"), "text-valign":"center", "text-halign":"center",
        "text-max-width":"104px", "text-wrap":"wrap",
        "width":"data(size)", "height":"data(size)",
        "border-width":2, "border-color":cssVar("--surface-0"),
        "shape":"round-rectangle", "padding":"5px"
    }},
    { selector:"node[kind='topic']", style:{
        "shape":"round-rectangle", "font-size":"10px", "font-weight":"600",
        "font-family":"-apple-system,Segoe UI,Arial,sans-serif",
        "text-max-width":"122px", "color":"#ffffff"
    }},
    { selector:"node[kind='external']", style:{
        "background-opacity":0.25, "border-style":"dashed",
        "border-color":cssVar("--border-strong"), "color":cssVar("--text-muted")
    }},
    { selector:"edge", style:{
        "width":"data(w)", "line-color":cssVar("--edge"),
        "target-arrow-color":cssVar("--edge"), "target-arrow-shape":"triangle",
        "arrow-scale":0.75, "curve-style":"bezier", "opacity":0.75
    }},
    { selector:"node:selected", style:{
        "border-width":3, "border-color":cssVar("--text-primary")
    }},
    { selector:".dim", style:{ "opacity":0.13 }},
    { selector:".hl", style:{
        "line-color":cssVar("--edge-strong"), "target-arrow-color":cssVar("--edge-strong"),
        "opacity":1, "width":2.5
    }}
  ];
}

function drawTopics(){
  const max = Math.max.apply(null, DATA.topics.map(t => t.count));
  const els = DATA.topics.map(t => ({ data:{
      id:"T:"+t.key, kind:"topic", label:t.label,
      color:cssVar("--role-root"),
      size: 34 + Math.round(58 * Math.sqrt(t.count / max)),
      topicKey:t.key
  }}));
  DATA.topicEdges.forEach((e,i) => els.push({ data:{
      id:"TE"+i, source:"T:"+e.source, target:"T:"+e.target,
      w: Math.min(6, 1 + e.weight * 0.7)
  }}));
  mount(els, { name:"cose", animate:false, padding:46, nodeRepulsion:11000,
               idealEdgeLength:118, nodeOverlap:18, gravity:0.5, numIter:1400 });
  hint("Bubble area = number of skills. Arrows = prerequisite links that cross a topic boundary (thickness = how many). Click a topic to open its skill DAG.");
}

function drawSkills(){
  const wanted = DATA.nodes.filter(n =>
    (state.topic === null || n.topic === state.topic) && passes(n));
  const wantedIds = new Set(wanted.map(n => n.id));

  // Pull in out-of-scope prerequisite neighbours as dimmed context nodes.
  const ext = new Set();
  if(state.showExt && state.topic !== null){
    wanted.forEach(n => {
      (prereqsOf.get(n.id) || []).forEach(p => { if(!wantedIds.has(p)) ext.add(p); });
      (dependentsOf.get(n.id) || []).forEach(d => { if(!wantedIds.has(d)) ext.add(d); });
    });
  }

  if(!wanted.length){
    mount([], null);
    empty("No skills match the current filters." +
          (state.topic ? " Try clearing the Bloom or role filters." : ""));
    return;
  }

  const maxDeg = Math.max(1, Math.max.apply(null, wanted.map(n => n.degree)));
  const els = [];
  wanted.forEach(n => els.push({ data:{
      id:n.id, kind:"skill", label:n.id, color:roleColor(n.role),
      size: 26 + Math.round(24 * (n.degree / maxDeg))
  }}));
  ext.forEach(id => { const n = byId.get(id); if(n) els.push({ data:{
      id:n.id, kind:"external", label:n.id, color:roleColor(n.role), size:24
  }}); });

  const present = new Set(els.map(e => e.data.id));
  let edgeCount = 0;
  DATA.edges.forEach((e,i) => {
    if(present.has(e.source) && present.has(e.target)){
      els.push({ data:{ id:"E"+i, source:e.source, target:e.target, w:1.6 } });
      edgeCount++;
    }
  });

  mount(els, { name:"dagre", rankDir:"TB", animate:false, padding:40,
               nodeSep:26, rankSep:62, edgeSep:12 });

  const isoShown = wanted.filter(n => n.role === "isolated").length;
  hint(wanted.length + " skills - " + edgeCount + " edges"
     + (ext.size ? " - " + ext.size + " dashed node(s) from other topics" : "")
     + (isoShown ? " - " + isoShown + " have no prerequisite link yet" : ""));
}

function mount(els, layout){
  document.getElementById("empty").style.display = "none";
  if(cy) cy.destroy();
  cy = cytoscape({
    container: document.getElementById("cy"),
    elements: els,
    style: baseStyle(),
    layout: layout || { name:"preset" },
    wheelSensitivity: 0.22,
    minZoom: 0.05, maxZoom: 3.5
  });

  cy.on("tap","node", ev => {
    const d = ev.target.data();
    if(d.kind === "topic"){ state.topic = d.topicKey; setMode("skills"); return; }
    select(d.id);
  });
  cy.on("tap", ev => { if(ev.target === cy) deselect(); });

  cy.on("mouseover","node", ev => showTip(ev));
  cy.on("mousemove","node", ev => moveTip(ev));
  cy.on("mouseout","node", hideTip);
}

function empty(msg){
  const el = document.getElementById("empty");
  el.textContent = msg; el.style.display = "flex";
  document.getElementById("hint").textContent = "";
}
function hint(t){ document.getElementById("hint").textContent = t; }

/* ---------------- tooltip ---------------- */
function showTip(ev){
  const d = ev.target.data();
  const tip = document.getElementById("tip");
  if(d.kind === "topic"){
    const t = DATA.topics.find(x => x.key === d.topicKey);
    tip.innerHTML = '<div class="t">'+t.key+'</div><div>'+t.label+'</div>'
      + '<div class="m">'+t.count+' skills - '+t.connected+' with a prerequisite link</div>';
  } else {
    const n = byId.get(d.id); if(!n) return;
    tip.innerHTML = '<div class="t">'+n.id+'</div><div>'+esc(n.full)+'</div>'
      + '<div class="m"><span class="badge">'+BLOOM_ABBR[n.bloom||"Unspecified"]+' '+(n.bloom||"Unspecified")+'</span> '
      + ROLE_LABEL[n.role]+' - '+n.prereqCount+' prereq / '+n.dependentCount+' dependent</div>';
  }
  tip.style.display = "block"; moveTip(ev);
}
function moveTip(ev){
  const tip = document.getElementById("tip"), r = document.getElementById("stage").getBoundingClientRect();
  let x = ev.renderedPosition.x + 16, y = ev.renderedPosition.y + 16;
  if(x + tip.offsetWidth > r.width) x = ev.renderedPosition.x - tip.offsetWidth - 14;
  if(y + tip.offsetHeight > r.height) y = ev.renderedPosition.y - tip.offsetHeight - 14;
  tip.style.left = Math.max(4,x)+"px"; tip.style.top = Math.max(4,y)+"px";
}
function hideTip(){ document.getElementById("tip").style.display = "none"; }
function esc(s){ return String(s).replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }

/* ---------------- detail panel ---------------- */
function select(id){
  const n = byId.get(id); if(!n) return;
  state.selected = id;
  const pr = (prereqsOf.get(id) || []).map(i => byId.get(i)).filter(Boolean);
  const dp = (dependentsOf.get(id) || []).map(i => byId.get(i)).filter(Boolean);

  const list = arr => arr.length
    ? '<ul>' + arr.map(s => '<li data-goto="'+s.id+'"><code>'+s.id+'</code>'+esc(s.full)+'</li>').join("") + '</ul>'
    : '<div class="none">none recorded</div>';

  document.getElementById("detailbody").innerHTML =
      '<button class="close" id="dclose">&times;</button>'
    + '<div class="sid">'+n.id+'</div><h3>'+esc(n.full)+'</h3>'
    + '<dl><dt>Bloom</dt><dd><span class="badge">'+BLOOM_ABBR[n.bloom||"Unspecified"]+'</span> '+(n.bloom||"Unspecified")+'</dd>'
    + '<dt>Topic</dt><dd>'+n.topicLabel+'</dd>'
    + '<dt>Role</dt><dd>'+ROLE_LABEL[n.role]+'</dd>'
    + '<dt>Fragment</dt><dd>'+(n.component < 0 ? "unconnected" : "#"+(n.component+1))+'</dd></dl>'
    + '<h4>Prerequisites ('+pr.length+')</h4>'+list(pr)
    + '<h4>Depends on this ('+dp.length+')</h4>'+list(dp);

  document.getElementById("detail").classList.add("show");
  document.getElementById("dclose").onclick = deselect;
  document.querySelectorAll("[data-goto]").forEach(el => el.onclick = () => {
    const t = byId.get(el.dataset.goto);
    if(t && t.topic !== state.topic && state.topic !== null){ state.topic = t.topic; renderTopics(); draw(); }
    setTimeout(() => { select(el.dataset.goto); focusNode(el.dataset.goto); }, 40);
  });

  focusNode(id);
}
function focusNode(id){
  if(!cy) return;
  const node = cy.getElementById(id);
  if(!node || node.empty()) return;
  cy.elements().addClass("dim");
  const nb = node.closedNeighborhood();
  nb.removeClass("dim");
  nb.edges().addClass("hl");
  cy.animate({ center:{ eles:node }, zoom:Math.max(cy.zoom(), 0.85) }, { duration:220 });
  cy.$(":selected").unselect(); node.select();
}
function deselect(){
  state.selected = null;
  document.getElementById("detail").classList.remove("show");
  if(cy){ cy.elements().removeClass("dim hl"); cy.$(":selected").unselect(); }
}

/* ---------------- mode / wiring ---------------- */
function setMode(m){
  state.mode = m;
  document.getElementById("m-topics").classList.toggle("on", m === "topics");
  document.getElementById("m-skills").classList.toggle("on", m === "skills");
  renderTopics(); draw();
}
function draw(){
  deselect();
  state.mode === "topics" ? drawTopics() : drawSkills();
}

document.getElementById("m-topics").onclick = () => setMode("topics");
document.getElementById("m-skills").onclick = () => setMode("skills");
document.getElementById("fit").onclick = () => cy && cy.fit(undefined, 40);
document.getElementById("hide-iso").onchange = e => { state.hideIso = e.target.checked; draw(); };
document.getElementById("show-ext").onchange = e => { state.showExt = e.target.checked; draw(); };

let qt = null;
document.getElementById("search").oninput = e => {
  clearTimeout(qt);
  qt = setTimeout(() => {
    state.query = e.target.value.trim();
    if(state.query && state.mode === "topics") setMode("skills");
    else draw();
  }, 220);
};

document.getElementById("theme").onclick = () => {
  const cur = document.documentElement.getAttribute("data-theme");
  const next = cur === "dark" ? "light"
    : cur === "light" ? "dark"
    : (matchMedia("(prefers-color-scheme: dark)").matches ? "light" : "dark");
  document.documentElement.setAttribute("data-theme", next);
  renderChips();
  if(cy){ cy.style(baseStyle()); redraw_colors(); }
};
function redraw_colors(){
  cy.nodes().forEach(n => {
    const d = n.data();
    if(d.kind === "topic") n.data("color", cssVar("--role-root"));
    else { const s = byId.get(d.id); if(s) n.data("color", roleColor(s.role)); }
  });
}

renderStats(); renderChips(); renderTopics(); setMode("topics");
</script>
</body>
</html>
"""


# --------------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate a standalone HTML viewer for an ATLAS skill ontology.")
    ap.add_argument("--source-dir", required=True, type=Path,
                    help="directory holding tuples.json + prereqs.json (read-only)")
    ap.add_argument("--out", required=True, type=Path,
                    help="output .html path (must not be named skill_ontology_dag.html)")
    ap.add_argument("--subject", default=None,
                    choices=["Mathematics", "Physics", "Chemistry"],
                    help="restrict to one subject (default: all subjects in the source)")
    ap.add_argument("--title", default=None, help="title shown in the viewer")
    args = ap.parse_args()

    if args.out.name == "skill_ontology_dag.html":
        sys.exit("error: refusing to write 'skill_ontology_dag.html' - "
                 "build_from_ontology.py treats that filename as an authoritative "
                 "ontology source. Pick another name.")

    data = load_ontology(args.source_dir, args.subject)
    s = data["stats"]

    title = args.title or (
        (args.subject + " " if args.subject else "") + "Skill Ontology")
    subtitle = "{src} - {n} skills, {e} prerequisite edges - generated {ts}".format(
        src=args.source_dir.as_posix(), n=s["skills"], e=s["edges"],
        ts=datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    html = (TEMPLATE
            .replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
            .replace("__TITLE__", title)
            .replace("__SUBTITLE__", subtitle))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")

    print("wrote {} ({:.1f} KB)".format(args.out.as_posix(), len(html.encode("utf-8")) / 1024))
    print("  skills            : {}".format(s["skills"]))
    print("  topics            : {}".format(s["topics"]))
    print("  prerequisite edges: {}".format(s["edges"]))
    print("  unconnected       : {} ({}%)".format(s["isolated"], s["isolatedPct"]))
    print("  fragments         : {} (largest {})".format(s["components"], s["largestComponent"]))
    if s["droppedEdgeRefs"]:
        print("  edge refs outside this subject slice, dropped: {}".format(s["droppedEdgeRefs"]))


if __name__ == "__main__":
    main()
