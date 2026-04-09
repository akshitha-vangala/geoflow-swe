from lark import Transformer


# AST Node Types for Imperative Program


class ASTNode:
    pass


class LetStmt(ASTNode):
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr


class AssignStmt(ASTNode):
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr


class PrintStmt(ASTNode):
    def __init__(self, args):
        self.args = args


class IfStmt(ASTNode):
    def __init__(self, cond, then_body, else_body=None):
        self.cond = cond
        self.then_body = then_body
        self.else_body = else_body or []


class ForStmt(ASTNode):
    def __init__(self, var, iterable, body):
        self.var = var
        self.iterable = iterable
        self.body = body


class WhileStmt(ASTNode):
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body


class ExprStmt(ASTNode):
    def __init__(self, expr):
        self.expr = expr


class ProgramBlock(ASTNode):
    def __init__(self, stmts):
        self.stmts = stmts


# Expression AST Nodes


class BinOp(ASTNode):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right


class UnaryOp(ASTNode):
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand


class MemberAccess(ASTNode):
    def __init__(self, obj, fields):
        self.obj = obj
        self.fields = fields


class CallExpr(ASTNode):
    def __init__(self, func, kwargs):
        self.func = func
        self.kwargs = kwargs


class Literal(ASTNode):
    def __init__(self, value):
        self.value = value


class ListLit(ASTNode):
    def __init__(self, items):
        self.items = items


class VarRef(ASTNode):
    def __init__(self, name):
        self.name = name


# Domain Model Classes


class Mode:
    def __init__(
        self,
        name,
        speed=None,
        cost=None,
        payload_capacity=None,
        build_cost=None,
    ):
        self.name = name
        self.speed = speed
        self.cost = cost
        self.payload_capacity = payload_capacity
        self.build_cost = build_cost

    def __repr__(self):
        return (
            f"Mode(name={self.name}, speed={self.speed}, "
            f"cost={self.cost}, build_cost={self.build_cost})"
        )


class Node:
    def __init__(self, name, loc=None, allows=None, schedule_windows=None):
        self.name = name
        self.loc = loc
        self.allows = allows or []
        self.schedule_windows = schedule_windows or []

    def __repr__(self):
        return (
            f"Node(name={self.name}, loc={self.loc}, "
            f"allows={self.allows})"
        )


class Context:
    def __init__(self):
        self.nodes = {}
        self.modes = {}
        self.geofences = {}
        self.missions = {}
        self.renders = {}
        self.routes = {}
        self.program = None

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
        self.missions[name] = {"props": props, "monitors": monitor_blocks}

    def add_render(self, name, props):
        if name in self.renders:
            raise Exception(f"Render '{name}' already defined")
        self.renders[name] = props


# Lark Transformer


class DSLTransformer(Transformer):
    def __init__(self, context):
        super().__init__()
        self.context = context

    def program(self, items):
        return self.context

    # Terminals
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

    def MODIFIER_TYPE(self, token):
        return str(token)

    def CMP_OP(self, token):
        return str(token)

    def ADD_OP(self, token):
        return str(token)

    def MUL_OP(self, token):
        return str(token)

    # Modes
    def mode_decl(self, items):
        name = items[0]
        props = dict(items[1:])
        mode = Mode(
            name=name,
            speed=props.get("speed"),
            cost=props.get("cost"),
            payload_capacity=props.get("payload_capacity"),
            build_cost=props.get("build_cost", 0.0),
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

    def build_cost_prop(self, items):
        return ("build_cost", float(items[0]))
