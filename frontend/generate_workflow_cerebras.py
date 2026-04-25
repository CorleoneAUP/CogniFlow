"""
generate_workflow_cerebras.py
Génère des diagrammes de workflow (Mermaid, Graphviz, HTML)
via l'agent Cerebras AI.
"""
from __future__ import annotations

import json
import os
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from collections import defaultdict, deque

# ── Auto-chargement du .env ───────────────────────────────────────────────────
def _load_dotenv():
    """Charge le fichier .env le plus proche dans l'arborescence."""
    current = Path(__file__).resolve().parent
    for _ in range(5):  # Monte jusqu'à 5 niveaux
        env_file = current / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.strip() and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:  # Ne pas écraser les vraies vars
                        os.environ[key] = val
            break
        current = current.parent

_load_dotenv()
# ─────────────────────────────────────────────────────────────────────────────

from cerebras.cloud.sdk import Cerebras


# ---------------------------------------------------------------------------
# TOOL IMPLEMENTATIONS
# ---------------------------------------------------------------------------

def tool_validate_workflow(workflow: dict) -> dict:
    errors: list[str] = []
    node_ids = {n["id"] for n in workflow.get("nodes", [])}
    if not node_ids:
        errors.append("No nodes found.")
    for edge in workflow.get("edges", []):
        if edge["from"] not in node_ids:
            errors.append(f"Edge references unknown source node: {edge['from']}")
        if edge["to"] not in node_ids:
            errors.append(f"Edge references unknown target node: {edge['to']}")
    connected = {e["from"] for e in workflow["edges"]} | {e["to"] for e in workflow["edges"]}
    isolated = node_ids - connected
    if isolated:
        errors.append(f"Isolated nodes (no edges): {sorted(isolated)}")
    return {
        "valid": len(errors) == 0,
        "node_count": len(node_ids),
        "edge_count": len(workflow.get("edges", [])),
        "actors": sorted({n["actor"] for n in workflow["nodes"]}),
        "errors": errors,
    }


def tool_analyze_layout(workflow: dict) -> dict:
    actors = list(dict.fromkeys(n["actor"] for n in workflow["nodes"]))
    actor_lane = {a: i for i, a in enumerate(actors)}
    in_degree: dict[str, int] = defaultdict(int)
    adjacency: dict[str, list[str]] = defaultdict(list)
    node_ids = [n["id"] for n in workflow["nodes"]]
    for nid in node_ids:
        in_degree.setdefault(nid, 0)
    for e in workflow["edges"]:
        adjacency[e["from"]].append(e["to"])
        in_degree[e["to"]] += 1
    queue = deque(nid for nid in node_ids if in_degree[nid] == 0)
    topo_order: list[str] = []
    while queue:
        nid = queue.popleft()
        topo_order.append(nid)
        for nbr in adjacency[nid]:
            in_degree[nbr] -= 1
            if in_degree[nbr] == 0:
                queue.append(nbr)
    # Construit un mapping col sûr (résistant aux cycles)
    topo_col = {nid: i for i, nid in enumerate(topo_order)}
    fallback = len(topo_order)
    for nid in node_ids:
        if nid not in topo_col:
            topo_col[nid] = fallback
            fallback += 1

    node_positions = {
        nid: {
            "col": topo_col[nid],
            "row": actor_lane[next(n["actor"] for n in workflow["nodes"] if n["id"] == nid)]
        }
        for nid in node_ids
    }
    return {"actors": actors, "actor_lane": actor_lane, "topological_order": topo_order, "node_positions": node_positions}


def tool_render_mermaid(workflow: dict) -> dict:
    actor_nodes: dict[str, list] = defaultdict(list)
    for n in workflow["nodes"]:
        actor_nodes[n["actor"]].append(n)
    lines = ["flowchart TD"]
    def mermaid_node(n: dict) -> str:
        nid, text, shape = n["id"], n["text"].replace('"', "'"), n["shape"]
        if shape == "Diamond":
            return f'    {nid}{{"{text}"}}'
        elif shape == "Oval":
            return f'    {nid}(("{text}"))'
        else:
            return f'    {nid}["{text}"]'
    for actor, nodes in actor_nodes.items():
        safe = re.sub(r"[^A-Za-z0-9_]", "_", actor)
        lines.append(f'  subgraph {safe}["{actor}"]')
        for n in nodes:
            lines.append("  " + mermaid_node(n))
        lines.append("  end")
    for e in workflow["edges"]:
        arrow = f' -->|"{e["label"]}"| ' if e["label"] else " --> "
        lines.append(f'  {e["from"]}{arrow}{e["to"]}')
    return {"format": "mermaid", "definition": "\n".join(lines)}


