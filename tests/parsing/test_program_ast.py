# tests/parsing/test_program_ast.py
#
# Verifies that DSLTransformer produces the correct AST node types
# inside context.program. No interpreter is executed here.

from transformer import (
    ProgramBlock, LetStmt, AssignStmt, PrintStmt,
    IfStmt, ForStmt, WhileStmt, ExprStmt,
    BinOp, MemberAccess, CallExpr,
)

# Minimal boilerplate prepended to every program-block snippet.
_PREAMBLE = """
    mode Car { speed: 60.0  cost: 2.0 }
    node A { loc: (0.0, 0.0)  allows: [Car] }
    node B { loc: (0.1, 0.1)  allows: [Car] }
"""


class TestProgramBlockAST:

    def test_program_block_stored_as_program_block(self, parse):
        ctx = parse(_PREAMBLE + """
            program {
                let x = 1
            }
        """)
        assert ctx.program is not None
        assert isinstance(ctx.program, ProgramBlock)

    def test_let_stmt_name_and_type(self, parse):
        ctx = parse(_PREAMBLE + """
            program {
                let answer = 42
            }
        """)
        let = ctx.program.stmts[0]
        assert isinstance(let, LetStmt)
        assert let.name == "answer"

    def test_assign_stmt_type(self, parse):
        ctx = parse(_PREAMBLE + """
            program {
                let x = 0
                x = 99
            }
        """)
        stmts = ctx.program.stmts
        assert isinstance(stmts[0], LetStmt)
        assert isinstance(stmts[1], AssignStmt)
        assert stmts[1].name == "x"

    def test_print_stmt_present(self, parse):
        ctx = parse(_PREAMBLE + """
            program {
                print("hello")
            }
        """)
        assert any(isinstance(s, PrintStmt) for s in ctx.program.stmts)

    def test_if_stmt_present(self, parse):
        ctx = parse(_PREAMBLE + """
            program {
                let x = 1
                if x > 0 {
                    print("positive")
                }
            }
        """)
        assert any(isinstance(s, IfStmt) for s in ctx.program.stmts)

    def test_if_else_bodies_populated(self, parse):
        ctx = parse(_PREAMBLE + """
            program {
                let x = 1
                if x > 0 {
                    print("yes")
                } else {
                    print("no")
                }
            }
        """)
        if_stmt = next(s for s in ctx.program.stmts if isinstance(s, IfStmt))
        assert len(if_stmt.then_body) >= 1
        assert len(if_stmt.else_body) >= 1

    def test_for_stmt_var_and_body(self, parse):
        ctx = parse(_PREAMBLE + """
            program {
                let items = [1, 2, 3]
                for v in items {
                    print(v)
                }
            }
        """)
        for_stmt = next(s for s in ctx.program.stmts if isinstance(s, ForStmt))
        assert for_stmt.var == "v"
        assert len(for_stmt.body) >= 1

    def test_while_stmt_present(self, parse):
        ctx = parse(_PREAMBLE + """
            program {
                let i = 0
                while i < 3 {
                    i = i + 1
                }
            }
        """)
        assert any(isinstance(s, WhileStmt) for s in ctx.program.stmts)

    def test_call_expr_inside_expr_stmt(self, parse):
        ctx = parse(_PREAMBLE + """
            program {
                find_path(from: A, to: B, alpha: 0.5, start_time: "08:00")
            }
        """)
        assert any(
            isinstance(s, ExprStmt) and isinstance(s.expr, CallExpr)
            for s in ctx.program.stmts
        )

    def test_binop_operator_stored(self, parse):
        ctx = parse(_PREAMBLE + """
            program {
                let total = 10 + 5
            }
        """)
        let = ctx.program.stmts[0]
        assert isinstance(let, LetStmt)
        assert isinstance(let.expr, BinOp)
        assert let.expr.op == "+"

    def test_member_access_fields(self, parse):
        ctx = parse(_PREAMBLE + """
            program {
                let r = find_path(from: A, to: B, alpha: 0.5, start_time: "08:00")
                let t = r.time
            }
        """)
        let_t = ctx.program.stmts[1]
        assert isinstance(let_t, LetStmt)
        assert isinstance(let_t.expr, MemberAccess)
        assert "time" in let_t.expr.fields

    def test_nested_if_inside_for(self, parse):
        ctx = parse(_PREAMBLE + """
            program {
                let items = [1, 2, 3]
                for v in items {
                    if v > 1 {
                        print(v)
                    }
                }
            }
        """)
        for_stmt = next(s for s in ctx.program.stmts if isinstance(s, ForStmt))
        assert any(isinstance(s, IfStmt) for s in for_stmt.body)