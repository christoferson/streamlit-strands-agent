import json
import logging

import duckdb
import pandas as pd
from strands import tool

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_int(value) -> int:
    try:
        if pd.isna(value):
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0


def _df_to_result(df: pd.DataFrame) -> dict:
    return {
        "row_count": len(df),
        "columns":   list(df.columns),
        "data":      df.to_dict(orient="records"),
    }


# ── Mock Data ─────────────────────────────────────────────────────────────────

def _build_mock_sales() -> pd.DataFrame:
    records = [
        # year  month  revenue   units  returns  cogs      region   category
        # ── 2023 ──────────────────────────────────────────────────────────────
        (2023,  1,  120_000,  400,  20,  72_000,  "North",  "Electronics"),
        (2023,  1,   85_000,  600,  15,  42_500,  "South",  "Accessories"),
        (2023,  2,  115_000,  380,  18,  69_000,  "North",  "Electronics"),
        (2023,  2,   78_000,  550,  12,  39_000,  "South",  "Accessories"),
        (2023,  3,  130_000,  420,  22,  78_000,  "North",  "Electronics"),
        (2023,  3,   92_000,  640,  18,  46_000,  "South",  "Accessories"),
        (2023,  4,  140_000,  460,  25,  84_000,  "North",  "Electronics"),
        (2023,  4,   98_000,  680,  20,  49_000,  "South",  "Accessories"),
        (2023,  5,  155_000,  500,  28,  93_000,  "North",  "Electronics"),
        (2023,  5,  105_000,  720,  22,  52_500,  "South",  "Accessories"),
        (2023,  6,  160_000,  520,  30,  96_000,  "North",  "Electronics"),
        (2023,  6,  110_000,  750,  25,  55_000,  "South",  "Accessories"),
        (2023,  7,  158_000,  510,  29,  94_800,  "North",  "Electronics"),
        (2023,  7,  108_000,  740,  24,  54_000,  "South",  "Accessories"),
        (2023,  8,  162_000,  525,  31,  97_200,  "North",  "Electronics"),
        (2023,  8,  112_000,  760,  26,  56_000,  "South",  "Accessories"),
        (2023,  9,  170_000,  550,  33, 102_000,  "North",  "Electronics"),
        (2023,  9,  118_000,  800,  28,  59_000,  "South",  "Accessories"),
        (2023, 10,  180_000,  580,  35, 108_000,  "North",  "Electronics"),
        (2023, 10,  125_000,  850,  30,  62_500,  "South",  "Accessories"),
        (2023, 11,  210_000,  680,  40, 126_000,  "North",  "Electronics"),
        (2023, 11,  148_000, 1000,  38,  74_000,  "South",  "Accessories"),
        (2023, 12,  250_000,  800,  50, 150_000,  "North",  "Electronics"),
        (2023, 12,  175_000, 1200,  45,  87_500,  "South",  "Accessories"),
        # ── 2024 ──────────────────────────────────────────────────────────────
        (2024,  1,  125_000,  415,  21,  75_000,  "North",  "Electronics"),
        (2024,  1,   88_000,  620,  16,  44_000,  "South",  "Accessories"),
        (2024,  2,  118_000,  390,  19,  70_800,  "North",  "Electronics"),
        (2024,  2,   80_000,  560,  13,  40_000,  "South",  "Accessories"),
        (2024,  3,  135_000,  435,  23,  81_000,  "North",  "Electronics"),
        (2024,  3,   95_000,  660,  19,  47_500,  "South",  "Accessories"),
        (2024,  4,  132_000,  440,  26,  79_200,  "North",  "Electronics"),
        (2024,  4,   90_000,  640,  22,  45_000,  "South",  "Accessories"),
        (2024,  5,  128_000,  420,  30,  76_800,  "North",  "Electronics"),
        (2024,  5,   88_000,  610,  28,  44_000,  "South",  "Accessories"),
        (2024,  6,  122_000,  400,  35,  73_200,  "North",  "Electronics"),
        (2024,  6,   82_000,  580,  32,  41_000,  "South",  "Accessories"),
        (2024,  7,  145_000,  475,  27,  87_000,  "North",  "Electronics"),
        (2024,  7,  100_000,  700,  22,  50_000,  "South",  "Accessories"),
        (2024,  8,  155_000,  505,  29,  93_000,  "North",  "Electronics"),
        (2024,  8,  108_000,  740,  25,  54_000,  "South",  "Accessories"),
        (2024,  9,  165_000,  535,  31,  99_000,  "North",  "Electronics"),
        (2024,  9,  115_000,  780,  27,  57_500,  "South",  "Accessories"),
        (2024, 10,  175_000,  565,  34, 105_000,  "North",  "Electronics"),
        (2024, 10,  122_000,  830,  29,  61_000,  "South",  "Accessories"),
        (2024, 11,  205_000,  665,  39, 123_000,  "North",  "Electronics"),
        (2024, 11,  144_000,  980,  37,  72_000,  "South",  "Accessories"),
        (2024, 12,  245_000,  785,  48, 147_000,  "North",  "Electronics"),
        (2024, 12,  170_000, 1175,  44,  85_000,  "South",  "Accessories"),
    ]

    df = pd.DataFrame(records, columns=[
        "year", "month", "revenue", "units_sold",
        "returns", "cogs", "region", "category",
    ])

    df["gross_profit"]  = (df["revenue"] - df["cogs"]).fillna(0)
    df["profit_margin"] = (
        df["gross_profit"] / df["revenue"] * 100
    ).fillna(0).round(2)
    df["net_revenue"] = (
        df["revenue"] - (df["returns"] * (df["revenue"] / df["units_sold"]))
    ).fillna(0)
    df["month_name"] = pd.to_datetime(df["month"], format="%m").dt.strftime("%B")
    df = df.fillna(0)
    return df