def tool_render_graphviz(workflow: dict) -> dict:
    actor_nodes: dict[str, list] = defaultdict(list)
    for n in workflow["nodes"]:
        actor_nodes[n["actor"]].append(n)
    lines = [
        'digraph workflow {',
        '  rankdir=TB;',
        '  graph [fontname="Helvetica", fontsize=10, bgcolor="#f9f9f9"];',
        '  node  [fontname="Helvetica", fontsize=9, style=filled, fillcolor="#ddeeff"];',
        '  edge  [fontname="Helvetica", fontsize=8];',
    ]
    colors = ["#cce5ff", "#d4edda", "#fff3cd", "#f8d7da", "#e2d9f3", "#d1ecf1", "#fefefe", "#fde2b0"]
    for idx, (actor, nodes) in enumerate(actor_nodes.items()):
        color = colors[idx % len(colors)]
        safe_actor = re.sub(r"[^A-Za-z0-9_]", "_", actor)
        lines.append(f'  subgraph cluster_{safe_actor} {{')
        lines.append(f'    label="{actor}";')
        lines.append(f'    style=filled; fillcolor="{color}";')
        for n in nodes:
            text = n["text"].replace('"', "'")
            shape = {"Diamond": "diamond", "Oval": "ellipse"}.get(n["shape"], "box")
            lines.append(f'    {n["id"]} [label="{text}", shape={shape}];')
        lines.append("  }")
    for e in workflow["edges"]:
        label = f' [label="{e["label"]}"]' if e["label"] else ""
        lines.append(f'  {e["from"]} -> {e["to"]}{label};')
    lines.append("}")
    return {"format": "graphviz_dot", "definition": "\n".join(lines)}


