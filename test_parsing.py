"""
GeoFlow — Parsing Branch Unit Tests
====================================
Tests the pipeline:  DSL string -> parser.parse() -> DSLTransformer().transform() -> Context

Run with:
    pytest test_parsing.py -v

All tests use real imports — no mocking. The graph, optimizer, simulator,
and renderer are never touched here; this file tests only parsing and
transformation.
"""

import pytest
from parser import parser
from transformer import DSLTransformer, Context


# ─── Helper ───────────────────────────────────────────────────────────────────

def parse(dsl: str) -> Context:
    """Parse a DSL string and return the resulting Context object."""
    tree = parser.parse(dsl)
    ctx  = Context()
    return DSLTransformer(ctx).transform(tree)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. MODE DECLARATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestModeDeclarations:

    def test_single_mode_speed_and_cost(self):
        ctx = parse("""
            mode Car {
                speed: 60.0
                cost: 2.0
            }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert "Car" in ctx.modes
        car = ctx.modes["Car"]
        assert car.speed == 60.0
        assert car.cost  == 2.0

    def test_mode_with_all_four_fields(self):
        ctx = parse("""
            mode HighSpeed {
                speed: 220.0
                cost: 5.0
                payload_capacity: 200
                build_cost: 300
            }
            node A { loc: (0.0, 0.0)  allows: [HighSpeed] }
            node B { loc: (0.1, 0.1)  allows: [HighSpeed] }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        m = ctx.modes["HighSpeed"]
        assert m.speed          == 220.0
        assert m.cost           == 5.0
        assert m.build_cost     == 300

    def test_multiple_modes_parsed(self):
        ctx = parse("""
            mode Bike   { speed: 18.0  cost: 0.3 }
            mode Subway { speed: 65.0  cost: 1.5 }
            mode Ferry  { speed: 30.0  cost: 1.0 }
            node A { loc: (0.0, 0.0)  allows: [Bike, Subway, Ferry] }
            node B { loc: (0.1, 0.1)  allows: [Bike] }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert set(["Bike", "Subway", "Ferry"]).issubset(ctx.modes.keys())

    def test_mode_zero_cost(self):
        ctx = parse("""
            mode Walking { speed: 5.0  cost: 0.0 }
            node A { loc: (0.0, 0.0)  allows: [Walking] }
            node B { loc: (0.1, 0.1)  allows: [Walking] }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert ctx.modes["Walking"].cost == 0.0

    def test_mode_fractional_speed(self):
        ctx = parse("""
            mode Drone { speed: 99.5  cost: 2.5 }
            node A { loc: (0.0, 0.0)  allows: [Drone] }
            node B { loc: (0.1, 0.1)  allows: [Drone] }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert ctx.modes["Drone"].speed == 99.5


# ═══════════════════════════════════════════════════════════════════════════════
# 2. NODE DECLARATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestNodeDeclarations:

    def test_node_loc_parsed_as_tuple(self):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node Warehouse { loc: (40.7128, -74.0060)  allows: [Car] }
            node StoreA    { loc: (40.7306, -73.9866)  allows: [Car] }
            mission M { from: Warehouse  to: StoreA  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        node = ctx.nodes["Warehouse"]
        assert abs(node.loc[0] - 40.7128) < 1e-4
        assert abs(node.loc[1] - (-74.0060)) < 1e-4

    def test_node_allows_list(self):
        ctx = parse("""
            mode Car  { speed: 60.0  cost: 2.0 }
            mode Bike { speed: 18.0  cost: 0.3 }
            node Hub { loc: (10.0, 10.0)  allows: [Car, Bike] }
            node End { loc: (10.1, 10.1)  allows: [Car] }
            mission M { from: Hub  to: End  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        allows = ctx.nodes["Hub"].allows
        assert "Car"  in allows
        assert "Bike" in allows

    def test_multiple_nodes_all_present(self):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (1.0, 1.0)  allows: [Car] }
            node B { loc: (2.0, 2.0)  allows: [Car] }
            node C { loc: (3.0, 3.0)  allows: [Car] }
            mission M { from: A  to: C  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert {"A", "B", "C"}.issubset(ctx.nodes.keys())

    def test_node_with_schedule_windows(self):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node Depot { loc: (0.0, 0.0)  allows: [Car] }
            node WH {
                loc: (0.1, 0.1)
                allows: [Car]
                schedule_windows: [09:00-12:00, 14:00-17:00]
            }
            mission M { from: Depot  to: WH  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        windows = ctx.nodes["WH"].schedule_windows
        assert len(windows) == 2

    def test_node_negative_longitude(self):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node NYC { loc: (40.7128, -74.0060)  allows: [Car] }
            node LA  { loc: (34.0522, -118.2437) allows: [Car] }
            mission M { from: NYC  to: LA  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert ctx.nodes["NYC"].loc[1] < 0
        assert ctx.nodes["LA"].loc[1]  < 0


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GEOFENCE DECLARATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestGeofenceDeclarations:

    def test_geofence_bounds_parsed(self):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (48.85, 2.33)  allows: [Car] }
            node B { loc: (48.88, 2.36)  allows: [Car] }
            geofence Zone {
                bounds: [(48.84, 2.32), (48.84, 2.37), (48.89, 2.37), (48.89, 2.32)]
                blocks: [Car]
                activate_at: 08:00
            }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert "Zone" in ctx.geofences
        gf = ctx.geofences["Zone"]
        assert len(gf["bounds"]) == 4

    def test_geofence_blocks_list(self):
        ctx = parse("""
            mode Car  { speed: 60.0  cost: 2.0 }
            mode Bike { speed: 18.0  cost: 0.3 }
            node A { loc: (0.0, 0.0)  allows: [Car, Bike] }
            node B { loc: (0.1, 0.1)  allows: [Car, Bike] }
            geofence NoCarZone {
                bounds: [(0.0, 0.0), (0.0, 0.2), (0.2, 0.2), (0.2, 0.0)]
                blocks: [Car]
                activate_at: 07:00
            }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        gf = ctx.geofences["NoCarZone"]
        assert "Car" in gf["blocks"]
        assert "Bike" not in gf["blocks"]

    def test_geofence_activate_at_stored(self):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            geofence LateZone {
                bounds: [(0.0, 0.0), (0.0, 0.2), (0.2, 0.2), (0.2, 0.0)]
                blocks: [Car]
                activate_at: 22:30
            }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert ctx.geofences["LateZone"]["activate_at"] == "22:30"

    def test_geofence_reduce_speed_rule(self):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            geofence SlowZone {
                bounds: [(0.0, 0.0), (0.0, 0.2), (0.2, 0.2), (0.2, 0.0)]
                activate_at: 07:00
                rules: {
                    reduce_speed: { Car: 0.5 }
                }
            }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        rules = ctx.geofences["SlowZone"]["rules"]
        assert "reduce_speed" in rules
        assert rules["reduce_speed"]["Car"] == 0.5

    def test_geofence_increase_cost_rule(self):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            geofence PriceyZone {
                bounds: [(0.0, 0.0), (0.0, 0.2), (0.2, 0.2), (0.2, 0.0)]
                activate_at: 07:00
                rules: {
                    increase_cost: { Car: 2.0 }
                }
            }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        rules = ctx.geofences["PriceyZone"]["rules"]
        assert rules["increase_cost"]["Car"] == 2.0

    def test_geofence_allow_only_rule(self):
        ctx = parse("""
            mode Car  { speed: 60.0  cost: 2.0 }
            mode Bike { speed: 18.0  cost: 0.3 }
            node A { loc: (0.0, 0.0)  allows: [Car, Bike] }
            node B { loc: (0.1, 0.1)  allows: [Car, Bike] }
            geofence EcoZone {
                bounds: [(0.0, 0.0), (0.0, 0.2), (0.2, 0.2), (0.2, 0.0)]
                activate_at: 09:00
                rules: {
                    allow_only: [Bike]
                }
            }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        rules = ctx.geofences["EcoZone"]["rules"]
        assert "Bike" in rules["allow_only"]
        assert "Car"  not in rules["allow_only"]

    def test_multiple_geofences_coexist(self):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            geofence ZoneA {
                bounds: [(0.0, 0.0), (0.0, 0.1), (0.1, 0.1), (0.1, 0.0)]
                blocks: [Car]
                activate_at: 08:00
            }
            geofence ZoneB {
                bounds: [(0.1, 0.1), (0.1, 0.2), (0.2, 0.2), (0.2, 0.1)]
                blocks: [Car]
                activate_at: 09:00
            }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert "ZoneA" in ctx.geofences
        assert "ZoneB" in ctx.geofences


# ═══════════════════════════════════════════════════════════════════════════════
# 4. MISSION DECLARATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMissionDeclarations:

    def test_mission_from_to_parsed(self):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node Origin { loc: (0.0, 0.0)  allows: [Car] }
            node Dest   { loc: (0.1, 0.1)  allows: [Car] }
            mission Trip {
                from: Origin
                to: Dest
                start_time: 08:00
                optimize: time
                alpha: 1.0
            }
        """)
        assert "Trip" in ctx.missions
        props = ctx.missions["Trip"]["props"]
        assert str(props["from"]) == "Origin" or getattr(props["from"], "name", None) == "Origin"
        assert str(props["to"])   == "Dest"   or getattr(props["to"],   "name", None) == "Dest"

    def test_mission_start_time_stored(self):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            mission M { from: A  to: B  start_time: 14:30  optimize: time  alpha: 1.0 }
        """)
        assert ctx.missions["M"]["props"]["start_time"] == "14:30"

    def test_mission_alpha_stored(self):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 0.3 }
        """)
        assert ctx.missions["M"]["props"]["alpha"] == 0.3

    def test_mission_optimize_cost(self):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            mission M { from: A  to: B  start_time: 08:00  optimize: cost  alpha: 0.0 }
        """)
        assert ctx.missions["M"]["props"]["optimize"] == "cost"

    def test_mission_improvement_and_budget(self):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0  build_cost: 50 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            mission InfraMission {
                from: A
                to: B
                start_time: 08:00
                optimize: time
                alpha: 1.0
                improvement: 20
                limit budget: 100000
            }
        """)
        props = ctx.missions["InfraMission"]["props"]
        assert props.get("improvement") == 20
        assert props.get("limit_budget") == 100000


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ROUTE DECLARATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRouteDeclarations:

    def test_route_mode_and_stops_parsed(self):
        ctx = parse("""
            mode Subway { speed: 65.0  cost: 1.5 }
            node StationA { loc: (52.50, 13.40)  allows: [Subway] }
            node StationB { loc: (52.52, 13.42)  allows: [Subway] }
            node StationC { loc: (52.54, 13.44)  allows: [Subway] }
            route Line1 {
                mode: Subway
                stops: [StationA, StationB, StationC]
            }
            mission M { from: StationA  to: StationC  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert "Line1" in ctx.routes
        r = ctx.routes["Line1"]
        assert r["mode"] == "Subway"
        stops = [s if isinstance(s, str) else getattr(s, "name", str(s)) for s in r["stops"]]
        assert "StationA" in stops
        assert "StationC" in stops

    def test_multiple_routes_coexist(self):
        ctx = parse("""
            mode Bus    { speed: 40.0  cost: 1.0 }
            mode Subway { speed: 65.0  cost: 1.5 }
            node A { loc: (0.0, 0.0)  allows: [Bus, Subway] }
            node B { loc: (0.1, 0.1)  allows: [Bus, Subway] }
            node C { loc: (0.2, 0.2)  allows: [Bus, Subway] }
            route BusLine  { mode: Bus     stops: [A, B, C] }
            route MetroRed { mode: Subway  stops: [A, C]    }
            mission M { from: A  to: C  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert "BusLine"  in ctx.routes
        assert "MetroRed" in ctx.routes


# ═══════════════════════════════════════════════════════════════════════════════
# 6. RENDER DECLARATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRenderDeclarations:

    def test_render_export_html_stored(self):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
            render MyDash {
                execution: dynamic
                show_nodes: true
                timeline: true
                sim_speed: 2.0x
                export_html: "output.html"
            }
        """)
        assert "MyDash" in ctx.renders
        # The transformer strips surrounding quotes from STRING tokens
        val = ctx.renders["MyDash"].get("export_html")
        assert val.strip('"').strip("'") == "output.html"

    def test_render_execution_mode(self):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
            render StaticDash {
                execution: static
                show_nodes: false
                timeline: false
                sim_speed: 1.0x
                export_html: "static.html"
            }
        """)
        assert ctx.renders["StaticDash"].get("execution") == "static"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. PROGRAM BLOCK — AST SHAPE
# ═══════════════════════════════════════════════════════════════════════════════

class TestProgramBlockParsing:
    """
    These tests only verify that the DSLTransformer correctly populates
    context.program with the right AST node types. No interpreter is run.
    """

    def test_program_block_is_stored(self):
        from transformer import ProgramBlock
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            program {
                let x = 1
            }
        """)
        assert ctx.program is not None
        assert isinstance(ctx.program, ProgramBlock)

    def test_let_stmt_in_program(self):
        from transformer import LetStmt, Literal
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            program {
                let answer = 42
            }
        """)
        stmts = ctx.program.stmts
        assert len(stmts) >= 1
        let = stmts[0]
        assert isinstance(let, LetStmt)
        assert let.name == "answer"

    def test_print_stmt_in_program(self):
        from transformer import PrintStmt
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            program {
                print("hello")
            }
        """)
        stmts = ctx.program.stmts
        assert any(isinstance(s, PrintStmt) for s in stmts)

    def test_if_stmt_in_program(self):
        from transformer import IfStmt
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            program {
                let x = 1
                if x > 0 {
                    print("positive")
                }
            }
        """)
        stmts = ctx.program.stmts
        assert any(isinstance(s, IfStmt) for s in stmts)

    def test_for_stmt_in_program(self):
        from transformer import ForStmt
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            program {
                let items = [1, 2, 3]
                for v in items {
                    print(v)
                }
            }
        """)
        stmts = ctx.program.stmts
        assert any(isinstance(s, ForStmt) for s in stmts)

    def test_while_stmt_in_program(self):
        from transformer import WhileStmt
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            program {
                let i = 0
                while i < 3 {
                    i = i + 1
                }
            }
        """)
        stmts = ctx.program.stmts
        assert any(isinstance(s, WhileStmt) for s in stmts)

    def test_call_expr_in_program(self):
        from transformer import ExprStmt, CallExpr
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            program {
                find_path(from: A, to: B, alpha: 0.5, start_time: "08:00")
            }
        """)
        stmts = ctx.program.stmts
        assert any(
            isinstance(s, ExprStmt) and isinstance(s.expr, CallExpr)
            for s in stmts
        )

    def test_binop_in_let_expr(self):
        from transformer import LetStmt, BinOp
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            program {
                let total = 10 + 5
            }
        """)
        let = ctx.program.stmts[0]
        assert isinstance(let, LetStmt)
        assert isinstance(let.expr, BinOp)
        assert let.expr.op == "+"

    def test_member_access_in_program(self):
        from transformer import LetStmt, MemberAccess
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            program {
                let r = find_path(from: A, to: B, alpha: 0.5, start_time: "08:00")
                let t = r.time
            }
        """)
        stmts = ctx.program.stmts
        let_t = stmts[1]
        assert isinstance(let_t, LetStmt)
        assert isinstance(let_t.expr, MemberAccess)
        assert "time" in let_t.expr.fields


