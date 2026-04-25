"""
Calculator Tool Package - Pure business logic and framework-agnostic tool.

This package provides:
- CalculatorService: Mathematical expression evaluation logic (no UI)
- calculator: Strands @tool wrapper that returns text

NO UI DEPENDENCIES - can be used from any interface.
"""

from .service import CalculatorService
from .tool import calculator

__all__ = [
    "CalculatorService",
    "calculator",
]