def tool_render_html(workflow: dict, layout: dict | None = None) -> dict:
    NODE_W, NODE_H = 180, 50
    LANE_PAD       = 20
    H_GAP, V_GAP   = 40, 30
    LANE_HEADER    = 36
    actors  = list(dict.fromkeys(n["actor"] for n in workflow["nodes"]))
    n_lanes = len(actors)
    lane_h  = LANE_HEADER + NODE_H + V_GAP * 2
    in_degree: dict[str, int] = defaultdict(int)
    adjacency: dict[str, list[str]] = defaultdict(list)
    node_ids = [n["id"] for n in workflow["nodes"]]
    for nid in node_ids:
        in_degree.setdefault(nid, 0)
    for e in workflow["edges"]:
        adjacency[e["from"]].append(e["to"])
        in_degree[e["to"]] += 1
    queue = deque(nid for nid in node_ids if in_degree[nid] == 0)
    col_map: dict[str, int] = {}
    col = 0
    while queue:
        batch = list(queue); queue.clear()
        for nid in batch:
            col_map[nid] = col
            for nbr in adjacency[nid]:
                in_degree[nbr] -= 1
                if in_degree[nbr] == 0:
                    queue.append(nbr)
        col += 1
    # Fallback pour les nœuds dans des cycles (non atteints par le tri topo)
    max_col = max(col_map.values(), default=0)
    for nid in node_ids:
        if nid not in col_map:
            max_col += 1
            col_map[nid] = max_col
    n_cols  = max(col_map.values(), default=0) + 1
    SVG_W   = LANE_PAD * 2 + n_cols * (NODE_W + H_GAP)
    SVG_H   = LANE_PAD * 2 + n_lanes * lane_h
    node_map  = {n["id"]: n for n in workflow["nodes"]}
    actor_idx = {a: i for i, a in enumerate(actors)}
    def cx(nid): return LANE_PAD + col_map[nid] * (NODE_W + H_GAP) + NODE_W / 2
    def cy(nid):
        actor = node_map[nid]["actor"]
        lane  = actor_idx[actor]
        return LANE_PAD + lane * lane_h + LANE_HEADER + V_GAP + NODE_H / 2
    PALETTE = ["#e8f4fd", "#eaf7ec", "#fef9e7", "#fdecea", "#f0ebf8", "#e8f8fb", "#f5f5f5", "#fef3e2"]
    svg_parts: list[str] = []
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W}" height="{SVG_H}">')
    svg_parts.append('<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#555"/></marker></defs>')
    for i, actor in enumerate(actors):
        y = LANE_PAD + i * lane_h
        color = PALETTE[i % len(PALETTE)]
        svg_parts.append(f'<rect x="{LANE_PAD}" y="{y}" width="{SVG_W - LANE_PAD*2}" height="{lane_h}" fill="{color}" stroke="#ccc" stroke-width="1" rx="6"/>')
        label = textwrap.shorten(actor, width=60, placeholder="…")
        svg_parts.append(f'<text x="{LANE_PAD + 8}" y="{y + 22}" font-family="Segoe UI,Arial,sans-serif" font-size="11" font-weight="bold" fill="#333">{label}</text>')
    for e in workflow["edges"]:
        x1, y1 = cx(e["from"]), cy(e["from"])
        x2, y2 = cx(e["to"]),   cy(e["to"])
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        svg_parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#555" stroke-width="1.5" marker-end="url(#arrow)"/>')
        if e["label"]:
            svg_parts.append(f'<text x="{mx:.1f}" y="{my - 4:.1f}" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="10" fill="#c0392b" font-weight="bold">{e["label"]}</text>')
    for n in workflow["nodes"]:
        nid   = n["id"]
        x, y  = cx(nid) - NODE_W / 2, cy(nid) - NODE_H / 2
        label = textwrap.shorten(n["text"], width=28, placeholder="…")
        if n["shape"] == "Diamond":
            hw, hh = NODE_W / 2, NODE_H / 2
            px, py = cx(nid), cy(nid)
            pts = f"{px},{py - hh} {px + hw},{py} {px},{py + hh} {px - hw},{py}"
            svg_parts.append(f'<polygon points="{pts}" fill="#fffde7" stroke="#f39c12" stroke-width="2"/>')
        elif n["shape"] == "Oval":
            svg_parts.append(f'<ellipse cx="{cx(nid):.1f}" cy="{cy(nid):.1f}" rx="{NODE_W/2}" ry="{NODE_H/2}" fill="#f0fff0" stroke="#27ae60" stroke-width="2"/>')
        else:
            svg_parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{NODE_W}" height="{NODE_H}" rx="6" fill="#fff" stroke="#2980b9" stroke-width="2"/>')
        svg_parts.append(f'<text x="{cx(nid):.1f}" y="{cy(nid):.1f}" text-anchor="middle" dominant-baseline="middle" font-family="Segoe UI,Arial,sans-serif" font-size="10" fill="#222">{label}</text>')
    svg_parts.append("</svg>")
    svg_code = "\n".join(svg_parts)
    html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"/><title>Workflow Diagram</title>
