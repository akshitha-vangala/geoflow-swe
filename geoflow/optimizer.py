import heapq
import math
from geoflow.graph import Graph


def _parse_time(t_str):
    if isinstance(t_str, (int, float)):
        return float(t_str)
    h, m = map(int, str(t_str).split(':'))
    return h + m / 60.0


def _get_window_wait_time(curr_time, windows):
    if not windows:
        return 0.0
    ct = curr_time % 24
    best_wait = float('inf')
    for w in windows:
        if isinstance(w, (list, tuple)) and len(w) == 2:
            open_s, close_s = str(w[0]), str(w[1])
        else:
            parts = str(w).split('-')
            if len(parts) != 2:
                continue
            open_s, close_s = parts[0].strip(), parts[1].strip()
        t1 = _parse_time(open_s)
        t2 = _parse_time(close_s)
        if ct <= t2:
            wait = max(0.0, t1 - ct)
            best_wait = min(best_wait, wait)
        else:
            wait = (24.0 - ct) + t1
            best_wait = min(best_wait, wait)
    return best_wait


def _get_vehicle_wait_time(graph: Graph, route_name, stop_name, current_time):
    if not route_name:
        return 0.0
    cycle_time = graph.route_cycle_times.get(route_name)
    offset = graph.route_offsets.get(route_name, {}).get(stop_name)
    if cycle_time is None or offset is None or cycle_time <= 0:
        return 0.0
    time_since_vehicle_passed = current_time % cycle_time
    wait = offset - time_since_vehicle_passed
    if wait < 0:
        wait += cycle_time
    return wait


