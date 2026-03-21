from parser import parser
from transformer import DSLTransformer, Context

text = """
mode fast {
  speed: 10
  cost: 5
  payload_capacity: 100
}

node A {
  loc: (1,2)
}

node B {
  loc: (3,4)
}

mission m1 {
  from: A
  to: B
  start_time: 12:30
}
"""

context = Context()

tree = parser.parse(text)

print("=== PARSE TREE ===")
print(tree.pretty())

DSLTransformer(context).transform(tree)

print("\n=== CONTEXT ===")
print("Modes:", context.modes)
print("Nodes:", context.nodes)
print("Missions:", context.missions)