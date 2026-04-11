# tests/conftest.py
import pytest
from parser import parser
from transformer import DSLTransformer, Context

@pytest.fixture
def parse():
    def _parse(dsl: str) -> Context:
        tree = parser.parse(dsl)
        ctx = Context()
        return DSLTransformer(ctx).transform(tree)
    return _parse

# As you add branches, shared fixtures go here too e.g.:
@pytest.fixture
def simple_ctx(parse):
    return parse("""
        mode Car { speed: 60.0  cost: 2.0 }
        node A { loc: (0.0, 0.0)  allows: [Car] }
        node B { loc: (0.1, 0.1)  allows: [Car] }
        mission M { from: A  to: B  start_time: 08:00  optimize: time  alpha: 1.0 }
    """)