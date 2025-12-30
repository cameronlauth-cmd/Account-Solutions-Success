"""
Opportunity data loader for Account Solutions Success.

Loads Salesforce Opportunity export Excel files and converts
them to Opportunity dataclass instances.
"""

from pathlib import Path
from datetime import datetime
from typing import List, Optional, Any
import glob

import pandas as pd

from .models import Opportunity, ProductSeries


# Column mappings: expected column name -> possible variations
COLUMN_MAPPINGS = {
    "order_number": ["order number", "ordernumber", "order_number", "order #", "order"],
    "opportunity_name": ["opportunity name", "opportunityname", "opportunity_name", "opp name"],
    "account_name": ["account name", "accountname", "account_name", "customer", "customer name"],
    "opportunity_owner": ["opportunity owner", "opportunityowner", "opportunity_owner", "owner", "opp owner"],
    "owner_role": ["owner role", "ownerrole", "owner_role", "role"],
    "fiscal_period": ["fiscal period", "fiscalperiod", "fiscal_period", "quarter", "period"],
    "lead_source": ["lead source", "leadsource", "lead_source", "source"],
    "deal_type": ["type", "deal type", "dealtype", "deal_type", "opportunity type"],
    "amount": ["amount", "deal value", "value", "price", "total"],
    "close_date": ["close date", "closedate", "close_date", "closed date", "won date"],
    "created_date": ["created date", "createddate", "created_date", "create date"],
    "products_quoted": ["products quoted", "productsquoted", "products_quoted", "products"],
    "primary_product": ["primary product", "primaryproduct", "primary_product", "main product"],
    "system_model": ["system model", "systemmodel", "system_model", "model"],
    "business_need": ["business need", "businessneed", "business_need", "need"],
    "primary_use_case": ["primary use case", "primaryusecase", "primary_use_case", "use case", "usecase"],
    "pain_points": ["pain points", "painpoints", "pain_points", "challenges"],
    "next_step": ["next step", "nextstep", "next_step", "next steps"],
}


def _find_column(df: pd.DataFrame, field_name: str) -> Optional[str]:
    """Find the actual column name in the dataframe for a given field."""
    possible_names = COLUMN_MAPPINGS.get(field_name, [field_name])

    # Create lowercase column mapping
    col_lower_map = {col.lower().strip(): col for col in df.columns}

    for possible in possible_names:
        if possible.lower() in col_lower_map:
            return col_lower_map[possible.lower()]

    # Try partial match
    for possible in possible_names:
        for col_lower, col_actual in col_lower_map.items():
            if possible.lower() in col_lower:
                return col_actual

    return None


def _get_value(row: pd.Series, df: pd.DataFrame, field_name: str, default: Any = "") -> Any:
    """Get value from row using field mapping."""
    col = _find_column(df, field_name)
    if col and col in row.index:
        val = row[col]
        if pd.isna(val):
            return default
        return val
    return default


def _parse_date(value: Any) -> Optional[datetime]:
    """Parse a date value to datetime."""
    if pd.isna(value):
        return None
    try:
        return pd.to_datetime(value)
    except:
        return None


def _parse_amount(value: Any) -> float:
    """Parse amount value to float."""
    if pd.isna(value):
        return 0.0
    try:
        # Handle string values with currency symbols
        if isinstance(value, str):
            value = value.replace("$", "").replace(",", "").strip()
        return float(value)
    except:
        return 0.0


def _derive_product_series(primary_product: str) -> ProductSeries:
    """Derive product series from primary product string."""
    if not primary_product:
        return ProductSeries.UNKNOWN

    product_upper = str(primary_product).upper().strip()

    # Check for explicit series identifiers
    if any(x in product_upper for x in ["F-SERIES", "FSERIES", "F100", "F60", "F130"]):
        return ProductSeries.F_SERIES
    if any(x in product_upper for x in ["M-SERIES", "MSERIES", "M40", "M50", "M60"]):
        return ProductSeries.M_SERIES
    if any(x in product_upper for x in ["H-SERIES", "HSERIES", "H10", "H20"]):
        return ProductSeries.H_SERIES
    if any(x in product_upper for x in ["R-SERIES", "RSERIES", "R10", "R20", "R30", "R40", "R50"]):
        return ProductSeries.R_SERIES

    # Check first character
    if product_upper.startswith("F"):
        return ProductSeries.F_SERIES
    if product_upper.startswith("M"):
        return ProductSeries.M_SERIES
    if product_upper.startswith("H"):
        return ProductSeries.H_SERIES
    if product_upper.startswith("R"):
        return ProductSeries.R_SERIES

    return ProductSeries.UNKNOWN


def load_opportunities(
    file_path: str | Path,
    console_output: Any = None
) -> List[Opportunity]:
    """
    Load opportunities from an Excel file.

    Args:
        file_path: Path to Excel file (can include glob pattern like "*.xlsx")
        console_output: Optional output handler with stream_message() method

    Returns:
        List of Opportunity dataclass instances
    """
    file_path = str(file_path)

    # Handle glob patterns
    if "*" in file_path:
        files = glob.glob(file_path)
        if not files:
            raise FileNotFoundError(f"No files matching pattern: {file_path}")
        file_path = files[0]  # Use first match
        if console_output:
            console_output.stream_message(f"Using file: {Path(file_path).name}")

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Opportunity file not found: {file_path}")

    # Load Excel
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
    except Exception:
        try:
            df = pd.read_excel(file_path, engine="xlrd")
        except Exception as e:
            raise ValueError(f"Failed to load Excel file: {e}")

    if console_output:
        console_output.stream_message(f"Loaded {len(df)} opportunity records")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Verify we have order number column
    order_col = _find_column(df, "order_number")
    if not order_col:
        raise ValueError(f"Order Number column not found. Available columns: {list(df.columns)}")

    opportunities = []
    skipped = 0

    for _, row in df.iterrows():
        order_number = str(_get_value(row, df, "order_number", "")).strip()

        # Skip rows without order number
        if not order_number or order_number.lower() in ["nan", "none", ""]:
            skipped += 1
            continue

        primary_product = str(_get_value(row, df, "primary_product", ""))

        opp = Opportunity(
            order_number=order_number,
            opportunity_name=str(_get_value(row, df, "opportunity_name", "")),
            account_name=str(_get_value(row, df, "account_name", "Unknown")),
            opportunity_owner=str(_get_value(row, df, "opportunity_owner", "")),
            owner_role=str(_get_value(row, df, "owner_role", "")),
            fiscal_period=str(_get_value(row, df, "fiscal_period", "")),
            lead_source=str(_get_value(row, df, "lead_source", "")),
            deal_type=str(_get_value(row, df, "deal_type", "")),
            amount=_parse_amount(_get_value(row, df, "amount", 0)),
            close_date=_parse_date(_get_value(row, df, "close_date")),
            created_date=_parse_date(_get_value(row, df, "created_date")),
            products_quoted=str(_get_value(row, df, "products_quoted", "")),
            primary_product=primary_product,
            system_model=str(_get_value(row, df, "system_model", "")),
            business_need=str(_get_value(row, df, "business_need", "")),
            primary_use_case=str(_get_value(row, df, "primary_use_case", "")),
            pain_points=str(_get_value(row, df, "pain_points", "")),
            next_step=str(_get_value(row, df, "next_step", "")),
            product_series=_derive_product_series(primary_product),
        )

        opportunities.append(opp)

    if console_output:
        console_output.stream_message(
            f"Parsed {len(opportunities)} opportunities ({skipped} skipped - no order number)"
        )

    return opportunities
