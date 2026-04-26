"""
Sales data service implementation.

Pure business logic for querying sales data.
"""

import json
from typing import Any, Dict
import duckdb
import pandas as pd
from ..base.service import BaseService


def _safe_int(value) -> int:
    """Convert value to int safely."""
    try:
        if pd.isna(value):
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0


def _df_to_result(df: pd.DataFrame) -> dict:
    """Convert DataFrame to result dict."""
    return {
        "row_count": len(df),
        "columns": list(df.columns),
        "data": df.to_dict(orient="records"),
    }


def _build_mock_sales() -> pd.DataFrame:
    """Build mock sales data."""
    records = [
        # year  month  revenue   units  returns  cogs      region   category
        # 2023
        (2023, 1, 120_000, 400, 20, 72_000, "North", "Electronics"),
        (2023, 1, 85_000, 600, 15, 42_500, "South", "Accessories"),
        (2023, 2, 115_000, 380, 18, 69_000, "North", "Electronics"),
        (2023, 2, 78_000, 550, 12, 39_000, "South", "Accessories"),
        (2023, 3, 130_000, 420, 22, 78_000, "North", "Electronics"),
        (2023, 3, 92_000, 640, 18, 46_000, "South", "Accessories"),
        (2023, 4, 140_000, 460, 25, 84_000, "North", "Electronics"),
        (2023, 4, 98_000, 680, 20, 49_000, "South", "Accessories"),
        (2023, 5, 155_000, 500, 28, 93_000, "North", "Electronics"),
        (2023, 5, 105_000, 720, 22, 52_500, "South", "Accessories"),
        (2023, 6, 160_000, 520, 30, 96_000, "North", "Electronics"),
        (2023, 6, 110_000, 750, 25, 55_000, "South", "Accessories"),
        (2023, 7, 158_000, 510, 29, 94_800, "North", "Electronics"),
        (2023, 7, 108_000, 740, 24, 54_000, "South", "Accessories"),
        (2023, 8, 162_000, 525, 31, 97_200, "North", "Electronics"),
        (2023, 8, 112_000, 760, 26, 56_000, "South", "Accessories"),
        (2023, 9, 170_000, 550, 33, 102_000, "North", "Electronics"),
        (2023, 9, 118_000, 800, 28, 59_000, "South", "Accessories"),
        (2023, 10, 180_000, 580, 35, 108_000, "North", "Electronics"),
        (2023, 10, 125_000, 850, 30, 62_500, "South", "Accessories"),
        (2023, 11, 210_000, 680, 40, 126_000, "North", "Electronics"),
        (2023, 11, 148_000, 1000, 38, 74_000, "South", "Accessories"),
        (2023, 12, 250_000, 800, 50, 150_000, "North", "Electronics"),
        (2023, 12, 175_000, 1200, 45, 87_500, "South", "Accessories"),
        # 2024
        (2024, 1, 125_000, 415, 21, 75_000, "North", "Electronics"),
        (2024, 1, 88_000, 620, 16, 44_000, "South", "Accessories"),
        (2024, 2, 118_000, 390, 19, 70_800, "North", "Electronics"),
        (2024, 2, 80_000, 560, 13, 40_000, "South", "Accessories"),
        (2024, 3, 135_000, 435, 23, 81_000, "North", "Electronics"),
        (2024, 3, 95_000, 660, 19, 47_500, "South", "Accessories"),
        (2024, 4, 132_000, 440, 26, 79_200, "North", "Electronics"),
        (2024, 4, 90_000, 640, 22, 45_000, "South", "Accessories"),
        (2024, 5, 128_000, 420, 30, 76_800, "North", "Electronics"),
        (2024, 5, 88_000, 610, 28, 44_000, "South", "Accessories"),
        (2024, 6, 122_000, 400, 35, 73_200, "North", "Electronics"),
        (2024, 6, 82_000, 580, 32, 41_000, "South", "Accessories"),
        (2024, 7, 145_000, 475, 27, 87_000, "North", "Electronics"),
        (2024, 7, 100_000, 700, 22, 50_000, "South", "Accessories"),
        (2024, 8, 155_000, 505, 29, 93_000, "North", "Electronics"),
        (2024, 8, 108_000, 740, 25, 54_000, "South", "Accessories"),
        (2024, 9, 165_000, 535, 31, 99_000, "North", "Electronics"),
        (2024, 9, 115_000, 780, 27, 57_500, "South", "Accessories"),
        (2024, 10, 175_000, 565, 34, 105_000, "North", "Electronics"),
        (2024, 10, 122_000, 830, 29, 61_000, "South", "Accessories"),
        (2024, 11, 205_000, 665, 39, 123_000, "North", "Electronics"),
        (2024, 11, 144_000, 980, 37, 72_000, "South", "Accessories"),
        (2024, 12, 245_000, 785, 48, 147_000, "North", "Electronics"),
        (2024, 12, 170_000, 1175, 44, 85_000, "South", "Accessories"),
    ]

    df = pd.DataFrame(records, columns=[
        "year", "month", "revenue", "units_sold",
        "returns", "cogs", "region", "category",
    ])

    df["gross_profit"] = (df["revenue"] - df["cogs"]).fillna(0)
    df["profit_margin"] = (
        df["gross_profit"] / df["revenue"] * 100
    ).fillna(0).round(2)
    df["net_revenue"] = (
        df["revenue"] - (df["returns"] * (df["revenue"] / df["units_sold"]))
    ).fillna(0)
    df["month_name"] = pd.to_datetime(df["month"], format="%m").dt.strftime("%B")
    df = df.fillna(0)
    return df


