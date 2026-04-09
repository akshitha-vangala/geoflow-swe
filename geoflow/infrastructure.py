import heapq
from geoflow.graph import haversine, parse_time
from geoflow.optimizer import optimize_path

def optimize_infrastructure(graph, mission_name):
    mission = graph.context.missions[mission_name]
    start = mission["props"].get("from")
    end = mission["props"].get("to")
    # Using 'limit_budget' mapped from 'limit budget: X'
    budget = mission["props"].get("limit_budget", float('inf')) 
    improvement = mission["props"].get("improvement", 0.0)
    
    # 1. Baseline Route
    baseline_path = optimize_path(graph, mission_name)
    if not baseline_path:
        baseline_time = float('inf')
    else:
        baseline_time = sum(p[2] for p in baseline_path)
        
    target_time = baseline_time * (1 - improvement / 100.0)
    if target_time == float('inf') and improvement > 0:
        target_time = float('inf')
        
    # Queue: (weight (time), u, build_spent, t_total, path, built_edges)
    queue = [(0.0, start, 0.0, 0.0, [(start, None, 0.0, 0.0, 0.0)], [])]
    visited = {}
    
    modes = list(graph.context.modes.values())
    nodes = list(graph.context.nodes.values())
    
    while queue:
        weight, u, build_spent, t_total, path_so_far, built_edges = heapq.heappop(queue)
        
        if u == end:
            if t_total <= target_time or (baseline_time == float('inf') and t_total < float('inf')):
                return {
                    "path": path_so_far, 
                    "built_edges": built_edges, 
                    "time": t_total, 
                    "build_cost": build_spent
                }
            continue
            
        frontier = visited.setdefault(u, [])
        is_dominated = False
        for (v_w, v_b) in frontier:
            if v_w <= weight and v_b <= build_spent:
                is_dominated = True
                break
        if is_dominated:
            continue
        frontier.append((weight, build_spent))
        
        # Time tracking
        start_time_hrs = parse_time(mission["props"].get("start_time", "08:00"))
        abs_time = start_time_hrs + t_total

        # Original edges
        if u in graph.base_edges:
            for dst, m_dict in graph.base_edges[u].items():
                for m_name, metrics in m_dict.items():
                    dynamic = graph.get_edge_metrics(u, dst, m_name, abs_time, metrics["distance"], metrics["base_speed"], metrics["base_cost_per_km"])
                    if dynamic:
                        t = dynamic["time"]
                        new_w = weight + t
                        heapq.heappush(queue, (new_w, dst, build_spent, t_total + t, path_so_far + [(dst, m_name, t, dynamic["cost"], t)], built_edges))
        
        # New infrastructure edges (Building)
        u_node = graph.context.nodes[u]
        for v_node in nodes:
            if u == v_node.name: continue
            dist = haversine(u_node.loc[0], u_node.loc[1], v_node.loc[0], v_node.loc[1])
            for m in modes:
                b_cost = getattr(m, 'build_cost', 0.0) or 0.0
                if b_cost > 0 and m.speed > 0:
                    edge_build_cost = dist * b_cost
                    if build_spent + edge_build_cost <= budget:
                        t = dist / m.speed
                        dynamic = graph.get_edge_metrics(u, v_node.name, m.name, abs_time, dist, m.speed, m.cost)
                        if dynamic:
                            t = dynamic["time"]
                            new_w = weight + t
                            new_built = list(built_edges)
                            new_built.append((u, v_node.name, m.name, edge_build_cost))
                            heapq.heappush(queue, (new_w, v_node.name, build_spent + edge_build_cost, t_total + t, path_so_far + [(v_node.name, m.name + " (NEW)", t, dynamic["cost"], t)], new_built))

    return "NOT POSSIBLE"
