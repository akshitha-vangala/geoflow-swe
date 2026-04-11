# tests/parsing/test_missions.py


class TestMissionDeclarations:

    def test_mission_from_to_parsed(self, parse):
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
        # transformer may store a Node object or a plain string
        frm = props["from"]
        to  = props["to"]
        assert (str(frm) == "Origin" or getattr(frm, "name", None) == "Origin")
        assert (str(to)  == "Dest"   or getattr(to,  "name", None) == "Dest")

    def test_mission_start_time_stored(self, parse):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            mission M { from: A  to: B  start_time: 14:30  optimize: time  alpha: 1.0 }
        """)
        assert ctx.missions["M"]["props"]["start_time"] == "14:30"

    def test_mission_alpha_stored(self, parse):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 0.3 }
        """)
        assert ctx.missions["M"]["props"]["alpha"] == 0.3

    def test_mission_optimize_cost(self, parse):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            mission M { from: A  to: B  start_time: 08:00  optimize: cost  alpha: 0.0 }
        """)
        assert ctx.missions["M"]["props"]["optimize"] == "cost"

    def test_mission_improvement_and_budget(self, parse):
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
        assert props.get("improvement")  == 20
        assert props.get("limit_budget") == 100000