class SalesDataService(BaseService):
    """
    Service for querying sales data.

    Provides methods to query monthly sales and drill down by month.
    """

    def __init__(self):
        """Initialize sales data service."""
        super().__init__(output_dir=None)
        self._sales_df = _build_mock_sales()

    def execute(
        self,
        query_type: str,
        year: int,
        month: int = 0,
        category: str = "all",
        region: str = "all"
    ) -> Dict[str, Any]:
        """
        Execute sales data query.

        Args:
            query_type: 'get_monthly_sales' or 'get_sales_by_month'
            year: Year to query (2023, 2024)
            month: Month number (1-12), required for get_sales_by_month
            category: 'Electronics', 'Accessories', or 'all'
            region: 'North', 'South', or 'all'

        Returns:
            Dict with status and query results
        """
        if query_type == "get_monthly_sales":
            return self._query_monthly_sales(year, category, region)
        elif query_type == "get_sales_by_month":
            if not month:
                return {
                    "status": "error",
                    "error": "month (1-12) is required for get_sales_by_month"
                }
            return self._query_sales_by_month(year, month, category, region)
        else:
            return {
                "status": "error",
                "error": f"Unknown query_type '{query_type}'. Use 'get_monthly_sales' or 'get_sales_by_month'."
            }

    def _query_monthly_sales(self, year: int, category: str, region: str) -> Dict[str, Any]:
        """Query monthly sales for a year."""
        filters = ["year = ?"]
        params = [year]

        if category != "all":
            filters.append("category = ?")
            params.append(category)
        if region != "all":
            filters.append("region = ?")
            params.append(region)

        where = " AND ".join(filters)
        sql = f"""
            SELECT
                month,
                month_name,
                SUM(revenue)                 AS revenue,
                SUM(units_sold)              AS units_sold,
                SUM(returns)                 AS returns,
                SUM(gross_profit)            AS gross_profit,
                ROUND(AVG(profit_margin), 2) AS profit_margin_pct,
                ROUND(SUM(net_revenue), 2)   AS net_revenue
            FROM sales
            WHERE {where}
            GROUP BY month, month_name
            ORDER BY month
        """

        con = duckdb.connect()
        con.register("sales", self._sales_df)
        df = con.execute(sql, params).df().fillna(0)

        if df.empty:
            return {
                "status": "error",
                "error": f"No data for year={year} category={category} region={region}",
                "row_count": 0,
                "data": []
            }

        df["ytd_revenue"] = df["revenue"].cumsum()
        result = _df_to_result(df)
        result.update({
            "status": "success",
            "year": year,
            "category": category,
            "region": region,
            "summary": {
                "total_revenue": _safe_int(df["revenue"].sum()),
                "total_units": _safe_int(df["units_sold"].sum()),
                "total_returns": _safe_int(df["returns"].sum()),
                "avg_monthly_rev": _safe_int(df["revenue"].mean()),
                "best_month": df.loc[df["revenue"].idxmax(), "month_name"],
                "worst_month": df.loc[df["revenue"].idxmin(), "month_name"],
                "total_gross_profit": _safe_int(df["gross_profit"].sum()),
            }
        })
        return result

    def _query_sales_by_month(
        self, year: int, month: int, category: str, region: str
    ) -> Dict[str, Any]:
        """Query sales by month with breakdown."""
        filters = ["year = ?", "month = ?"]
        params = [year, month]

        if category != "all":
            filters.append("category = ?")
            params.append(category)
        if region != "all":
            filters.append("region = ?")
            params.append(region)

        where = " AND ".join(filters)
        sql = f"""
            SELECT
                year, month, month_name, region, category,
                revenue, units_sold, returns, gross_profit,
                profit_margin, ROUND(net_revenue, 2) AS net_revenue
            FROM sales
            WHERE {where}
            ORDER BY region, category
        """

        con = duckdb.connect()
        con.register("sales", self._sales_df)
        df = con.execute(sql, params).df()

        if df.empty:
            return {
                "status": "error",
                "error": f"No data for year={year} month={month} category={category} region={region}",
                "row_count": 0,
                "data": []
            }

        result = _df_to_result(df)
        result.update({
            "status": "success",
            "year": year,
            "month": month,
            "summary": {
                "total_revenue": _safe_int(df["revenue"].sum()),
                "total_units": _safe_int(df["units_sold"].sum()),
                "total_returns": _safe_int(df["returns"].sum()),
                "total_gross_profit": _safe_int(df["gross_profit"].sum()),
            }
        })
        return result
