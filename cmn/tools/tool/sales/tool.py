"""
Sales Tool - Strands agent interface (UI agnostic).

This tool wraps the SalesService and returns pure data (no UI elements).
"""

import json
import logging

from strands import tool

from .service import SalesService

logger = logging.getLogger(__name__)

# Initialize service
_sales_service = SalesService()


@tool
def sales_data(
    query_type: str,
    year: int,
    month: int = 0,
    category: str = "all",
    region: str = "all",
) -> str:
    """
    Retrieve sales performance data from the database.

    Use get_monthly_sales to get a full year of monthly aggregated data.
    Use get_sales_by_month to drill into a specific month broken down by
    region and category. For year-over-year comparisons call once per year.

    Args:
        query_type: Query mode - 'get_monthly_sales' for a full year of
                    monthly totals, or 'get_sales_by_month' for a single
                    month broken down by region and category.
        year: The year to query, e.g. 2023 or 2024.
        month: Month number 1-12. Required for get_sales_by_month only.
               Pass 0 (default) when using get_monthly_sales.
        category: Product category filter - 'Electronics', 'Accessories',
                  or 'all' (default).
        region: Region filter - 'North', 'South', or 'all' (default).

    Returns:
        str: JSON string containing query results and summary statistics.
    """
    logger.info(
        "sales_data tool called: query_type=%s year=%s month=%s "
        "category=%s region=%s",
        query_type, year, month, category, region,
    )

    try:
        if query_type == "get_monthly_sales":
            result = _sales_service.query_monthly_sales(year, category, region)

        elif query_type == "get_sales_by_month":
            if not month:
                result = {"error": "month (1-12) is required for get_sales_by_month"}
            else:
                result = _sales_service.query_sales_by_month(year, month, category, region)

        else:
            result = {
                "error": (
                    f"Unknown query_type '{query_type}'. "
                    "Use 'get_monthly_sales' or 'get_sales_by_month'."
                )
            }

        return json.dumps(result, default=str)

    except Exception as e:
        logger.error("Sales query failed: %s", str(e), exc_info=True)
        return json.dumps({
            "error": f"Sales query failed: {str(e)}",
            "error_type": "query"
        })
