"""
Deployment data loader for Account Solutions Success.

Loads Professional Services deployment case Excel files and converts
them to Deployment dataclass instances.

Deployment cases have the same structure as Support Cases
(Record Type: Deployment vs Support).
"""

from pathlib import Path
from datetime import datetime
from typing import List, Optional, Any, Dict
from collections import defaultdict
import glob

import pandas as pd

from .models import Deployment, Severity, SupportLevel, ProductSeries


# Column mappings: expected column name -> possible variations
COLUMN_MAPPINGS = {
    "case_number": ["case number", "casenumber", "case_number", "case #", "case"],
    "order_number": ["order number", "ordernumber", "order_number", "order #", "order"],
    "account_name": ["account name", "accountname", "account_name", "customer", "customer name"],
    "case_owner": ["case owner", "caseowner", "case_owner", "owner", "assigned to"],
    "case_age_days": ["case age days", "caseagedays", "case_age_days", "age days", "case age"],
    "severity": ["severity", "priority", "level", "sev"],
    "text_body": ["text body", "textbody", "text_body", "message", "body", "description"],
    "from_address": ["from address", "fromaddress", "from_address", "from", "sender", "email"],
    "product_series": ["product series", "productseries", "product_series", "series"],
    "case_reason": ["case reason", "casereason", "case_reason", "reason", "category"],
    "product_model": ["product model", "productmodel", "product_model", "model"],
    "support_level": ["support level", "supportlevel", "support_level", "tier", "support tier"],
    "message_date": ["message date", "messagedate", "message_date", "date", "timestamp"],
    "status": ["status", "state", "case status"],
    "serial_number": ["serial number", "serialnumber", "serial_number", "serial", "asset serial"],
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


def _parse_severity(value: Any) -> Severity:
    """Parse severity string to Severity enum."""
    if pd.isna(value):
        return Severity.S4

    val_upper = str(value).upper().strip()

    if "S1" in val_upper or "SEV1" in val_upper or "CRITICAL" in val_upper:
        return Severity.S1
    if "S2" in val_upper or "SEV2" in val_upper or "HIGH" in val_upper:
        return Severity.S2
    if "S3" in val_upper or "SEV3" in val_upper or "MEDIUM" in val_upper:
        return Severity.S3

    return Severity.S4


def _parse_support_level(value: Any) -> SupportLevel:
    """Parse support level string to SupportLevel enum."""
    if pd.isna(value):
        return SupportLevel.UNKNOWN

    val_upper = str(value).upper().strip()

    if "GOLD" in val_upper:
        return SupportLevel.GOLD
    if "SILVER" in val_upper:
        return SupportLevel.SILVER
    if "BRONZE" in val_upper:
        return SupportLevel.BRONZE

    return SupportLevel.UNKNOWN


def _parse_product_series(value: Any) -> ProductSeries:
    """Parse product series string to ProductSeries enum."""
    if pd.isna(value):
        return ProductSeries.UNKNOWN

    val_upper = str(value).upper().strip()

    if val_upper in ["F", "F-SERIES", "FSERIES"]:
        return ProductSeries.F_SERIES
    if val_upper in ["M", "M-SERIES", "MSERIES"]:
        return ProductSeries.M_SERIES
    if val_upper in ["H", "H-SERIES", "HSERIES"]:
        return ProductSeries.H_SERIES
    if val_upper in ["R", "R-SERIES", "RSERIES"]:
        return ProductSeries.R_SERIES

    return ProductSeries.UNKNOWN


def _parse_int(value: Any, default: int = 0) -> int:
    """Parse value to integer."""
    if pd.isna(value):
        return default
    try:
        return int(float(value))
    except:
        return default


def _detect_service_deploy(messages: List[str], case_owner: str) -> bool:
    """
    Detect if this was a service team deployment vs self-deploy.

    Heuristics:
    - Service team names in owner
    - References to PS engineer, installation team
    - On-site references
    """
    # Check case owner for service indicators
    owner_lower = case_owner.lower()
    service_keywords = ["professional services", "ps ", "deploy", "install", "implementation"]
    if any(kw in owner_lower for kw in service_keywords):
        return True

    # Check messages for service deployment indicators
    all_text = " ".join(messages).lower()
    service_phrases = [
        "on-site", "onsite",
        "installation complete",
        "deployment engineer",
        "ps engineer",
        "implementation specialist",
        "service team",
        "professional services",
    ]

    return any(phrase in all_text for phrase in service_phrases)


def load_deployments(
    file_path: str | Path,
    console_output: Any = None
) -> List[Deployment]:
    """
    Load deployment cases from an Excel file.

    Deployment cases are grouped by case number, with messages aggregated.

    Args:
        file_path: Path to Excel file (can include glob pattern like "*.xlsx")
        console_output: Optional output handler with stream_message() method

    Returns:
        List of Deployment dataclass instances (one per unique case)
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
        raise FileNotFoundError(f"Deployment file not found: {file_path}")

    # Load Excel
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
    except Exception:
        try:
            df = pd.read_excel(file_path, engine="xlrd")
        except Exception as e:
            raise ValueError(f"Failed to load Excel file: {e}")

    if console_output:
        console_output.stream_message(f"Loaded {len(df)} deployment records")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Verify we have required columns
    case_col = _find_column(df, "case_number")
    order_col = _find_column(df, "order_number")

    if not case_col:
        raise ValueError(f"Case Number column not found. Available columns: {list(df.columns)}")

    # Group rows by case number (each case may have multiple message rows)
    case_groups: Dict[str, List[pd.Series]] = defaultdict(list)

    for _, row in df.iterrows():
        case_num = str(_get_value(row, df, "case_number", "")).strip()
        if case_num and case_num.lower() not in ["nan", "none", ""]:
            case_groups[case_num].append(row)

    deployments = []
    skipped_no_order = 0

    for case_num, rows in case_groups.items():
        # Use first row for metadata
        first_row = rows[0]

        order_number = str(_get_value(first_row, df, "order_number", "")).strip()

        # Skip if no order number
        if not order_number or order_number.lower() in ["nan", "none", ""]:
            skipped_no_order += 1
            continue

        # Aggregate messages and from addresses
        messages = []
        from_addresses = []

        for row in rows:
            msg = _get_value(row, df, "text_body", "")
            if msg and str(msg).strip():
                messages.append(str(msg))

            from_addr = _get_value(row, df, "from_address", "")
            if from_addr and str(from_addr).strip():
                from_addresses.append(str(from_addr))

        case_owner = str(_get_value(first_row, df, "case_owner", ""))

        deployment = Deployment(
            case_number=case_num,
            order_number=order_number,
            account_name=str(_get_value(first_row, df, "account_name", "Unknown")),
            serial_number=str(_get_value(first_row, df, "serial_number", "")),
            case_owner=case_owner,
            case_age_days=_parse_int(_get_value(first_row, df, "case_age_days", 0)),
            message_date=_parse_date(_get_value(first_row, df, "message_date")),
            severity=_parse_severity(_get_value(first_row, df, "severity")),
            case_reason=str(_get_value(first_row, df, "case_reason", "")),
            status=str(_get_value(first_row, df, "status", "")),
            product_series=_parse_product_series(_get_value(first_row, df, "product_series")),
            product_model=str(_get_value(first_row, df, "product_model", "")),
            support_level=_parse_support_level(_get_value(first_row, df, "support_level")),
            messages=messages,
            from_addresses=list(set(from_addresses)),  # Unique addresses
            is_service_deploy=_detect_service_deploy(messages, case_owner),
        )

        deployments.append(deployment)

    if console_output:
        console_output.stream_message(
            f"Parsed {len(deployments)} deployment cases "
            f"({skipped_no_order} skipped - no order number)"
        )

    return deployments
