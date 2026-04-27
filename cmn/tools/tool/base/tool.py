"""
Base tool class for tool architecture.

Tools are thin wrappers around services.
"""

from .service import BaseService


class BaseTool:
    """
    Base class for Strands @tool wrappers.

    Tools are thin wrappers around services that:
    1. Convert parameters to appropriate types
    2. Call the service
    3. Convert results to JSON strings
    4. Handle errors and return error JSON

    Tools must be UI-agnostic and return only JSON strings.
    """

    def __init__(self, service: BaseService):
        """
        Initialize tool with service instance.

        Args:
            service: Service instance to wrap
        """
        self.service = service

    def execute_and_jsonify(self, *args, **kwargs) -> str:
        """
        Execute service and return JSON string.

        This is the pattern all @tool functions should follow:
        1. Call service.execute()
        2. Handle exceptions
        3. Return json.dumps(result)

        Returns:
            JSON string with result or error
        """
        import json
        import logging

        logger = logging.getLogger(self.__class__.__name__)

        try:
            result = self.service.execute(*args, **kwargs)
            return json.dumps(result)

        except ValueError as e:
            logger.error("Validation error: %s", str(e))
            return json.dumps({
                "status": "error",
                "error": str(e),
                "error_type": "validation"
            })

        except Exception as e:
            logger.error("Tool execution failed: %s", str(e), exc_info=True)
            return json.dumps({
                "status": "error",
                "error": f"Execution failed: {str(e)}",
                "error_type": "execution"
            })
