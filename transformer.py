from lark import Transformer


class Mode:
    def __init__(self, name, speed=None, cost=None, payload_capacity=None):
        self.name = name
        self.speed = speed
        self.cost = cost
        self.payload_capacity = payload_capacity

    def __repr__(self):
        return (
            f"Mode(name={self.name}, speed={self.speed}, "
            f"cost={self.cost}, payload={self.payload_capacity})")


class Node:
    def __init__(self, name, loc=None, allows=None, schedule_windows=None):
        self.name = name
        self.loc = loc
        self.allows = allows or []
        self.schedule_windows = schedule_windows or []

    def __repr__(self):
        return f"Node(name={self.name}, loc={self.loc}, allows={self.allows})"


class Context:
    def __init__(self):
        self.nodes = {}
        self.modes = {}
        self.geofences = {}
        self.missions = {}

    def add_mode(self, mode):
        if mode.name in self.modes:
            raise Exception(f"Mode '{mode.name}' already defined")
        self.modes[mode.name] = mode

    def add_node(self, node):
        if node.name in self.nodes:
            raise Exception(f"Node '{node.name}' already defined")
        self.nodes[node.name] = node

    def add_geofence(self, name, props):
        if name in self.geofences:
            raise Exception(f"Geofence '{name}' already defined")
        self.geofences[name] = props

    def add_mission(self, name, props, monitor_blocks):
        if name in self.missions:
            raise Exception(f"Mission '{name}' already defined")
        self.missions[name] = {
            "props": props,
            "monitors": monitor_blocks
        }


class DSLTransformer(Transformer):
    def __init__(self, context):
        self.context = context

    def IDENTIFIER(self, token):
        return str(token)

    def NUMBER(self, token):
        return float(token)

    def BOOLEAN(self, token):
        return token == "true"

    def STRING(self, token):
        return token[1:-1]

    def CONDITION(self, token):
        return str(token)

    def ACTION(self, token):
        return str(token)

    def mode_decl(self, items):
        name = items[0]
        props = dict(items[1:])
        mode = Mode(
            name=name,
            speed=props.get("speed"),
            cost=props.get("cost"),
            payload_capacity=props.get("payload_capacity")
        )
        self.context.add_mode(mode)

    def mode_prop(self, items):
        return items[0]

    def speed_prop(self, items):
        return ("speed", items[0])

    def cost_prop(self, items):
        return ("cost", items[0])

    def payload_prop(self, items):
        return ("payload_capacity", items[0])

    def node_decl(self, items):
        name = items[0]
        props = dict(items[1:])
        node = Node(
            name=name,
            loc=props.get("loc"),
            allows=props.get("allows"),
            schedule_windows=props.get("schedule_windows")
        )
        self.context.add_node(node)

    def node_prop(self, items):
        return items[0]

    def loc_prop(self, items):
        return ("loc", items[0])

    def allows_prop(self, items):
        return ("allows", items[0])

    def schedule_prop(self, items):
        return ("schedule_windows", items[0])

    def geofence_decl(self, items):
        name = items[0]
        props = dict(items[1:])
        self.context.add_geofence(name, props)

    def geofence_prop(self, items):
        return items[0]

    def bounds_prop(self, items):
        return ("bounds", items[0])

    def blocks_prop(self, items):
        return ("blocks", items[0])

    def reactive_mission(self, items):
        name = items[0]
        props = {}
        monitors = []
        for item in items[1:]:
            if isinstance(item, tuple):
                props[item[0]] = item[1]
            else:
                monitors.append(item)
        self.context.add_mission(name, props, monitors)

    def from_prop(self, items):
        return ("from", items[0])

    def to_prop(self, items):
        return ("to", items[0])

    def start_time_prop(self, items):
        return ("start_time", items[0])

    def optimize_prop(self, items):
        return ("optimize", items[0])

    def limit_prop(self, items):
        return (f"limit_{items[0]}", items[1])

    def monitor_block(self, items):
        return {
            "name": items[0],
            "trigger": items[1],
            "fallback": items[2]
        }

    def trigger_stmt(self, items):
        return items[0]

    def fallback_stmt(self, items):
        return items[0]

    def render_stmt(self, items):
        name = items[0]
        props = dict(items[1:])
        return {
            "type": "render",
            "name": name,
            **props
        }

    def render_prop(self, items):
        return items[0]

    def execution_prop(self, items):
        return ("execution", str(items[0]))

    def timeline_prop(self, items):
        return ("timeline", items[0])

    def sim_speed_prop(self, items):
        return ("sim_speed", items[0])

    def nodes_prop(self, items):
        return ("show_nodes", items[0])

    def export_prop(self, items):
        return ("export_html", items[0])

    def coordinate(self, items):
        return (items[0], items[1])

    def coord_list(self, items):
        return items

    def list(self, items):
        return items
