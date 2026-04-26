"""
Sales data tool implementation.

Thin wrapper around SalesDataService that extends BaseTool.
"""

from strands import tool
from ..base.tool import BaseTool
from .service import SalesDataService


class SalesDataTool(BaseTool):
    """
    Sales data tool that queries sales information.

    This is a thin wrapper around SalesDataService that:
    1. Converts parameters to appropriate types
    2. Calls the service
    3. Converts results to JSON strings
    4. Handles errors
    """

    def __init__(self):
        """Initialize sales data tool with service."""
        service = SalesDataService()
        super().__init__(service)

    @tool(name="sales_data")
    def execute(
        self,
        query_type: str,
        year: int,
        month: int = 0,
        category: str = "all",
        region: str = "all"
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
            JSON string with query results and summary statistics
        """
        return self.execute_and_jsonify(
            query_type=query_type,
            year=year,
            month=month,
            category=category,
            region=region
        )
