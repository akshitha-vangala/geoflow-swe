"""
semantic/base.py
Base class for all semantic checkers.
Every checker gets the full context and a shared reporter.
"""

from .reporter import Reporter


class BaseChecker:
    """
    All checkers inherit from this.
    Provides:
    - self.ctx      → the GeoFlow context (nodes, modes, routes, etc.)
    - self.reporter → shared Reporter instance
    - self.error()  → shorthand for self.reporter.error(checker_name, msg)
    - self.warning()→ shorthand for self.reporter.warning(checker_name, msg)
    - self._node_name() → safely extract string name from Node obj or str
    """

    # Subclasses set this to label their errors clearly
    NAME = "BaseChecker"

    def __init__(self, context, reporter: Reporter):
        self.ctx      = context
        self.reporter = reporter

    def run(self):
        """Override in each subclass to run all checks."""
        raise NotImplementedError

    # ── Convenience wrappers ──────────────────────────────────────────────────

    def error(self, message: str):
        self.reporter.error(self.NAME, message)

    def warning(self, message: str):
        self.reporter.warning(self.NAME, message)

    # ── Shared utilities ──────────────────────────────────────────────────────

    @staticmethod
    def _node_name(x) -> str:
        """
        Normalise a node reference to a plain string.
        The transformer sometimes stores Node objects, sometimes strings.
        """
        if hasattr(x, 'name'):  return str(x.name)
        if isinstance(x, dict): return str(x.get('name', x))
        return str(x)

    @staticmethod
    def _get(obj, key, default=None):
        """Unified attribute/key access for both dicts and objects."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
