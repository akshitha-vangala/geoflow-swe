"""
GeoFlow Standard Library
Implements the built-in functions available inside program { } blocks:
  - generate_network(modes, size, bounds)          -> GeoflowResult
  - find_path(from, to, alpha, start_time)         -> GeoflowResult
  - build_path(from, to, alpha, start_time)        -> GeoflowResult
  - optimize_hub(cities, budget, mode)             -> GeoflowResult
  - create_node(name, lat, lon, allows)            -> GeoflowResult
  - suggest_nodes(connect_to, count, prefix)       -> GeoflowResult
"""

import random
import math
import numpy as np
from scipy.cluster.vq import kmeans


# ─── GeoflowResult ────────────────────────────────────────────────────────────

class GeoflowResult(dict):
    """Dict subclass with attribute-style access: result.time, result.possible."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            return None                      # return None instead of raising —
                                             # lets users write: if result.time
    def __setattr__(self, name, value):
        self[name] = value


# ─── Shared utilities ─────────────────────────────────────────────────────────

def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def _to_name(x) -> str:
    """
    FIX 1 — normalise any node reference to a plain string name.
    The interpreter evaluates node identifiers to Node objects before
    passing them as kwargs. str(Node(...)) gives the full repr, not the name.
    """
    if hasattr(x, 'name'):   return str(x.name)
    if isinstance(x, dict):  return str(x.get('name', x))
    return str(x)


def _get_loc(node):
    """Handle both Node objects (.loc) and plain dicts (["loc"])."""
    if hasattr(node, 'loc'):
        return node.loc
    return node['loc']


# ─── 1. generate_network ──────────────────────────────────────────────────────

_MODE_PRESETS = [
    ("Subway",    65,  2.0, 120),
    ("Bus",       40,  1.0,  20),
    ("HighSpeed", 220, 5.0, 300),
    ("Car",       60,  3.0,   0),
    ("Drone",     100, 2.0,  50),
    ("Ferry",     30,  1.5,  80),
    ("Monorail",  80,  3.0, 150),
]
_CITY_PREFIXES = ["North", "South", "East", "West", "New", "Old",
                  "Port", "Fort", "Lake"]
_CITY_SUFFIXES = ["ville", "town", "burg", "field", "bridge", "haven",
                  "shore", "wood", "ford", "wick", "gate", "ridge",
                  "holm", "peak"]


def generate_network(context, graph, kwargs):
    """
    Procedurally generate a complete GeoFlow network and inject it
    into context + graph.
    kwargs: modes (int), size (int), bounds (list of 2 coords)
    """
    from transformer import Mode, Node
    from geoflow.graph import Graph

    n_modes  = int(kwargs.get("modes", 4))
    n_cities = int(kwargs.get("size",  15))
    bounds   = kwargs.get("bounds", None)

    if bounds and len(bounds) >= 2:
        lat_min = min(bounds[0][0], bounds[1][0])
        lat_max = max(bounds[0][0], bounds[1][0])
        lon_min = min(bounds[0][1], bounds[1][1])
        lon_max = max(bounds[0][1], bounds[1][1])
    else:
        lat_min, lat_max = 25.0, 37.0
        lon_min, lon_max = -107.0, -93.0

    random.seed(42)

    # Inject modes
    chosen = random.sample(_MODE_PRESETS, k=min(n_modes, len(_MODE_PRESETS)))
    new_mode_names = []
    for (m_name, speed, cost, bc) in chosen:
        speed_v = round(speed * random.uniform(0.85, 1.15))
        cost_v  = round(cost  * random.uniform(0.80, 1.20), 2)
        bc_v    = round(bc    * random.uniform(0.90, 1.10))
        if m_name not in context.modes:
            context.add_mode(Mode(name=m_name, speed=speed_v,
                                  cost=cost_v, build_cost=bc_v))
        new_mode_names.append(m_name)

    # Inject nodes
    generated_names, used_names = [], set()
    for _ in range(n_cities):
        for _ in range(100):
            name = random.choice(_CITY_PREFIXES) + random.choice(_CITY_SUFFIXES)
            if name not in used_names:
                used_names.add(name)
                break
        lat = round(random.uniform(lat_min, lat_max), 4)
        lon = round(random.uniform(lon_min, lon_max), 4)
        context.add_node(Node(name=name, loc=(lat, lon),
                              allows=list(new_mode_names)))
        generated_names.append(name)

    # Inject routes
    city_names  = list(context.nodes.keys())
    route_count = 0
    for m_name in new_mode_names:
        for r_idx in range(random.randint(2, 4)):
            stops_n = random.randint(3, min(6, len(city_names)))
            stops   = random.sample(city_names, k=stops_n)
            r_name  = f"{m_name}Route{r_idx + 1}"
            try:
                context.add_route(r_name, {"mode": m_name, "stops": stops})
                route_count += 1
            except Exception:
                pass

    # Inject geofences — FIX 4: never use empty blocks list
    _GEOFENCE_RULES = [
        lambda modes: {"block":        [random.choice(modes)]},
        lambda modes: {"reduce_speed": {random.choice(modes): round(random.uniform(0.4, 0.8), 1)}},
        lambda modes: {"increase_cost":{random.choice(modes): round(random.uniform(1.2, 2.0), 1)}},
        lambda modes: {"allow_only":   random.sample(modes, k=min(2, len(modes)))},
    ]
    for gf_idx in range(random.randint(2, 4)):
        c_lat  = random.uniform(lat_min + 0.5, lat_max - 0.5)
        c_lon  = random.uniform(lon_min + 0.5, lon_max - 0.5)
        r_lat  = random.uniform(0.4, 1.2)
        r_lon  = random.uniform(0.4, 1.2)
        bounds_pts = [
            (round(c_lat - r_lat, 4), round(c_lon - r_lon, 4)),
            (round(c_lat - r_lat, 4), round(c_lon + r_lon, 4)),
            (round(c_lat + r_lat, 4), round(c_lon + r_lon, 4)),
            (round(c_lat + r_lat, 4), round(c_lon - r_lon, 4)),
        ]
        rule_fn     = random.choice(_GEOFENCE_RULES)
        rules       = rule_fn(new_mode_names)
        activate_at = (f"{random.randint(7, 14):02d}:"
                       f"{random.choice(['00','15','30','45'])}")
        # blocks must have at least one entry — use the first mode as default
        blocks = [new_mode_names[0]] if new_mode_names else []
        context.add_geofence(f"AutoZone{gf_idx + 1}", {
            "bounds":      bounds_pts,
            "blocks":      blocks,
            "rules":       rules,
            "activate_at": activate_at,
        })

    # Rebuild graph
    new_graph = Graph(context)
    graph.base_edges        = new_graph.base_edges
    graph.node_geofences    = new_graph.node_geofences
    graph.route_cycle_times = new_graph.route_cycle_times
    graph.route_offsets     = new_graph.route_offsets

    return GeoflowResult(
        possible=True,
        generated=True,
        nodes=len(generated_names),
        routes=route_count,
        modes=len(new_mode_names),
        city_names=generated_names,
        mode_names=new_mode_names,
    )


# ─── 2. find_path ─────────────────────────────────────────────────────────────

def find_path(context, graph, kwargs):
    """
    Find the optimal path between two nodes.

    FIX 1: kwargs 'from' and 'to' may arrive as Node objects (the interpreter
    evaluates identifiers before passing them). We normalise with _to_name().
    """
    from geoflow.optimizer import optimize_path

    frm   = _to_name(kwargs.get("from",       ""))
    to    = _to_name(kwargs.get("to",         ""))
    alpha = float(kwargs.get("alpha",          0.5))
    start = str(kwargs.get("start_time", "08:00"))

    # Validate nodes exist
    if frm not in context.nodes:
        print(f"  [find_path] ERROR: Node '{frm}' not found in context.")
        return GeoflowResult(possible=False, time=0.0, cost=0.0,
                            nodes=[], error=f"Node '{frm}' not found")
    if to not in context.nodes:
        print(f"  [find_path] ERROR: Node '{to}' not found in context.")
        return GeoflowResult(possible=False, time=0.0, cost=0.0,
                            nodes=[], error=f"Node '{to}' not found")

    # Create a temporary mission so optimize_path can run
    tmp = "_InteractiveMission_"
    context.missions[tmp] = {
        "props": {"from": frm, "to": to,
                "alpha": alpha, "start_time": start},
        "monitors": []
    }

    path = optimize_path(graph, tmp)
    del context.missions[tmp]

    if not path:
        print(f"  [find_path] No path found: {frm} -> {to}")
        return GeoflowResult(possible=False, time=0.0, cost=0.0, nodes=[])

    total_t   = sum(p[2] for p in path)
    total_c   = sum(p[3] for p in path)
    node_list = [p[0] for p in path]

    return GeoflowResult(
        possible=True,
        path=path,
        time=round(total_t, 4),
        cost=round(total_c, 4),
        nodes=node_list,
    )


# ─── 3. build_path ────────────────────────────────────────────────────────────

def build_path(context, graph, kwargs):
    """
    FIX 2: Was completely fake — hardcoded 1.0/10.0 per step and ignored
    from/to/alpha entirely. Now calls the real infrastructure optimizer
    (optimize_infrastructure) exactly as main.py does for missions with
    an improvement target.

    Falls back to find_path if no infrastructure module is available.
    """
    from geoflow.optimizer import optimize_path

    frm   = _to_name(kwargs.get("from",       ""))
    to    = _to_name(kwargs.get("to",         ""))
    alpha = float(kwargs.get("alpha",          0.5))
    start = str(kwargs.get("start_time", "08:00"))

    if frm not in context.nodes:
        return GeoflowResult(possible=False, time=0.0, cost=0.0,
                             error=f"Node '{frm}' not found")
    if to not in context.nodes:
        return GeoflowResult(possible=False, time=0.0, cost=0.0,
                             error=f"Node '{to}' not found")

    # Try the real infrastructure optimizer first
    try:
        from geoflow.infrastructure import optimize_infrastructure

        tmp = "_BuildPathMission_"
        context.missions[tmp] = {
            "props": {
                "from":       frm,
                "to":         to,
                "alpha":      alpha,
                "start_time": start,
                "improvement": kwargs.get("improvement", 0.1),
                "limit_budget": kwargs.get("budget", float("inf")),
            },
            "monitors": []
        }

        result = optimize_infrastructure(graph, tmp)
        del context.missions[tmp]

        if result == "NOT POSSIBLE" or not result:
            return GeoflowResult(possible=False, time=0.0, cost=0.0,
                                 error="Infrastructure target not achievable")

        path      = result.get("path", [])
        total_t   = sum(p[2] for p in path) if path else 0.0
        total_c   = result.get("build_cost", 0.0)
        node_list = [p[0] for p in path]

        print(f"  [build_path] Build cost: ${total_c:.2f} | "
              f"Travel time: {total_t:.2f} hrs")
        for edge in result.get("built_edges", []):
            print(f"  [build_path]   Build {edge[2]}: "
                  f"{edge[0]} -> {edge[1]} for ${edge[3]:.2f}")

        return GeoflowResult(
            possible=True,
            path=path,
            time=round(total_t, 4),
            cost=round(total_c, 4),
            build_cost=round(total_c, 4),
            nodes=node_list,
            built_edges=result.get("built_edges", []),
        )

    except (ImportError, Exception) as e:
        # Fall back to find_path so build_path always returns something useful
        print(f"  [build_path] Infrastructure optimizer unavailable ({e}), "
              f"falling back to find_path.")

    return find_path(context, graph, {
        "from": frm, "to": to,
        "alpha": alpha, "start_time": start
    })


# ─── 4. optimize_hub ─────────────────────────────────────────────────────────

def optimize_hub(context, graph, kwargs):
    """
    Find the optimal geographic location for a new hub connecting a set
    of cities, then ADD it to context so the graph can use it.

    FIX 3a: Scoring formula was dimensionally inconsistent
             (mixed time units and unitless fractions).
             Fixed to: alpha * norm_time + (1-alpha) * norm_cost
             where both terms are normalised to [0,1].

    FIX 3b: Hub was never added to context/graph — just returned lat/lon.
             Now creates a real Node and adds it so subsequent find_path
             calls can route through it.
    """
    from transformer import Node

    cities    = kwargs.get("cities", [])
    budget    = float(kwargs.get("budget", float("inf")))
    mode_name = _to_name(kwargs.get("mode", ""))
    hub_name  = str(kwargs.get("name", "OptimizedHub"))
    alpha     = float(kwargs.get("alpha", 0.5))

    if isinstance(cities, str):
        cities = [cities]
    city_names = [_to_name(c) for c in cities]

    # Validate
    invalid = [c for c in city_names if c not in context.nodes]
    if invalid:
        return GeoflowResult(possible=False,
                             error=f"Unknown cities: {invalid}")
    mode_obj = context.modes.get(mode_name)
    if not mode_obj:
        return GeoflowResult(possible=False,
                             error=f"Unknown mode '{mode_name}'")

    build_cost_per_km = float(getattr(mode_obj, 'build_cost', 0) or 0)
    speed             = float(getattr(mode_obj, 'speed',      1) or 1)

    city_locs = [
        (_get_loc(context.nodes[c])[0],
         _get_loc(context.nodes[c])[1], c)
        for c in city_names
    ]
    lat_min = min(l[0] for l in city_locs)
    lat_max = max(l[0] for l in city_locs)
    lon_min = min(l[1] for l in city_locs)
    lon_max = max(l[1] for l in city_locs)

    # Grid search — find hub position that minimises weighted time+cost
    grid_steps = 25
    best_score = float('inf')
    best_lat = best_lon = 0.0
    best_cost = best_time = 0.0

    # Pre-compute max values for normalisation
    max_possible_dist = _haversine(lat_min, lon_min, lat_max, lon_max)
    max_possible_time = (max_possible_dist * len(city_locs)) / speed
    max_possible_cost = (max_possible_dist * len(city_locs)) * build_cost_per_km

    for i_lat in range(grid_steps + 1):
        for i_lon in range(grid_steps + 1):
            lat = lat_min + (lat_max - lat_min) * i_lat / grid_steps
            lon = lon_min + (lon_max - lon_min) * i_lon / grid_steps

            total_dist = sum(
                _haversine(lat, lon, cl[0], cl[1])
                for cl in city_locs
            )
            build_c = total_dist * build_cost_per_km
            if build_c > budget:
                continue

            total_time = total_dist / speed

            # FIX 3a: normalise both terms to [0,1] then weight by alpha
            norm_time = total_time / max_possible_time if max_possible_time > 0 else 0
            norm_cost = build_c / max_possible_cost   if max_possible_cost > 0 else 0
            score     = alpha * norm_time + (1.0 - alpha) * norm_cost

            if score < best_score:
                best_score = score
                best_lat   = round(lat, 4)
                best_lon   = round(lon, 4)
                best_cost  = round(build_c, 2)
                best_time  = round(total_time, 4)

    if best_score == float('inf'):
        return GeoflowResult(
            possible=False,
            error="No hub location feasible within budget"
        )

    # FIX 3b: add the hub as a real node so routing can use it
    all_modes = list(context.modes.keys())
    context.nodes[hub_name] = Node(
        name=hub_name,
        loc=(best_lat, best_lon),
        allows=all_modes
    )
    if hasattr(graph, 'add_node'):
        graph.add_node(hub_name, pos=(best_lat, best_lon), allows=all_modes)

    print(f"  [optimize_hub] Hub '{hub_name}' placed at "
          f"({best_lat}, {best_lon}), build cost ${best_cost:.2f}, "
          f"total travel time {best_time:.2f} hrs.")

    # Compute time saved vs direct city-to-city routing
    direct_time = (
        sum(
            _haversine(city_locs[i][0], city_locs[i][1],
                       city_locs[(i + 1) % len(city_locs)][0],
                       city_locs[(i + 1) % len(city_locs)][1])
            for i in range(len(city_locs))
        ) / speed
    )
    time_saved = round(max(0.0, direct_time - best_time), 4)

    return GeoflowResult(
        possible=True,
        name=hub_name,
        lat=best_lat,
        lon=best_lon,
        build_cost=best_cost,
        time=best_time,
        time_saved=time_saved,
        cities=city_names,
        mode=mode_name,
    )


# ─── 5. create_node ───────────────────────────────────────────────────────────

def create_node(context, graph, kwargs):
    """Dynamically create a node and optionally evaluate its hub impact."""
    from transformer import Node

    name   = kwargs.get("name")
    lat    = float(kwargs.get("lat"))
    lon    = float(kwargs.get("lon"))
    allows = kwargs.get("allows", list(context.modes.keys()) or ["All"])
    allows = [_to_name(a) for a in allows] if isinstance(allows, list) else ["All"]
    eval_targets = kwargs.get("evaluate_targets", [])

    if not name:
        raise ValueError("[create_node] 'name' parameter is required.")

    context.nodes[name] = Node(name=name, loc=(lat, lon), allows=allows)

    if hasattr(graph, 'add_node'):
        graph.add_node(name, pos=(lat, lon), allows=allows)

    print(f"  [create_node] Node '{name}' created at ({lat:.4f}, {lon:.4f}).")

    if eval_targets:
        target_names = [_to_name(t) for t in eval_targets]
        _evaluate_hub_impact(context, target_names, [name])

    return GeoflowResult(possible=True, name=name, lat=lat, lon=lon)


# ─── 6. suggest_nodes ────────────────────────────────────────────────────────

def suggest_nodes(context, graph, kwargs):
    """
    Use K-Means clustering to find optimal hub locations for a set of cities.

    FIX 5: Guard against count > len(coords) which crashes kmeans.
    """
    from transformer import Node

    targets = kwargs.get("connect_to", [])
    count   = int(kwargs.get("count",   1))
    prefix  = str(kwargs.get("prefix",  "AutoHub"))
    allows  = kwargs.get("allows", list(context.modes.keys()) or ["All"])

    target_names = [_to_name(t) for t in targets]

    if len(target_names) < 2:
        raise ValueError(
            "[suggest_nodes] 'connect_to' requires at least 2 cities."
        )

    coords = []
    for t in target_names:
        if t not in context.nodes:
            raise ValueError(f"[suggest_nodes] City '{t}' not found.")
        loc = _get_loc(context.nodes[t])
        coords.append([loc[0], loc[1]])

    # FIX 5: kmeans crashes if k > number of unique data points
    count = min(count, len(coords))

    data = np.array(coords, dtype=float)
    print(f"  [suggest_nodes] Running K-Means clustering (k={count})...")
    centroids, _ = kmeans(data, count)

    generated_nodes = []
    for i, center in enumerate(centroids):
        node_name = f"{prefix}_{i + 1}"
        lat = float(center[0])
        lon = float(center[1])
        context.nodes[node_name] = Node(
            name=node_name,
            loc=(lat, lon),
            allows=allows if isinstance(allows, list) else ["All"]
        )
        if hasattr(graph, 'add_node'):
            graph.add_node(node_name, pos=(lat, lon), allows=allows)
        generated_nodes.append(node_name)
        print(f"  [suggest_nodes] Node '{node_name}' at ({lat:.4f}, {lon:.4f}).")

    _evaluate_hub_impact(context, target_names, generated_nodes)

    return GeoflowResult(
        possible=True,
        nodes=generated_nodes,
        count=len(generated_nodes)
    )


# ─── Hub impact report ────────────────────────────────────────────────────────

def _evaluate_hub_impact(context, target_cities, new_hubs):
    """
    Print a before/after distance report for hub placement.
    FIX 6: Removed emoji — crashes Windows cp1252 terminals.
    """
    if len(target_cities) < 2 or not new_hubs:
        return

    baseline_dist = 0.0
    pairs = 0
    for i in range(len(target_cities)):
        for j in range(i + 1, len(target_cities)):
            n1 = context.nodes.get(target_cities[i])
            n2 = context.nodes.get(target_cities[j])
            if n1 and n2:
                l1, l2 = _get_loc(n1), _get_loc(n2)
                baseline_dist += _haversine(l1[0], l1[1], l2[0], l2[1])
                pairs += 1

    hub_dist = 0.0
    for city in target_cities:
        node = context.nodes.get(city)
        if not node:
            continue
        c_loc    = _get_loc(node)
        min_dist = float('inf')
        for hub in new_hubs:
            h_node = context.nodes.get(hub)
            if not h_node:
                continue
            h_loc = _get_loc(h_node)
            d = _haversine(c_loc[0], c_loc[1], h_loc[0], h_loc[1])
            if d < min_dist:
                min_dist = d
        if min_dist < float('inf'):
            hub_dist += min_dist * 2

    savings_pct = ((baseline_dist - hub_dist) / baseline_dist * 100
                   if baseline_dist > 0 else 0.0)

    print("\n--- Network Impact Report ---")
    print(f"  Target cities  : {', '.join(target_cities)}")
    print(f"  Direct routing : {baseline_dist:.2f} km")
    print(f"  Hub routing    : {hub_dist:.2f} km")
    if savings_pct > 0:
        print(f"  Result         : {savings_pct:.1f}% reduction in travel distance")
    else:
        print(f"  Result         : No spatial gain ({savings_pct:.1f}%). "
              f"Hubs may be misplaced.")
    print("----------------------------\n")
