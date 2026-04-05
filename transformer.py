from lark import Transformer

# ─── AST Node Types for Imperative Program ────────────────────────────────────

class ASTNode:
    pass

class LetStmt(ASTNode):
    def __init__(self, name, expr):
        self.name = name; self.expr = expr

class AssignStmt(ASTNode):
    def __init__(self, name, expr):
        self.name = name; self.expr = expr

class PrintStmt(ASTNode):
    def __init__(self, args):
        self.args = args

class IfStmt(ASTNode):
    def __init__(self, cond, then_body, else_body=None):
        self.cond = cond; self.then_body = then_body; self.else_body = else_body or []

class ForStmt(ASTNode):
    def __init__(self, var, iterable, body):
        self.var = var; self.iterable = iterable; self.body = body

class WhileStmt(ASTNode):
    def __init__(self, cond, body):
        self.cond = cond; self.body = body

class ExprStmt(ASTNode):
    def __init__(self, expr): self.expr = expr

class ProgramBlock(ASTNode):
    def __init__(self, stmts): self.stmts = stmts

# ─── Expression AST Nodes ─────────────────────────────────────────────────────

class BinOp(ASTNode):
    def __init__(self, op, left, right):
        self.op = op; self.left = left; self.right = right

class UnaryOp(ASTNode):
    def __init__(self, op, operand):
        self.op = op; self.operand = operand

class MemberAccess(ASTNode):
    def __init__(self, obj, fields):  # fields is list of strs
        self.obj = obj; self.fields = fields

class CallExpr(ASTNode):
    def __init__(self, func, kwargs):
        self.func = func; self.kwargs = kwargs   # dict of name->expr

class Literal(ASTNode):
    def __init__(self, value): self.value = value

class ListLit(ASTNode):
    def __init__(self, items): self.items = items

class VarRef(ASTNode):
    def __init__(self, name): self.name = name


# ─── Domain Model Classes ─────────────────────────────────────────────────────

class Mode:
    def __init__(self, name, speed=None, cost=None, payload_capacity=None, build_cost=None):
        self.name = name
        self.speed = speed
        self.cost = cost
        self.payload_capacity = payload_capacity
        self.build_cost = build_cost

    def __repr__(self):
        return f"Mode(name={self.name}, speed={self.speed}, cost={self.cost}, build_cost={self.build_cost})"


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
        self.renders = {}
        self.routes = {}
        self.program = None        # ProgramBlock | None

    def add_route(self, name, props):
        if name in self.routes:
            raise Exception(f"Route '{name}' already defined")
        self.routes[name] = props

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

    def add_render(self, name, props):
        if name in self.renders:
            raise Exception(f"Render '{name}' already defined")
        self.renders[name] = props


# ─── Lark Transformer ─────────────────────────────────────────────────────────

