# tests/parsing/test_modes.py


class TestModeDeclarations:

    def test_single_mode_speed_and_cost(self, parse):
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
        assert ctx.modes["Car"].speed == 60.0
        assert ctx.modes["Car"].cost  == 2.0

    def test_mode_with_all_four_fields(self, parse):
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
        assert m.speed      == 220.0
        assert m.cost       == 5.0
        assert m.build_cost == 300

    def test_multiple_modes_all_present(self, parse):
        ctx = parse("""
            mode Bike   { speed: 18.0  cost: 0.3 }
            mode Subway { speed: 65.0  cost: 1.5 }
            mode Ferry  { speed: 30.0  cost: 1.0 }
            node A { loc: (0.0, 0.0)  allows: [Bike, Subway, Ferry] }
            node B { loc: (0.1, 0.1)  allows: [Bike] }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert {"Bike", "Subway", "Ferry"}.issubset(ctx.modes.keys())

    def test_mode_zero_cost(self, parse):
        ctx = parse("""
            mode Walking { speed: 5.0  cost: 0.0 }
            node A { loc: (0.0, 0.0)  allows: [Walking] }
            node B { loc: (0.1, 0.1)  allows: [Walking] }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert ctx.modes["Walking"].cost == 0.0

    def test_mode_fractional_speed(self, parse):
        ctx = parse("""
            mode Drone { speed: 99.5  cost: 2.5 }
            node A { loc: (0.0, 0.0)  allows: [Drone] }
            node B { loc: (0.1, 0.1)  allows: [Drone] }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert ctx.modes["Drone"].speed == 99.5