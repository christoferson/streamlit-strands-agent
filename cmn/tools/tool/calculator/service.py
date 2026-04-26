"""
Calculator service implementation.

Pure business logic for mathematical expression evaluation.
"""

from typing import Any, Dict
from ..base.service import BaseService


class CalculatorService(BaseService):
    """
    Service for evaluating mathematical expressions.

    Safely evaluates arithmetic expressions using a restricted namespace.
    """

    def __init__(self):
        """Initialize calculator service (no output directory needed)."""
        super().__init__(output_dir=None)

    def execute(self, expression: str) -> Dict[str, Any]:
        """
        Evaluate a mathematical expression.

        Args:
            expression: Mathematical expression string (e.g., "2 + 2", "(3 * 4) / 2")

        Returns:
            Dict with status, result, and optional error:
            {
                "status": "success" | "error",
                "result": float (if success),
                "expression": str,
                "error": str (if error)
            }
        """
        if not expression or not expression.strip():
            return {
                "status": "error",
                "error": "Expression cannot be empty",
                "expression": expression
            }

        allowed = {
            "__builtins__": {},
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "pow": pow,
        }

        try:
            result = eval(expression, allowed)
            return {
                "status": "success",
                "result": result,
                "expression": expression
            }
        except ZeroDivisionError:
            return {
                "status": "error",
                "error": "Division by zero",
                "expression": expression
            }
        except (SyntaxError, NameError, TypeError) as e:
            return {
                "status": "error",
                "error": f"Invalid expression: {str(e)}",
                "expression": expression
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Evaluation failed: {str(e)}",
                "expression": expression
            }
