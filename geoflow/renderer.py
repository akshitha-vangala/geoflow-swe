import json
import os
import sys

MODE_COLORS = ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231", "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe", "#008080", "#e6beff", "#9a6324", "#fffac8", "#800000", "#aaffc3", "#808000", "#ffd8b1", "#000075", "#808080", "#ffffff", "#000000"]

def _node_name(x):
    """Normalise a node reference to a plain string name to prevent JSON crashes."""
    if hasattr(x, 'name'):    return str(x.name)
    if isinstance(x, dict):   return str(x.get('name', x))
    return str(x)

def render_map(context, graph, path_nodes: list, timeline: list, output_file: str):
    print(f"  [Renderer] Preparing to generate map at: {output_file}...")
    
    if not context.nodes:
        print("  [Renderer Error] Context contains no nodes. Aborting.")
        return

    os.makedirs(os.path.dirname(output_file) or "outputs", exist_ok=True)

    # 1. Clean Path (Force string conversions)
    clean_path = []
    for p in path_nodes:
        if isinstance(p, (list, tuple)) and len(p) >= 1:
            clean_path.append((_node_name(p[0]),) + tuple(p[1:]))
        else:
            clean_path.append(p)

    data = {
        "nodes":     {},
        "modes":     {},
        "routes":    {},
        "geofences": {},
        "mission":   {},
        "path":      clean_path,
        "timeline":  timeline
    }

    # 2. Nodes (Strict type enforcement for JSON)
    for n_id, n in context.nodes.items():
        if isinstance(n, dict):
            lat, lon  = float(n["loc"][0]), float(n["loc"][1])
            allows    = [str(a) for a in n.get("allows", [])]
            is_hypo   = bool(n.get("is_hypothetical", False))
        else:
            lat, lon  = float(n.loc[0]), float(n.loc[1])
            allows    = [str(a) for a in n.allows]
            is_hypo   = bool(getattr(n, 'is_hypothetical', False))

        data["nodes"][str(n_id)] = {
            "lat": lat,
            "lon": lon,
            "allows": allows,
            "is_hypothetical": is_hypo
        }

    # 3. Modes
    color_idx = 0
    data["modes"]["Walking"] = {"speed": 5.0, "cost": 0.0, "color": "#888888"}

    for m_name, m in context.modes.items():
        if str(m_name) == "Walking": continue
        data["modes"][str(m_name)] = {
            "speed": float(m.speed or 0),
            "cost":  float(m.cost or 0),
            "color": MODE_COLORS[color_idx % len(MODE_COLORS)]
        }
        color_idx += 1

    # 4. Routes
    for r_name, r in context.routes.items():
        data["routes"][str(r_name)] = {
            "mode":  str(r.get("mode")),
            "stops": [_node_name(s) for s in r.get("stops", [])]
        }

    # 5. Geofences
    for g_name, g in context.geofences.items():
        data["geofences"][str(g_name)] = {
            "bounds":      [[float(c[0]), float(c[1])] for c in g.get("bounds", [])],
            "blocks":      [str(b) for b in g.get("blocks", [])],
            "rules":       g.get("rules", {}),
            "activate_at": str(g.get("activate_at", "00:00")),
            "active":      True
        }

    # 6. Mission
    if clean_path:
        data["mission"] = {
            "name":       "Imperative Route",
            "start":      str(clean_path[0][0]),
            "end":        str(clean_path[-1][0]),
            "start_time": "08:00",
            "alpha":      1.0
        }
    elif context.missions:
        m_name  = list(context.missions.keys())[0]
        m_props = context.missions[m_name]["props"]
        data["mission"] = {
            "name":       str(m_name),
            "start":      str(m_props.get("from")),
            "end":        str(m_props.get("to")),
            "start_time": str(m_props.get("start_time", "08:00")),
            "alpha":      float(m_props.get("alpha", 1.0))
        }

    # 7. Convert to JSON safely
    try:
        json_payload = json.dumps(data)
    except Exception as e:
        print(f"  [Renderer Error] Failed to serialize data to JSON: {e}")
        return

    # 8. Locate Template file (Checks both 'geoflow' subfolder and root folder)
    template_path_sub = os.path.join(os.path.dirname(__file__), "template.html")
    template_path_root = os.path.join(os.getcwd(), "template.html")
    
    if os.path.exists(template_path_sub):
        template_path = template_path_sub
    elif os.path.exists(template_path_root):
        template_path = template_path_root
    else:
        print(f"  [Renderer Error] 'template.html' is missing! Put it in the root or 'geoflow/' folder.")
        return

    # 9. Write Output
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("{{GEOFLOW_DATA}}", json_payload)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
        
    print(f"  [Renderer] ✅ Successfully built interactive dashboard!")
    print(f"  [Renderer DEBUG] clean_path sample: {clean_path[:3]}")
    print(f"  [Renderer DEBUG] path entry lengths: {[len(p) for p in clean_path[:5]]}")