"""
semantic/
Modular semantic validation for GeoFlow v2.

Public API — the only thing main.py needs to import:

    from semantic.validator import SemanticValidator
    from semantic.reporter  import SemanticError
"""

from .validator import SemanticValidator
from .reporter  import SemanticError

__all__ = ['SemanticValidator', 'SemanticError']
