"""
Calculator Tool - Strands agent interface (UI agnostic).

This tool wraps the CalculatorService and returns pure text (no UI elements).
"""

import logging

from strands import tool

from .service import CalculatorService

logger = logging.getLogger(__name__)

# Initialize service
_calculator_service = CalculatorService()


@tool
def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression and return the result.

    Supports standard arithmetic operations: addition, subtraction,
    multiplication, division, exponentiation, and parentheses grouping.

    Args:
        expression: A mathematical expression string to evaluate,
                    e.g. '2 + 2', '(3 * 4) / 2', '2 ** 10'.

    Returns:
        str: The result of the evaluated expression, or an error message
             if the expression is invalid.
    """
    return _calculator_service.evaluate(expression)
