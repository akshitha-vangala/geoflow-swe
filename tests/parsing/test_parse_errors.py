# tests/parsing/test_parse_errors.py

import pytest


class TestParseErrors:

    def test_empty_input_raises(self, parse):
        with pytest.raises(Exception):
            parse("")

    def test_missing_closing_brace_raises(self, parse):
        with pytest.raises(Exception):
            parse("""
                mode Car {
                    speed: 60.0
                    cost: 2.0
            """)

    def test_invalid_token_raises(self, parse):
        with pytest.raises(Exception):
            parse("""
                mode @@Invalid {
                    speed: 60.0
                }
            """)

    def test_mode_missing_speed_raises(self, parse):
        with pytest.raises(Exception):
            parse("""
                mode Car { cost: 2.0 }
                node A { loc: (0.0, 0.0)  allows: [Car] }
                node B { loc: (0.1, 0.1)  allows: [Car] }
                mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
            """)

    def test_mission_missing_from_raises(self, parse):
        with pytest.raises(Exception):
            parse("""
                mode Car { speed: 60.0  cost: 2.0 }
                node A { loc: (0.0, 0.0)  allows: [Car] }
                node B { loc: (0.1, 0.1)  allows: [Car] }
                mission M { to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
            """)