# Singleton — built once at import time, reused across all tool calls
_SALES_DF = _build_mock_sales()


# ── Query Implementations ─────────────────────────────────────────────────────

def _query_monthly_sales(year: int, category: str, region: str) -> dict:
    """Return all 12 months for a year, aggregated across regions/categories."""
    filters = ["year = ?"]
    params  = [year]

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
    con.register("sales", _SALES_DF)
    df = con.execute(sql, params).df().fillna(0)

    if df.empty:
        return {
            "error":     f"No data for year={year} category={category} region={region}",
            "row_count": 0,
            "data":      [],
        }

    df["ytd_revenue"] = df["revenue"].cumsum()

    result = _df_to_result(df)
    result.update({
        "year":     year,
        "category": category,
        "region":   region,
        "summary": {
            "total_revenue":      _safe_int(df["revenue"].sum()),
            "total_units":        _safe_int(df["units_sold"].sum()),
            "total_returns":      _safe_int(df["returns"].sum()),
            "avg_monthly_rev":    _safe_int(df["revenue"].mean()),
            "best_month":         df.loc[df["revenue"].idxmax(), "month_name"],
            "worst_month":        df.loc[df["revenue"].idxmin(), "month_name"],
            "total_gross_profit": _safe_int(df["gross_profit"].sum()),
        },
    })
    return result


def _query_sales_by_month(
    year: int, month: int, category: str, region: str
) -> dict:
    """Return a single month broken down by region × category."""
    filters = ["year = ?", "month = ?"]
    params  = [year, month]

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
    con.register("sales", _SALES_DF)
    df = con.execute(sql, params).df()

    if df.empty:
        return {
            "error":     f"No data for year={year} month={month} category={category} region={region}",
            "row_count": 0,
            "data":      [],
        }

    result = _df_to_result(df)
    result.update({
        "year":  year,
        "month": month,
        "summary": {
            "total_revenue":      _safe_int(df["revenue"].sum()),
            "total_units":        _safe_int(df["units_sold"].sum()),
            "total_returns":      _safe_int(df["returns"].sum()),
            "total_gross_profit": _safe_int(df["gross_profit"].sum()),
        },
    })
    return result


# ── Tool ──────────────────────────────────────────────────────────────────────

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
        query_type: Query mode — 'get_monthly_sales' for a full year of
                    monthly totals, or 'get_sales_by_month' for a single
                    month broken down by region and category.
        year: The year to query, e.g. 2023 or 2024.
        month: Month number 1-12. Required for get_sales_by_month only.
               Pass 0 (default) when using get_monthly_sales.
        category: Product category filter — 'Electronics', 'Accessories',
                  or 'all' (default).
        region: Region filter — 'North', 'South', or 'all' (default).

    Returns:
        str: JSON string containing query results and summary statistics.
    """
    logger.info(
        "sales_data tool called: query_type=%s year=%s month=%s "
        "category=%s region=%s",
        query_type, year, month, category, region,
    )

    if query_type == "get_monthly_sales":
        result = _query_monthly_sales(year, category, region)

    elif query_type == "get_sales_by_month":
        if not month:
            result = {"error": "month (1-12) is required for get_sales_by_month"}
        else:
            result = _query_sales_by_month(year, month, category, region)

    else:
        result = {
            "error": (
                f"Unknown query_type '{query_type}'. "
                "Use 'get_monthly_sales' or 'get_sales_by_month'."
            )
        }

    return json.dumps(result, default=str)