class DSLTransformer(Transformer):
    def __init__(self, context):
        super().__init__()
        self.context = context

    def program(self, items):
        return self.context

    # ── Terminals ──────────────────────────────────────────────────────────────
    def IDENTIFIER(self, token): return str(token)
    def NUMBER(self, token): return float(token)
    def BOOLEAN(self, token): return token == "true"
    def STRING(self, token): return token[1:-1]
    def CONDITION(self, token): return str(token)
    def ACTION(self, token): return str(token)
    def MODIFIER_TYPE(self, token): return str(token)
    def CMP_OP(self, token): return str(token)
    def ADD_OP(self, token): return str(token)
    def MUL_OP(self, token): return str(token)

    # ── Modes ──────────────────────────────────────────────────────────────────
    def mode_decl(self, items):
        name = items[0]
        props = dict(items[1:])
        mode = Mode(name=name, speed=props.get("speed"), cost=props.get("cost"),
                    payload_capacity=props.get("payload_capacity"), build_cost=props.get("build_cost", 0.0))
        self.context.add_mode(mode)

    def mode_prop(self, items): return items[0]
    def speed_prop(self, items): return ("speed", items[0])
    def cost_prop(self, items): return ("cost", items[0])
    def payload_prop(self, items): return ("payload_capacity", items[0])
    def build_cost_prop(self, items): return ("build_cost", float(items[0]))

    # ── Nodes ──────────────────────────────────────────────────────────────────
    def node_decl(self, items):
        name = items[0]
        props = dict(items[1:])
        node = Node(name=name, loc=props.get("loc"), allows=props.get("allows"),
                    schedule_windows=props.get("schedule_windows"))
        self.context.add_node(node)

    def node_prop(self, items): return items[0]
    def loc_prop(self, items): return ("loc", items[0])
    def allows_prop(self, items): return ("allows", items[0])
    def schedule_prop(self, items): return ("schedule_windows", items)
    def schedule_window(self, items): return f"{items[0]}-{items[1]}"

    # ── Geofences ──────────────────────────────────────────────────────────────
    def geofence_decl(self, items):
        name = items[0]
        props = dict(items[1:])
        self.context.add_geofence(name, props)

    def geofence_prop(self, items): return items[0]
    def bounds_prop(self, items): return ("bounds", items[0])
    def blocks_prop(self, items): return ("blocks", items[0])
    def activate_at_prop(self, items): return ("activate_at", str(items[0]))

    def rules_block(self, items):
        rules = {}
        for item in items:
            rules[item[0]] = item[1]
        return ("rules", rules)

    def rule_stmt(self, items): return items[0]
    def block_rule(self, items): return ("block", items[0])
    def allow_only_rule(self, items): return ("allow_only", items[0])

    def modifier_stmt(self, items):
        mod_type = str(items[0])
        mod_dict = {}
        for mv in items[1:]:
            mod_dict[mv[0]] = mv[1]
        return (mod_type, mod_dict)

    def modifier_val(self, items): return (str(items[0]), float(items[1]))

    # ── Hubs ───────────────────────────────────────────────────────────────────
    def hub_decl(self, items):
        name = items[0]
        nodes_to_connect = items[1]
        lats, lons = [], []
        for n in nodes_to_connect:
            if n in self.context.nodes:
                loc = self.context.nodes[n].loc
                lats.append(loc[0]); lons.append(loc[1])
        if lats:
            median_lat = sum(lats)/len(lats)
            median_lon = sum(lons)/len(lons)
            node = Node(name=name, loc=(median_lat, median_lon), allows=["Walking"])
            self.context.add_node(node)
            if not hasattr(self.context, 'hubs_built'):
                self.context.hubs_built = []
            self.context.hubs_built.append({"name": name, "loc": (median_lat, median_lon), "connects": nodes_to_connect})

    def connects_prop(self, items): return items[0]

    # ── Routes ─────────────────────────────────────────────────────────────────
    def route_decl(self, items):
        name = items[0]
        props = dict(items[1:])
        self.context.add_route(name, props)

    def route_prop(self, items): return items[0]
    def route_mode_prop(self, items): return ("mode", items[0])
    def stops_prop(self, items): return ("stops", items[0])

    # ── Missions ───────────────────────────────────────────────────────────────
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

    def mission_prop(self, items): return items[0]
    def from_prop(self, items): return ("from", items[0])
    def to_prop(self, items): return ("to", items[0])
    def start_time_prop(self, items): return ("start_time", items[0])
    def alpha_prop(self, items): return ("alpha", float(items[0]))
    def improvement_prop(self, items): return ("improvement", float(items[0]))
    def optimize_prop(self, items): return ("optimize", items[0])
    def limit_prop(self, items): return (f"limit_{items[0]}", float(items[1]))

    def monitor_block(self, items):
        return {"name": items[0], "trigger": items[1], "fallback": items[2]}
    def trigger_stmt(self, items): return items[0]
    def fallback_stmt(self, items): return items[0]

    # ── Renders ────────────────────────────────────────────────────────────────
    def render_stmt(self, items):
        name = items[0]
        props = dict(items[1:])
        self.context.add_render(name, props)

    def render_prop(self, items): return items[0]
    def execution_prop(self, items): return ("execution", str(items[0]))
    def timeline_prop(self, items): return ("timeline", items[0])
    def sim_speed_prop(self, items): return ("sim_speed", items[0])
    def nodes_prop(self, items): return ("show_nodes", items[0])
    def export_prop(self, items): return ("export_html", items[0])

    # ── Shared ─────────────────────────────────────────────────────────────────
    def coordinate(self, items): return (items[0], items[1])
    def coord_list(self, items): return items
    def list(self, items): return items

    # ── Program Block ──────────────────────────────────────────────────────────
    def program_block(self, items):
        block = ProgramBlock(stmts=items)
        self.context.program = block

    def program_stmt(self, items): return items[0]

    def let_stmt(self, items):
        return LetStmt(name=items[0], expr=items[1])

    def assign_stmt(self, items):
        return AssignStmt(name=items[0], expr=items[1])

    def print_stmt(self, items):
        return PrintStmt(args=items[0] if items else [])

    def print_args(self, items): return items

    def if_then_body(self, items): return list(items)
    def if_else_body(self, items): return list(items)
    def for_body(self, items): return list(items)
    def while_body(self, items): return list(items)

    def if_stmt(self, items):
        cond = items[0]
        then_body = items[1]    # list from if_then_body
        else_body = items[2] if len(items) > 2 else []
        return IfStmt(cond=cond, then_body=then_body, else_body=else_body)

    def for_stmt(self, items):
        var = items[0]; it = items[1]; body = items[2]  # list from for_body
        return ForStmt(var=var, iterable=it, body=body)

    def while_stmt(self, items):
        cond = items[0]; body = items[1]  # list from while_body
        return WhileStmt(cond=cond, body=body)

    def expr_stmt(self, items): return ExprStmt(expr=items[0])

    # ── Expressions ────────────────────────────────────────────────────────────
    def expr(self, items): return items[0]
    def or_expr(self, items):
        result = items[0]
        for right in items[1:]:
            result = BinOp("or", result, right)
        return result

    def and_expr(self, items):
        result = items[0]
        for right in items[1:]:
            result = BinOp("and", result, right)
        return result

    def not_op(self, items): return UnaryOp("not", items[0])
    def not_expr(self, items): return items[0]

    def cmp_expr(self, items):
        if len(items) == 1: return items[0]
        return BinOp(items[1], items[0], items[2])

    def add_expr(self, items):
        result = items[0]
        i = 1
        while i < len(items):
            op = str(items[i]); right = items[i+1]
            result = BinOp(op, result, right); i += 2
        return result

    def mul_expr(self, items):
        result = items[0]
        i = 1
        while i < len(items):
            op = str(items[i]); right = items[i+1]
            result = BinOp(op, result, right); i += 2
        return result

    def neg_op(self, items): return UnaryOp("-", items[0])
    def unary_expr(self, items): return items[0]

    def postfix_expr(self, items):
        obj = items[0]
        if len(items) == 1: return obj
        return MemberAccess(obj=obj, fields=list(items[1:]))

    def atom(self, items): return items[0]
    def num_lit(self, items): return Literal(items[0])
    def str_lit(self, items): return Literal(items[0])
    def bool_lit(self, items): return Literal(items[0])
    def null_lit(self, items): return Literal(None)
    def tuple_lit(self, items): return Literal((float(items[0]), float(items[1])))
    def list_lit(self, items): return ListLit(items=list(items))
    def var_ref(self, items): return VarRef(name=items[0])

    def call_expr(self, items):
        func = items[0]
        kwargs = items[1] if len(items) > 1 else {}
        return CallExpr(func=func, kwargs=kwargs)

    def call_args(self, items):
        d = {}
        for k, v in items:
            d[k] = v
        return d

    def named_arg(self, items): return (items[0], items[1])