def _point_in_polygon(lat, lon, bounds):
    """
    Ray-casting point-in-polygon test.
    bounds: list of [lat, lon] or (lat, lon) pairs.
    """
    inside = False
    n = len(bounds)
    j = n - 1
    for i in range(n):
        xi, yi = float(bounds[i][0]), float(bounds[i][1])
        xj, yj = float(bounds[j][0]), float(bounds[j][1])
        if ((yi > lon) != (yj > lon)) and (lat < (xj - xi) * (lon - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _is_edge_geofence_blocked(context, u_name, v_name, mode_name, abs_time_hrs):
    """
    Check all active geofences to see if this edge (u->v via mode) is blocked
    at abs_time_hrs.

    Returns True if blocked, False if clear.

    Checks both endpoint nodes — if either endpoint is inside an active
    geofence that blocks this mode, the edge is considered blocked.
    """
    u_node = context.nodes.get(u_name)
    v_node = context.nodes.get(v_name)
    if not u_node or not v_node:
        return False

    # Get coordinates — handle both Node objects and plain dicts
    def _loc(node):
        if hasattr(node, 'loc'):
            return node.loc
        return node.get('loc', (0, 0))

    u_lat, u_lon = _loc(u_node)
    v_lat, v_lon = _loc(v_node)

    for g_name, g in context.geofences.items():
        # Skip inactive geofences
        if not g.get('active', True):
            continue

        # Check activation time
        activate_at = g.get('activate_at', '00:00')
        try:
            activate_hrs = _parse_time(activate_at)
        except Exception:
            activate_hrs = 0.0

        if abs_time_hrs < activate_hrs:
            continue  # geofence not yet active at this time

        bounds = g.get('bounds', [])
        if len(bounds) < 3:
            continue  # degenerate polygon, skip

        u_inside = _point_in_polygon(u_lat, u_lon, bounds)
        v_inside = _point_in_polygon(v_lat, v_lon, bounds)

        if not u_inside and not v_inside:
            continue  # neither endpoint in this geofence

        # ── Check blocks list ─────────────────────────────────────────────
        blocks = g.get('blocks', [])
        if mode_name in blocks:
            return True

        # ── Check rules ───────────────────────────────────────────────────
        rules = g.get('rules', {})

        if rules.get('block') and mode_name in rules['block']:
            return True

        if rules.get('allow_only'):
            if mode_name not in rules['allow_only']:
                return True

    return False


def _get_geofence_speed_cost_multipliers(context, u_name, v_name, mode_name, abs_time_hrs):
    """
    Return (speed_multiplier, cost_multiplier) from all active geofences
    affecting this edge. Multipliers stack multiplicatively.
    """
    u_node = context.nodes.get(u_name)
    v_node = context.nodes.get(v_name)
    if not u_node or not v_node:
        return 1.0, 1.0

    def _loc(node):
        if hasattr(node, 'loc'):
            return node.loc
        return node.get('loc', (0, 0))

    u_lat, u_lon = _loc(u_node)
    v_lat, v_lon = _loc(v_node)

    speed_mult = 1.0
    cost_mult  = 1.0

    for g_name, g in context.geofences.items():
        if not g.get('active', True):
            continue
        try:
            activate_hrs = _parse_time(g.get('activate_at', '00:00'))
        except Exception:
            activate_hrs = 0.0
        if abs_time_hrs < activate_hrs:
            continue

        bounds = g.get('bounds', [])
        if len(bounds) < 3:
            continue

        u_inside = _point_in_polygon(u_lat, u_lon, bounds)
        v_inside = _point_in_polygon(v_lat, v_lon, bounds)
        if not u_inside and not v_inside:
            continue

        rules = g.get('rules', {})
        rs = rules.get('reduce_speed', {})
        if mode_name in rs:
            speed_mult *= float(rs[mode_name])

        ic = rules.get('increase_cost', {})
        if mode_name in ic:
            cost_mult *= float(ic[mode_name])

        rc = rules.get('reduce_cost', {})
        if mode_name in rc:
            cost_mult *= float(rc[mode_name])

        isp = rules.get('increase_speed', {})
        if mode_name in isp:
            speed_mult *= float(isp[mode_name])

    return speed_mult, cost_mult


def optimize_path(graph: Graph, mission_name: str):
    mission = graph.context.missions[mission_name]
    props   = mission["props"]

    # Normalise start/end — may be Node objects or strings
    def _name(x):
        if hasattr(x, 'name'): return str(x.name)
        if isinstance(x, dict): return str(x.get('name', x))
        return str(x)

    start    = _name(props.get("from"))
    end      = _name(props.get("to"))
    optimize = props.get("optimize", "time")
    alpha    = float(props.get("alpha", 1.0 if optimize == "time" else 0.5))
    start_hours = _parse_time(props.get("start_time", "08:00"))

    if start not in graph.context.nodes:
        print(f"  [optimizer] ERROR: start node '{start}' not in context")
        return None
    if end not in graph.context.nodes:
        print(f"  [optimizer] ERROR: end node '{end}' not in context")
        return None

    # (weight, node, time_so_far, cost_so_far, path)
    queue   = [(0.0, start, 0.0, 0.0,
                [(start, None, 0.0, 0.0, 0.0)])]
    visited = {}

    while queue:
        weight, u, t_total, c_total, path_so_far = heapq.heappop(queue)

        if u == end:
            return path_so_far

        if u in visited and visited[u] <= weight:
            continue
        visited[u] = weight

        abs_arr_time = start_hours + t_total

        if u not in graph.base_edges:
            continue

        for dst, modes in graph.base_edges[u].items():
            dst_node = graph.context.nodes.get(dst)
            if not dst_node:
                continue

            for m_name, metrics in modes.items():

                # ── GEOFENCE BLOCK CHECK ──────────────────────────────────
                # This runs in the optimizer so the Python-computed path
                # respects geofences, not just the JS dashboard.
                if _is_edge_geofence_blocked(
                        graph.context, u, dst, m_name, abs_arr_time):
                    continue  # skip this edge entirely

                # ── Get base travel metrics from graph ────────────────────
                dynamic = graph.get_edge_metrics(
                    u, dst, m_name, abs_arr_time,
                    metrics["distance"], metrics["base_speed"],
                    metrics["base_cost_per_km"]
                )
                if not dynamic:
                    continue

                # ── Apply geofence speed/cost modifiers ───────────────────
                spd_mult, cst_mult = _get_geofence_speed_cost_multipliers(
                    graph.context, u, dst, m_name, abs_arr_time
                )
                travel_time = dynamic["time"] / spd_mult if spd_mult > 0 else float('inf')
                edge_cost   = dynamic["cost"] * cst_mult

                # ── Wait times ────────────────────────────────────────────
                route_wait = _get_vehicle_wait_time(
                    graph, metrics.get("route"), u, abs_arr_time
                )
                projected_arr = abs_arr_time + route_wait + travel_time
                node_wait = _get_window_wait_time(
                    projected_arr,
                    getattr(dst_node, "schedule_windows", [])
                    if not isinstance(dst_node, dict)
                    else dst_node.get("schedule_windows", [])
                )

                if node_wait == float('inf'):
                    continue

                total_step_time = route_wait + travel_time + node_wait

                # ── Objective function ────────────────────────────────────
                edge_w = alpha * total_step_time + (1 - alpha) * edge_cost
                new_w  = weight + edge_w

                if dst not in visited or visited.get(dst, float('inf')) > new_w:
                    new_path = list(path_so_far)
                    new_path.append(
                        (dst, m_name, total_step_time, edge_cost, edge_w)
                    )
                    heapq.heappush(queue, (
                        new_w, dst,
                        t_total + total_step_time,
                        c_total + edge_cost,
                        new_path
                    ))

    return None