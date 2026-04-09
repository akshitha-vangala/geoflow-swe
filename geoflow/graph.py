from shapely.geometry import Point, Polygon
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = math.sin((lat2-lat1)/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2-lon1)/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def parse_time(t_str):
    if not t_str: return 0.0
    pts = str(t_str).split(':')
    return int(pts[0]) + (int(pts[1])/60.0 if len(pts)>1 else 0.0)

class Graph:
    def __init__(self, context):
        self.context = context
        self.base_edges = {} # (u, v) -> { mode_name: {"base_speed": s, "base_cost": c, "distance": d, "route": r_name} }
        self.node_geofences = {} # n_name -> [ (g_name, g_dict) ]
        self.route_cycle_times = {} 
        self.route_offsets = {} # r_name -> { stop_name: offset_hrs }
        self._build()

    def _build(self):
        # Auto-inject Walking mode if not present
        if "Walking" not in self.context.modes:
            from transformer import Mode
            self.context.modes["Walking"] = Mode("Walking", speed=5.0, cost=0.0)
            
        nodes = list(self.context.nodes.values())
        geofences = list(self.context.geofences.values())
        
        self.node_geofences = {}
        for n in nodes:
            n_name = n.name if hasattr(n, 'name') else n.get('name', str(n))
            self.node_geofences[n_name] = []
        for g_name, g in self.context.geofences.items():
            bounds = g.get("bounds", [])
            if not bounds: continue
            poly = Polygon(bounds)
            for n in nodes:
                pt = Point(n.loc[0], n.loc[1])
                if poly.contains(pt):
                    n_name = n.name if hasattr(n, 'name') else n.get('name', str(n))
                    self.node_geofences[n_name].append((g_name, g))
                    
        # Add point-to-point implicit connections
        for mode_name in ["Walking", "Car"]:
            mode_obj = self.context.modes.get(mode_name)
            if not mode_obj: continue
            for u in nodes:
                for v in nodes:
                    if u.name == v.name: continue
                    dist_km = haversine(u.loc[0], u.loc[1], v.loc[0], v.loc[1])
                    if u.name not in self.base_edges: self.base_edges[u.name] = {}
                    self.base_edges[u.name].setdefault(v.name, {})[mode_name] = {
                        "base_speed": mode_obj.speed,
                        "base_cost_per_km": mode_obj.cost,
                        "distance": dist_km,
                        "route": None
                    }

        # Add Vehicle connections strictly from explicit Routes
        for r_name, r_props in self.context.routes.items():
            m_name = r_props.get("mode")
            stops = r_props.get("stops", [])
            mode_obj = self.context.modes.get(m_name)
            
            if not mode_obj or mode_obj.speed <= 0 or len(stops) < 2:
                continue
                
            self.route_offsets[r_name] = {}
            current_offset = 0.0
            
            for i in range(len(stops)):
                u_name = stops[i]
                v_name = stops[(i + 1) % len(stops)] 
                
                if u_name not in self.route_offsets[r_name]:
                    self.route_offsets[r_name][u_name] = current_offset
                
                if u_name == v_name: continue
                
                u = self.context.nodes.get(u_name)
                v = self.context.nodes.get(v_name)
                if not u or not v: continue
                
                dist_km = haversine(u.loc[0], u.loc[1], v.loc[0], v.loc[1])
                
                if u_name not in self.base_edges: self.base_edges[u_name] = {}
                self.base_edges[u_name].setdefault(v_name, {})[m_name] = {
                    "base_speed": mode_obj.speed,
                    "base_cost_per_km": mode_obj.cost,
                    "distance": dist_km,
                    "route": r_name
                }
                current_offset += dist_km / mode_obj.speed
            
            self.route_cycle_times[r_name] = current_offset

    def get_edge_metrics(self, u_name, v_name, mode_name, abs_time_hrs, base_distance, base_speed, base_cost_per_km):
        speed_mult = 1.0
        cost_mult = 1.0
        is_blocked = False

        active_gfs = self.node_geofences.get(u_name, []) + self.node_geofences.get(v_name, [])
        for g_name, g in active_gfs:
            activation_time = parse_time(g.get("activate_at", "00:00"))
            if abs_time_hrs >= activation_time:
                rules = g.get("rules", {})
                
                if g.get("blocks") and mode_name in g["blocks"]:
                    is_blocked = True
                if "block" in rules and mode_name in rules["block"]:
                    is_blocked = True
                if "allow_only" in rules and rules["allow_only"] and mode_name not in rules["allow_only"]:
                    is_blocked = True
                    
                if "reduce_speed" in rules and mode_name in rules["reduce_speed"]:
                    speed_mult *= rules["reduce_speed"][mode_name]
                if "increase_speed" in rules and mode_name in rules["increase_speed"]:
                    speed_mult *= rules["increase_speed"][mode_name]
                    
                if "reduce_cost" in rules and mode_name in rules["reduce_cost"]:
                    cost_mult *= rules["reduce_cost"][mode_name]
                if "increase_cost" in rules and mode_name in rules["increase_cost"]:
                    cost_mult *= rules["increase_cost"][mode_name]
                    
        if is_blocked or base_speed * speed_mult <= 0:
            return None
            
        final_speed = base_speed * speed_mult
        return {
            "time": base_distance / final_speed,
            "cost": (base_distance * base_cost_per_km) * cost_mult,
            "distance": base_distance
        }
