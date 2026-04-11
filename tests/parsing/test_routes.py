# tests/parsing/test_routes.py


class TestRouteDeclarations:

    def test_route_mode_and_stops_parsed(self, parse):
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

    def test_route_stop_count(self, parse):
        ctx = parse("""
            mode Bus { speed: 40.0  cost: 1.0 }
            node A { loc: (0.0, 0.0)  allows: [Bus] }
            node B { loc: (0.1, 0.1)  allows: [Bus] }
            node C { loc: (0.2, 0.2)  allows: [Bus] }
            node D { loc: (0.3, 0.3)  allows: [Bus] }
            route R { mode: Bus  stops: [A, B, C, D] }
            mission M { from: A  to: D  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert len(ctx.routes["R"]["stops"]) == 4

    def test_multiple_routes_coexist(self, parse):
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
        assert ctx.routes["BusLine"]["mode"]  == "Bus"
        assert ctx.routes["MetroRed"]["mode"] == "Subway"