from geoflow.graph import Graph

def _node_name(x):
    """Normalise a path entry's node field to a plain string name."""
    if hasattr(x, 'name'):   return x.name        # Node object
    if isinstance(x, dict):  return x.get('name', str(x))
    return str(x)

def _get_loc(node_obj):
    """Get (lat, lon) from either a Node object or a dict-style node."""
    if hasattr(node_obj, 'loc'):  return node_obj.loc[0], node_obj.loc[1]
    if isinstance(node_obj, dict): return node_obj["loc"][0], node_obj["loc"][1]
    raise ValueError(f"[GeoFlow] Cannot get loc from {type(node_obj)}")


class Simulator:
    def __init__(self, context, graph: Graph, path):
        self.context  = context
        self.graph    = graph
        # FIX: normalise every tuple so index-0 is always a plain string
        self.path     = [
            (_node_name(p[0]),) + tuple(p[1:])
            for p in path
        ]
        self.timeline = []

    def run(self):
        start_node = self.path[0][0]
        current_time = 0.0

        node_obj = self.context.nodes[start_node]
        lat, lon = _get_loc(node_obj)

        self.timeline.append({
            "time":   current_time,
            "node":   start_node,
            "lat":    lat,
            "lon":    lon,
            "mode":   "START",
            "action": "departure"
        })

        for i in range(1, len(self.path)):
            curr_node_name, mode, t_hrs, cost = (
                self.path[i][0],
                self.path[i][1],
                self.path[i][2],
                self.path[i][3],
            )

            current_time += t_hrs

            if curr_node_name not in self.context.nodes:
                print(f"[GeoFlow] Simulator warning: node '{curr_node_name}' not in context, skipping.")
                continue

            node_obj = self.context.nodes[curr_node_name]
            lat, lon = _get_loc(node_obj)

            self.timeline.append({
                "time":         current_time,
                "node":         curr_node_name,
                "lat":          lat,
                "lon":          lon,
                "mode":         mode,
                "cost_incurred": cost,
                "action":       "arrival"
            })

        # ── Background cyclic routing traffic ────────────────────────────────
        for r_name, r_props in self.context.routes.items():
            m_name = r_props.get("mode")
            stops  = r_props.get("stops", [])
            if len(stops) < 2 or not m_name:
                continue

            t = 0.0
            max_sim_time = current_time + 4.0
            cycle_idx    = 0

            from geoflow.graph import parse_time
            m_props     = list(self.context.missions.values())[0]["props"] if self.context.missions else {}
            start_hours = parse_time(m_props.get("start_time", "08:00"))

            while t < max_sim_time:
                u_name = _node_name(stops[cycle_idx % len(stops)])
                v_name = _node_name(stops[(cycle_idx + 1) % len(stops)])

                base_dict = self.graph.base_edges.get(u_name, {}).get(v_name, {}).get(m_name)
                if not base_dict:
                    break

                abs_arr_time = start_hours + t
                edge_data    = self.graph.get_edge_metrics(
                    u_name, v_name, m_name, abs_arr_time,
                    base_dict["distance"], base_dict["base_speed"], base_dict["base_cost_per_km"]
                )
                if not edge_data:
                    break

                t_hrs  = edge_data["time"]

                if u_name not in self.context.nodes or v_name not in self.context.nodes:
                    break

                u_lat, u_lon = _get_loc(self.context.nodes[u_name])
                v_lat, v_lon = _get_loc(self.context.nodes[v_name])

                self.timeline.append({
                    "time": start_hours + t,   "node": u_name, "lat": u_lat, "lon": u_lon,
                    "mode": m_name, "action": f"{r_name} waiting", "is_background": True
                })
                t += t_hrs
                self.timeline.append({
                    "time": start_hours + t,   "node": v_name, "lat": v_lat, "lon": v_lon,
                    "mode": m_name, "action": f"{r_name} arriving", "is_background": True
                })

                cycle_idx += 1

        return self.timeline