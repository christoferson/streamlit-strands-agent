"""
Calculator tool package.

Provides:
- CalculatorService: Business logic for expression evaluation
- CalculatorTool: BaseTool wrapper with JSON responses and @tool decorator
"""

from .service import CalculatorService
from .tool import CalculatorTool

__all__ = [
    "CalculatorService",
    "CalculatorTool",
]
