# tests/parsing/test_renders.py


class TestRenderDeclarations:

    def test_render_present_in_context(self, parse):
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

    def test_render_export_html_strips_quotes(self, parse):
        # Transformer strips surrounding quotes from STRING tokens.
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
        val = ctx.renders["MyDash"].get("export_html")
        assert val.strip('"').strip("'") == "output.html"

    def test_render_execution_dynamic(self, parse):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
            render D {
                execution: dynamic
                show_nodes: true
                timeline: true
                sim_speed: 1.0x
                export_html: "d.html"
            }
        """)
        assert ctx.renders["D"].get("execution") == "dynamic"

    def test_render_execution_static(self, parse):
        ctx = parse("""
            mode Car { speed: 60.0  cost: 2.0 }
            node A { loc: (0.0, 0.0)  allows: [Car] }
            node B { loc: (0.1, 0.1)  allows: [Car] }
            mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
            render S {
                execution: static
                show_nodes: false
                timeline: false
                sim_speed: 1.0x
                export_html: "s.html"
            }
        """)
        assert ctx.renders["S"].get("execution") == "static"