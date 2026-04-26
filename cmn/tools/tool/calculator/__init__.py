"""
Calculator tool package.

Provides:
- CalculatorService: Business logic for expression evaluation
- CalculatorTool: BaseTool wrapper with JSON responses
- calculator: Strands @tool wrapper function
"""

from .service import CalculatorService
from .tool import CalculatorTool
from .strands_wrapper import calculator

__all__ = [
    "CalculatorService",
    "CalculatorTool",
    "calculator",
]
