from strands import tool


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
    # Restrict eval to safe math operations only
    allowed = {
        "__builtins__": {},
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "pow": pow,
    }

    try:
        result = eval(expression, allowed)  # noqa: S307
        return str(result)
    except ZeroDivisionError:
        return "Error: division by zero."
    except Exception as e:
        return f"Error evaluating expression: {e}"