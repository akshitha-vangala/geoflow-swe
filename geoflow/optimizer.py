import heapq
from geoflow.graph import Graph

def _parse_time(t_str):
    h, m = map(int, t_str.split(':'))
    return h + m / 60.0


def _get_window_wait_time(curr_time, windows):
    if not windows:
        return 0.0
    ct = curr_time % 24          # wrap absolute hours back to 0-24 clock
    best_wait = float('inf')
    for w in windows:
        open_s, close_s = w.split('-')
        t1 = _parse_time(open_s)
        t2 = _parse_time(close_s)
        if ct <= t2:
            # currently within or before this window today
            wait = max(0.0, t1 - ct)
            best_wait = min(best_wait, wait)
        else:
            # window already passed today — wait until it opens tomorrow
            wait = (24.0 - ct) + t1
            best_wait = min(best_wait, wait)
    return best_wait

def _get_vehicle_wait_time(graph: Graph, route_name, stop_name, current_time):
    if not route_name:
        return 0.0 # No wait time if not on a specialized cyclic route (e.g. Walking)
    
    cycle_time = graph.route_cycle_times.get(route_name)
    offset = graph.route_offsets.get(route_name, {}).get(stop_name)
    
    if cycle_time is None or offset is None or cycle_time <= 0:
        return 0.0
        
    # How much time until the vehicle reaches 'stop_name'
    time_since_vehicle_passed_offset0 = current_time % cycle_time
    wait = offset - time_since_vehicle_passed_offset0
    if wait < 0:
        wait += cycle_time
    return wait

def optimize_path(graph: Graph, mission_name: str):
    mission = graph.context.missions[mission_name]
    start = mission["props"].get("from")
    end = mission["props"].get("to")
    optimize = mission["props"].get("optimize", "time")
    alpha = mission["props"].get("alpha", 1.0 if optimize == "time" else 0.5)
    
    start_time_str = mission["props"].get("start_time", "08:00")
    start_hours = _parse_time(start_time_str)
    
    # queue: (weight, current_node, time_so_far, cost_so_far, path)
    queue = [(0.0, start, 0.0, 0.0, [(start, None, 0.0, 0.0, 0.0)])]
    visited = {}
    
    while queue:
        weight, u, t_total, c_total, path_so_far = heapq.heappop(queue)
        
        if u == end:
            return path_so_far
            
        if u in visited and visited[u] <= weight:
            continue
        visited[u] = weight
        
        # We need absolute arrival time tracking for dynamic waiting computations
        abs_arr_time = start_hours + t_total
        
        if u in graph.base_edges:
            for dst, modes in graph.base_edges[u].items():
                dst_node = graph.context.nodes[dst]
                
                for m_name, metrics in modes.items():
                    dynamic = graph.get_edge_metrics(u, dst, m_name, abs_arr_time, metrics["distance"], metrics["base_speed"], metrics["base_cost_per_km"])
                    if not dynamic:
                        continue
                        
                    travel_time = dynamic["time"]
                    
                    # Compute vehicle wait time if utilizing a cyclic transit route
                    route_wait = _get_vehicle_wait_time(graph, metrics["route"], u, abs_arr_time)
                    
                    # Compute schedule window wait time at the destination node
                    projected_abs_arr = abs_arr_time + route_wait + travel_time
                    node_wait = _get_window_wait_time(projected_abs_arr, getattr(dst_node, "schedule_windows", []))
                    
                    if node_wait == float('inf'):
                        continue 
                        
                    total_step_time = route_wait + travel_time + node_wait
                    c = dynamic["cost"]
                    
                    # Objective weighting matching alpha logic explicitly requested
                    edge_w = alpha * total_step_time + (1 - alpha) * c
                    new_w = weight + edge_w
                    
                    if dst not in visited or visited.get(dst, float('inf')) > new_w:
                        new_path = list(path_so_far)
                        new_path.append((dst, m_name, total_step_time, c, edge_w))
                        heapq.heappush(queue, (new_w, dst, t_total + total_step_time, c_total + c, new_path))
                        
    return None