<style>body{{margin:0;background:#f4f6f8;display:flex;flex-direction:column;align-items:center;padding:24px;font-family:Segoe UI,Arial,sans-serif;}}
h1{{color:#2c3e50;font-size:1.4rem;margin-bottom:16px;}}
.wrap{{background:#fff;border-radius:12px;box-shadow:0 4px 20px #0001;padding:20px;overflow-x:auto;}}</style>
</head><body><h1>Workflow — Processus de Marché</h1><div class="wrap">{svg_code}</div></body></html>"""
    return {"format": "html", "html": html}


# ---------------------------------------------------------------------------
# TOOL REGISTRY
# ---------------------------------------------------------------------------
TOOLS = [
    {"type":"function","function":{"name":"validate_workflow","description":"Validates the workflow JSON.","parameters":{"type":"object","properties":{"workflow":{"type":"object"}},"required":["workflow"],"additionalProperties":False}}},
    {"type":"function","function":{"name":"analyze_layout","description":"Analyzes topology and assigns swim-lane indices.","parameters":{"type":"object","properties":{"workflow":{"type":"object"}},"required":["workflow"],"additionalProperties":False}}},
    {"type":"function","function":{"name":"render_mermaid","description":"Generates Mermaid flowchart.","parameters":{"type":"object","properties":{"workflow":{"type":"object"}},"required":["workflow"],"additionalProperties":False}}},
    {"type":"function","function":{"name":"render_graphviz","description":"Generates Graphviz DOT.","parameters":{"type":"object","properties":{"workflow":{"type":"object"}},"required":["workflow"],"additionalProperties":False}}},
    {"type":"function","function":{"name":"render_html","description":"Generates HTML/SVG swim-lane diagram.","parameters":{"type":"object","properties":{"workflow":{"type":"object"}},"required":["workflow"],"additionalProperties":False}}},
]


def dispatch_tool(name: str, arguments: str) -> Any:
    handlers = {
        "validate_workflow": tool_validate_workflow,
        "analyze_layout":    tool_analyze_layout,
        "render_mermaid":    tool_render_mermaid,
        "render_graphviz":   tool_render_graphviz,
        "render_html":       tool_render_html,
    }
    if name not in handlers:
        return {"error": f"Unknown tool: {name}"}
    try:
        args_dict = json.loads(arguments) if isinstance(arguments, str) else arguments
    except (json.JSONDecodeError, TypeError) as e:
        return {"error": f"Failed to parse arguments: {e}"}
    try:
        return handlers[name](**args_dict)
    except Exception as e:
        return {"error": f"Tool execution failed: {e}"}


# ---------------------------------------------------------------------------
# PIPELINE SÉQUENTIELLE (sans LLM — appels directs)
# ---------------------------------------------------------------------------

from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class AgentResult:
    mermaid_def:  str = ""
    graphviz_def: str = ""
    html_content: str = ""
    summary:      str = ""
    tool_calls:   list[str] = field(default_factory=list)


def save_outputs(result: AgentResult, output_dir: str = "diagram_output") -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    if result.mermaid_def:
        p = out / "workflow.mmd"; p.write_text(result.mermaid_def, encoding="utf-8"); paths["mermaid"] = p
    if result.graphviz_def:
        p = out / "workflow.dot"; p.write_text(result.graphviz_def, encoding="utf-8"); paths["graphviz"] = p
    if result.html_content:
        p = out / "workflow.html"; p.write_text(result.html_content, encoding="utf-8"); paths["html"] = p
    return paths


def main(workflow: dict) -> AgentResult:
    """Pipeline séquentielle : appels directs aux fonctions, sans LLM."""
    result = AgentResult()

    # 1. Validation
    validation = tool_validate_workflow(workflow)
    result.tool_calls.append("validate_workflow")
    if not validation["valid"]:
        result.summary = f"⚠️ Workflow invalide : {validation['errors']}"
        return result

    # 2. Analyse du layout
    tool_analyze_layout(workflow)
    result.tool_calls.append("analyze_layout")

    # 3. Mermaid
    mermaid = tool_render_mermaid(workflow)
    result.mermaid_def = mermaid.get("definition", "")
    result.tool_calls.append("render_mermaid")

    # 4. Graphviz
    graphviz = tool_render_graphviz(workflow)
    result.graphviz_def = graphviz.get("definition", "")
    result.tool_calls.append("render_graphviz")

    # 5. HTML
    html = tool_render_html(workflow)
    result.html_content = html.get("html", "")
    result.tool_calls.append("render_html")

    result.summary = (
        f"✅ {validation['node_count']} nœuds, "
        f"{validation['edge_count']} edges, "
        f"{len(validation['actors'])} acteurs. "
        f"Diagrammes générés : Mermaid, Graphviz, HTML."
    )

    save_outputs(result)
    return result


if __name__ == "__main__":
    sample = {
        "nodes": [
            {"id": "N1", "actor": "SERVICE CONTRACTANT", "shape": "Oval",      "text": "Début"},
            {"id": "N2", "actor": "SERVICE CONTRACTANT", "shape": "Rectangle", "text": "Préparer contrat"},
            {"id": "N3", "actor": "FIN",                 "shape": "Oval",      "text": "Classement"},
        ],
        "edges": [
            {"from": "N1", "to": "N2", "label": None},
            {"from": "N2", "to": "N3", "label": None},
        ]
    }
    r = main(sample)
    print(r.summary)

