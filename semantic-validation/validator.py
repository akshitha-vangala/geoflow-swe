"""
semantic/validator.py

Orchestrator — runs all checkers in the correct order and
reports results through the shared Reporter.

Order matters:
  1. ScopeChecker   — names must exist before we check types on them
  2. TypeChecker     — values must be right type before checking ranges
  3. ConstraintChecker — ranges/logic checked after types confirmed
  4. ConsistencyChecker — cross-declaration checks last, after all
                          individual declarations are validated

Usage:
    from semantic.validator import SemanticValidator

    validator = SemanticValidator(context)
    validator.validate()   # raises SemanticError if any errors found
"""

from .reporter import Reporter, SemanticError
from .scope_checker       import ScopeChecker
from .type_checker        import TypeChecker
from .constraint_checker  import ConstraintChecker
from .consistency_checker import ConsistencyChecker


class SemanticValidator:

    # Checkers run in this exact order
    _CHECKERS = [
        ScopeChecker,
        TypeChecker,
        ConstraintChecker,
        ConsistencyChecker,
    ]

    def __init__(self, context):
        self.context  = context
        self.reporter = Reporter()

    def validate(self):
        """
        Run all checkers. Print all warnings and errors.
        Raise SemanticError if any errors were found.
        Warnings alone do not raise.
        """
        print("  Running semantic validation...")

        for CheckerClass in self._CHECKERS:
            checker = CheckerClass(self.context, self.reporter)
            try:
                checker.run()
            except Exception as e:
                # A checker itself crashing shouldn't silently swallow the
                # problem — report it and keep going with the other checkers
                self.reporter.error(
                    CheckerClass.NAME,
                    f"Internal checker error: {e}"
                )

        self.reporter.print_all()

        if self.reporter.has_errors():
            raise SemanticError(
                f"Semantic validation failed: {self.reporter.summary()}"
            )

        print(f"  Semantic validation passed. ({self.reporter.summary()})")
