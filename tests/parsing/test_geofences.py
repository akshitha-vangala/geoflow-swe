# tests/parsing/test_geofences.py


class TestGeofenceDeclarations:

    def test_geofence_bounds_length(self, parse):
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
        assert len(ctx.geofences["Zone"]["bounds"]) == 4

    def test_geofence_blocks_list(self, parse):
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
        assert "Car"  in gf["blocks"]
        assert "Bike" not in gf["blocks"]

    def test_geofence_activate_at_stored(self, parse):
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

    def test_geofence_reduce_speed_rule(self, parse):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            geofence SlowZone {
                bounds: [(0.0, 0.0), (0.0, 0.2), (0.2, 0.2), (0.2, 0.0)]
                activate_at: 07:00
                rules: { reduce_speed: { Car: 0.5 } }
            }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        rules = ctx.geofences["SlowZone"]["rules"]
        assert "reduce_speed" in rules
        assert rules["reduce_speed"]["Car"] == 0.5

    def test_geofence_increase_cost_rule(self, parse):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            geofence PriceyZone {
                bounds: [(0.0, 0.0), (0.0, 0.2), (0.2, 0.2), (0.2, 0.0)]
                activate_at: 07:00
                rules: { increase_cost: { Car: 2.0 } }
            }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        assert ctx.geofences["PriceyZone"]["rules"]["increase_cost"]["Car"] == 2.0

    def test_geofence_allow_only_rule(self, parse):
        ctx = parse("""
            mode Car  { speed: 60.0  cost: 2.0 }
            mode Bike { speed: 18.0  cost: 0.3 }
            node A { loc: (0.0, 0.0)  allows: [Car, Bike] }
            node B { loc: (0.1, 0.1)  allows: [Car, Bike] }
            geofence EcoZone {
                bounds: [(0.0, 0.0), (0.0, 0.2), (0.2, 0.2), (0.2, 0.0)]
                activate_at: 09:00
                rules: { allow_only: [Bike] }
            }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
        """)
        rules = ctx.geofences["EcoZone"]["rules"]
        assert "Bike" in rules["allow_only"]
        assert "Car"  not in rules["allow_only"]

    def test_multiple_geofences_coexist(self, parse):
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