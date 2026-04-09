"""
semantic/reporter.py
Shared error/warning collector used by all checkers.
"""


class SemanticError(Exception):
    """Raised after validation if any errors were collected."""
    pass


class Reporter:
    """
    Collects errors and warnings from all semantic checkers.
    Keeps them separate so we can print all errors at once
    rather than stopping at the first one.
    """

    def __init__(self):
        self._errors   = []
        self._warnings = []

    # ── Recording ─────────────────────────────────────────────────────────────

    def error(self, checker: str, message: str):
        self._errors.append((checker, message))

    def warning(self, checker: str, message: str):
        self._warnings.append((checker, message))

    # ── Reporting ─────────────────────────────────────────────────────────────

    def has_errors(self) -> bool:
        return len(self._errors) > 0

    def print_all(self):
        for checker, msg in self._warnings:
            print(f"  [GeoFlow Warning  | {checker}] {msg}")
        for checker, msg in self._errors:
            print(f"  [GeoFlow Error    | {checker}] {msg}")

    def summary(self) -> str:
        return (
            f"{len(self._errors)} error(s), "
            f"{len(self._warnings)} warning(s)"
        )
