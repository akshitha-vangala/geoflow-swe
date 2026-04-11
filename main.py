import sys
import os

from parser import parser
from transformer import DSLTransformer, Context
from geoflow.graph import Graph
from geoflow.optimizer import optimize_path
from geoflow.simulator import Simulator
from geoflow.renderer import render_map
from geoflow.infrastructure import optimize_infrastructure
from interpreter import Interpreter
from semantic.validator import SemanticValidator
from semantic.reporter  import SemanticError

def main(input_file: str):
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.", file=sys.stderr)
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print("1. Parsing DSL...")
    try:
        tree = parser.parse(content)
    except Exception as e:
        print(f"[GeoFlow Parse Error] {e}", file=sys.stderr)
        return

    ctx = Context()
    try:
        context = DSLTransformer(ctx).transform(tree)
    except Exception as e:
        print(f"[GeoFlow Transform Error] {e}", file=sys.stderr)
        return
    
    try:
        SemanticValidator(context).validate()
    except SemanticError:
        print(f"[GeoFlow Semantic Error] Aborting: {e}", file=sys.stderr)
        return

    print("2. Building Graph...")
    graph = Graph(context)

    # ── v2 Program Block ──────────────────────────────────────────────────────
    if context.program:
        print("3. Running Program Block...")
        interp = Interpreter(context, graph)
        try:
            interp.run(context.program)
        except Exception as e:
            print(f"[GeoFlow Runtime Error] {e}", file=sys.stderr)
            import traceback; traceback.print_exc()
        return

    # ── v1 Legacy Auto Mode ───────────────────────────────────────────────────
    print("3. Optimizing Route...")
    if not context.missions:
        print("No missions or program block found in DSL.", file=sys.stderr)
        return

    if getattr(context, 'hubs_built', None):
        print("\n--- Hubs Generated ---")
        for hub in context.hubs_built:
            print(f"Hub '{hub['name']}' created at {hub['loc']} connecting {hub['connects']}")
        print("----------------------\n")

    mission_name = list(context.missions.keys())[0]
    mission_props = context.missions[mission_name]["props"]

    if "improvement" in mission_props or "limit_budget" in mission_props:
        print(f"Running Path Maker Infrastructure Optimization for {mission_name}...")
        result = optimize_infrastructure(graph, mission_name)
        if result == "NOT POSSIBLE":
            print("NOT POSSIBLE: Target improvement and budget constraints cannot be met.")
            return
        else:
            path = result["path"]
            print(f"Infrastructure Plan Found! Construction Cost: ${result['build_cost']:.2f}")
            for edge in result["built_edges"]:
                print(f" - Build {edge[2]} edge: {edge[0]} -> {edge[1]} for ${edge[3]:.2f}")
    else:
        path = optimize_path(graph, mission_name)

    if not path:
        print(f"No path found for mission {mission_name}!", file=sys.stderr)
        return

    path_nodes = [p[0] for p in path]
    print(f"Optimal Path found: {' -> '.join(path_nodes)}")

    print("4. Simulating Timeline...")
    sim = Simulator(context, graph, path)
    timeline = sim.run()

    print("5. Rendering Map...")
    render_config = list(context.renders.values())[0] if context.renders else {}
    output_filename = render_config.get("export_html", "output.html")
    output_filename = output_filename.strip('"').strip("'")
    output_file = os.path.join("outputs", output_filename)

    render_map(context, graph, path, timeline, output_file)
    print(f"Done! Output saved to {output_file}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main("delivery.gfl")