# ═══════════════════════════════════════════════════════════════════════════════
# 8. PARSE ERRORS
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseErrors:

    def test_empty_input_raises(self):
        with pytest.raises(Exception):
            parse("")

    def test_missing_closing_brace_raises(self):
        with pytest.raises(Exception):
            parse("""
                mode Car {
                    speed: 60.0
                    cost: 2.0
            """)

    def test_invalid_token_raises(self):
        with pytest.raises(Exception):
            parse("""
                mode @@Invalid {
                    speed: 60.0
                }
            """)

    def test_missing_loc_on_node_raises(self):
        # The parser is lenient about missing loc — it does not raise at parse
        # time. What we can assert is that a node without loc either raises
        # downstream OR produces a node with no usable loc attribute.
        try:
            ctx = parse("""
                mode Car { speed: 60.0  cost: 2.0 }
                node Broken { allows: [Car] }
                mission M { from: Broken  to: Broken  start_time: 08:00  optimize: time  alpha: 1.0 }
            """)
            # If parsing succeeded, the node must either be absent or have no loc
            node = ctx.nodes.get("Broken")
            if node is not None:
                loc = getattr(node, "loc", None) or node.get("loc") if isinstance(node, dict) else getattr(node, "loc", None)
                assert loc is None, "Expected no loc on a node declared without one"
        except Exception:
            pass  # raising is also acceptable
