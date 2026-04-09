
"""
GeoFlow v2 Interpreter
Tree-walking interpreter for program { } blocks in GeoFlow DSL scripts.
"""

import os
import sys

from transformer import (
    ProgramBlock, LetStmt, AssignStmt, PrintStmt,
    IfStmt, ForStmt, WhileStmt, ExprStmt,
    BinOp, UnaryOp, MemberAccess, CallExpr,
    Literal, ListLit, VarRef,
    ASTNode,
)
from geoflow.stdlib import (
    GeoflowResult,
    generate_network as _stdlib_generate,
    find_path as _stdlib_find_path,
    build_path as _stdlib_build_path,
    optimize_hub as _stdlib_optimize_hub,
    create_node as _stdlib_create_node,
    suggest_nodes as _stdlib_suggest_nodes,
)


# ─── Exceptions for control flow ─────────────────────────────────────────────

class BreakSignal(Exception): pass
class ContinueSignal(Exception): pass
class ReturnSignal(Exception):
    def __init__(self, value): self.value = value


# ─── Interpreter ─────────────────────────────────────────────────────────────

class Interpreter:
    def __init__(self, context, graph):
        self.context = context
        self.graph   = graph
        self.scope   = {}
        self._render_cache = {}

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self, program: ProgramBlock):
        for stmt in program.stmts:
            self._exec(stmt)

    # ── Statement dispatcher ──────────────────────────────────────────────────

    def _exec(self, node: ASTNode):
        t = type(node)
        if   t is LetStmt:    self._exec_let(node)
        elif t is AssignStmt: self._exec_assign(node)
        elif t is PrintStmt:  self._exec_print(node)
        elif t is IfStmt:     self._exec_if(node)
        elif t is ForStmt:    self._exec_for(node)
        elif t is WhileStmt:  self._exec_while(node)
        elif t is ExprStmt:   self._eval(node.expr)
        else:
            raise RuntimeError(f"[GeoFlow] Unknown statement: {t}")

    def _exec_let(self, node: LetStmt):
        self.scope[node.name] = self._eval(node.expr)

    def _exec_assign(self, node: AssignStmt):
        if node.name not in self.scope:
            raise RuntimeError(f"[GeoFlow] Variable '{node.name}' used before assignment. Use 'let' first.")
        self.scope[node.name] = self._eval(node.expr)

    def _exec_print(self, node: PrintStmt):
        parts = [self._stringify(self._eval(a)) for a in node.args]
        print(" ".join(parts))

    def _exec_if(self, node: IfStmt):
        cond = self._eval(node.cond)
        if self._truthy(cond):
            for s in node.then_body:
                self._exec(s)
        else:
            for s in node.else_body:
                self._exec(s)

    def _exec_for(self, node: ForStmt):
        iterable = self._eval(node.iterable)
        if not hasattr(iterable, '__iter__'):
            raise RuntimeError(f"[GeoFlow] for-in: cannot iterate over {type(iterable)}")
        try:
            for item in iterable:
                self.scope[node.var] = item
                try:
                    for s in node.body:
                        self._exec(s)
                except ContinueSignal:
                    continue
        except BreakSignal:
            pass

    def _exec_while(self, node: WhileStmt):
        try:
            while self._truthy(self._eval(node.cond)):
                try:
                    for s in node.body:
                        self._exec(s)
                except ContinueSignal:
                    continue
        except BreakSignal:
            pass

    # ── Expression evaluator ──────────────────────────────────────────────────

    def _eval(self, node: ASTNode):
        t = type(node)

        if t is Literal:
            return node.value

        if t is ListLit:
            return [self._eval(i) for i in node.items]

        if t is VarRef:
            if node.name in self.scope:
                return self.scope[node.name]
            if node.name in self.context.nodes:   return self.context.nodes[node.name]
            if node.name in self.context.modes:   return self.context.modes[node.name]
            if node.name in self.context.routes:  return self.context.routes[node.name]
            if node.name in self.context.renders: return self.context.renders[node.name]
            if node.name in self.context.missions:return self.context.missions[node.name]
            raise RuntimeError(f"[GeoFlow] Undefined variable: '{node.name}'")

        if t is MemberAccess:
            obj = self._eval(node.obj)
            for field in node.fields:
                if isinstance(obj, dict):
                    obj = obj.get(field)
                elif hasattr(obj, field):
                    obj = getattr(obj, field)
                else:
                    raise RuntimeError(f"[GeoFlow] '{field}' not found on {type(obj)}")
            return obj

        if t is BinOp:
            return self._eval_binop(node)

        if t is UnaryOp:
            return self._eval_unary(node)

        if t is CallExpr:
            return self._eval_call(node)

        raise RuntimeError(f"[GeoFlow] Cannot evaluate node: {t}")

    def _eval_binop(self, node: BinOp):
        op = node.op
        if op == "or":
            return self._truthy(self._eval(node.left)) or self._truthy(self._eval(node.right))
        if op == "and":
            return self._truthy(self._eval(node.left)) and self._truthy(self._eval(node.right))

        left  = self._eval(node.left)
        right = self._eval(node.right)

        ops = {
            "+":  lambda a, b: a + b,
            "-":  lambda a, b: a - b,
            "*":  lambda a, b: a * b,
            "/":  lambda a, b: a / b if b != 0 else float('inf'),
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            "<":  lambda a, b: a < b,
            ">":  lambda a, b: a > b,
            "<=": lambda a, b: a <= b,
            ">=": lambda a, b: a >= b,
        }
        if op not in ops:
            raise RuntimeError(f"[GeoFlow] Unknown operator: {op}")
        try:
            return ops[op](left, right)
        except TypeError:
            if op == "+":
                return str(left) + str(right)
            raise

    def _eval_unary(self, node: UnaryOp):
        val = self._eval(node.operand)
        if node.op == "-":    return -val
        if node.op == "not":  return not self._truthy(val)
        raise RuntimeError(f"[GeoFlow] Unknown unary op: {node.op}")

    # ── Built-in call dispatcher ──────────────────────────────────────────────

    def _eval_call(self, node: CallExpr):
        func = node.func
        kwargs = {k: self._eval(v) for k, v in node.kwargs.items()}

        
        if func == "input":
    # Grammar only allows named args, so input(prompt: "Enter: ") is the
    # only valid form. kwargs values are already evaluated at this point.
            prompt = str(kwargs.get("prompt", ""))
            try:
                return input(prompt)
            except EOFError:
                return ""

        if func == "print":
            parts = [self._stringify(v) for v in kwargs.values()]
            print(" ".join(parts))
            return None

        if func == "float":
            val = list(kwargs.values())[0] if kwargs else 0
            return float(val)

        if func == "int":
            val = list(kwargs.values())[0] if kwargs else 0
            return int(float(val))

        if func == "str":
            val = list(kwargs.values())[0] if kwargs else ""
            return str(val)

        if func == "len":
            val = list(kwargs.values())[0] if kwargs else []
            return len(val) if hasattr(val, "__len__") else 0

        if func == "render":
            return self._eval_render(kwargs)

        if func == "generate_network":
            print("[GeoFlow] Generating random network...")
            return _stdlib_generate(self.context, self.graph, kwargs)

        if func == "find_path":
            print(f"[GeoFlow] Finding path: {kwargs.get('from')} → {kwargs.get('to')}...")
            return _stdlib_find_path(self.context, self.graph, kwargs)

        if func == "build_path":
            print(f"[GeoFlow] Running infrastructure optimizer...")
            return _stdlib_build_path(self.context, self.graph, kwargs)

        if func == "optimize_hub":
            print(f"[GeoFlow] Optimizing hub location...")
            return _stdlib_optimize_hub(self.context, self.graph, kwargs)

        if func == "create_node":
            return _stdlib_create_node(self.context, self.graph, kwargs)

        if func == "suggest_nodes":
            return _stdlib_suggest_nodes(self.context, self.graph, kwargs)

        raise RuntimeError(f"[GeoFlow] Unknown function: '{func}'. Available: input, print, find_path, build_path, optimize_hub, generate_network, render, float, int, str, len")

    def _eval_render(self, kwargs):
        """Handle render(config: ..., output: ...) or render(using: renderName, output: ...)"""
        from geoflow.renderer import render_map
        from geoflow.simulator import Simulator
        from geoflow.optimizer import optimize_path

        using_name  = kwargs.get("using") or kwargs.get("config") or None
        output      = kwargs.get("output") or kwargs.get("to") or None
        path_result = kwargs.get("path") or kwargs.get("result") or None

        # Get render config
        render_config = {}
        if using_name and str(using_name) in self.context.renders:
            render_config = self.context.renders[str(using_name)]

        # Output path
        if not output:
            output = render_config.get("export_html", "output.html")
        output = str(output).strip('"').strip("'")

        # FIX 3: ensure outputs/ directory exists before writing
        os.makedirs("outputs", exist_ok=True)
        output_file = os.path.join("outputs", output)

        # Resolve path from result
        path = []
        if isinstance(path_result, GeoflowResult) and path_result.get("path"):
            path = path_result["path"]
        elif isinstance(path_result, dict) and path_result.get("path"):
            # FIX 4: also handle plain dict results (e.g. from suggest_nodes)
            path = path_result["path"]
        elif self.context.missions:
            m_name = list(self.context.missions.keys())[0]
            path = optimize_path(self.graph, m_name)

        timeline = []
        if path:
            try:
                sim = Simulator(self.context, self.graph, path)
                timeline = sim.run()
            except Exception as e:
                print(f"[GeoFlow] Simulation warning: {e}", file=sys.stderr)

        render_map(self.context, self.graph, path or [], timeline, output_file)
        print(f"[GeoFlow] Rendered → {output_file}")
        return GeoflowResult(possible=True, output=output_file)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _truthy(self, val):
        if val is None:            return False
        if isinstance(val, bool):  return val
        if isinstance(val, (int, float)): return val != 0
        if isinstance(val, str):   return len(val) > 0
        if isinstance(val, (list, dict)): return len(val) > 0
        if isinstance(val, GeoflowResult): return val.get("possible", True)
        return True

    def _stringify(self, val):
        if val is None: return "null"
        if isinstance(val, bool): return "true" if val else "false"
        if isinstance(val, float):
            return str(int(val)) if val == int(val) else str(round(val, 4))
        if isinstance(val, GeoflowResult):
            parts = []
            for k, v in val.items():
                if k not in ("path",):
                    parts.append(f"{k}={v}")
            return "{ " + ", ".join(parts) + " }"
        return str(val)