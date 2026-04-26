"""
Calculator tool implementation.

Thin wrapper around CalculatorService that extends BaseTool.
"""

from ..base.tool import BaseTool
from .service import CalculatorService
from strands import tool


class CalculatorTool(BaseTool):
    """
    Calculator tool that evaluates mathematical expressions.

    This is a thin wrapper around CalculatorService that:
    1. Converts parameters to appropriate types
    2. Calls the service
    3. Converts results to JSON strings
    4. Handles errors
    """

    def __init__(self):
        """Initialize calculator tool with service."""
        service = CalculatorService()
        super().__init__(service)

    @tool(name="calculator")
    def execute(self, expression: str) -> str:
        """
        Evaluate a mathematical expression.

        Args:
            expression: Mathematical expression string (e.g., "2 + 2")

        Returns:
            JSON string with result or error
        """
        return self.execute_and_jsonify(expression=expression)
