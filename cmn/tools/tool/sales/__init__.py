"""
Sales Tool Package - Pure business logic and framework-agnostic tool.

This package provides:
- SalesService: Sales data query logic (no UI)
- sales_data: Strands @tool wrapper that returns data

NO UI DEPENDENCIES - can be used from any interface.
"""

from .service import SalesService
from .tool import sales_data

__all__ = [
    "SalesService",
    "sales_data",
]
