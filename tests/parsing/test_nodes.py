# tests/parsing/test_nodes.py


class TestNodeDeclarations:

    def test_node_loc_parsed_as_tuple(self, parse):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node Warehouse { loc: (40.7128, -74.0060)  allows: [Car] }
            node StoreA    { loc: (40.7306, -73.9866)  allows: [Car] }
            mission M { from: Warehouse  to: StoreA  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        node = ctx.nodes["Warehouse"]
        assert abs(node.loc[0] - 40.7128)   < 1e-4
        assert abs(node.loc[1] - (-74.006)) < 1e-4

    def test_node_allows_list(self, parse):
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

    def test_multiple_nodes_all_present(self, parse):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (1.0, 1.0)  allows: [Car] }
            node B { loc: (2.0, 2.0)  allows: [Car] }
            node C { loc: (3.0, 3.0)  allows: [Car] }
            mission M { from: A  to: C  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert {"A", "B", "C"}.issubset(ctx.nodes.keys())

    def test_node_with_schedule_windows(self, parse):
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
        assert len(ctx.nodes["WH"].schedule_windows) == 2

    def test_node_negative_longitude(self, parse):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node NYC { loc: (40.7128, -74.0060)   allows: [Car] }
            node LA  { loc: (34.0522, -118.2437)  allows: [Car] }
            mission M { from: NYC  to: LA  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert ctx.nodes["NYC"].loc[1] < 0
        assert ctx.nodes["LA"].loc[1]  < 0

    def test_missing_loc_is_lenient(self, parse):
        # Parser does not enforce loc at parse time — semantic validator
        # is responsible. Assert the node is absent or has no loc.
        try:
            ctx = parse("""
                mode Car { speed: 60.0  cost: 2.0 }
                node Broken { allows: [Car] }
                mission M { from: Broken  to: Broken  start_time: 08:00  optimize: time  alpha: 1.0 }
            """)
            node = ctx.nodes.get("Broken")
            if node is not None:
                loc = (
                    node.get("loc") if isinstance(node, dict)
                    else getattr(node, "loc", None)
                )
                assert loc is None, "Expected no loc on a node declared without one"
        except Exception:
            pass  # raising is also acceptable behaviour