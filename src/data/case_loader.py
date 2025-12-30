"""
Support Case data loader for Account Solutions Success.

Loads Support Case Excel files and converts them to SupportCase
dataclass instances. Includes repeat issue detection.
"""

from pathlib import Path
from datetime import datetime
from typing import List, Optional, Any, Dict, Set
from collections import defaultdict
import glob
import re

import pandas as pd

from .models import SupportCase, Severity, SupportLevel, ProductSeries


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
    "created_date": ["created date", "createddate", "created_date", "date created"],
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


def _detect_repeat_issues(cases: List[SupportCase]) -> None:
    """
    Detect repeat issues across cases.

    A case is marked as a repeat if:
    - Same account + same serial number + similar case reason
    - Messages reference a previous case number
    - Within 90 days of a closed case with similar issue

    Modifies cases in-place to set is_repeat_issue and repeat_of_case.
    """
    # Group cases by account + serial
    account_serial_map: Dict[str, List[SupportCase]] = defaultdict(list)

    for case in cases:
        if case.serial_number:
            key = f"{case.account_name}|{case.serial_number}"
            account_serial_map[key].append(case)

    # Check each group for repeats
    for key, group_cases in account_serial_map.items():
        if len(group_cases) < 2:
            continue

        # Sort by date (oldest first)
        sorted_cases = sorted(
            group_cases,
            key=lambda c: c.created_date or datetime.min
        )

        # Check for similar case reasons (simplistic matching)
        for i, current in enumerate(sorted_cases):
            for prev in sorted_cases[:i]:
                # Skip if case reasons don't match
                if not _similar_case_reason(current.case_reason, prev.case_reason):
                    continue

                # Skip if too far apart (> 90 days)
                if current.created_date and prev.created_date:
                    days_apart = (current.created_date - prev.created_date).days
                    if days_apart > 90:
                        continue

                # Mark as repeat
                current.is_repeat_issue = True
                current.repeat_of_case = prev.case_number
                break

    # Also check message content for case references
    case_numbers: Set[str] = {c.case_number for c in cases}

    for case in cases:
        if case.is_repeat_issue:
            continue  # Already detected

        all_messages = " ".join(case.messages).lower()

        # Look for references to other case numbers
        patterns = [
            r'case\s*#?\s*(\d{5,8})',
            r'ticket\s*#?\s*(\d{5,8})',
            r'previous\s+case\s+(\d{5,8})',
            r'related\s+to\s+(\d{5,8})',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, all_messages)
            for match in matches:
                # Normalize and check if it's a different case
                ref_case = match.strip()
                if ref_case != case.case_number and ref_case in case_numbers:
                    case.is_repeat_issue = True
                    case.repeat_of_case = ref_case
                    break
            if case.is_repeat_issue:
                break


def _similar_case_reason(reason1: str, reason2: str) -> bool:
    """Check if two case reasons are similar."""
    if not reason1 or not reason2:
        return False

    r1 = reason1.lower().strip()
    r2 = reason2.lower().strip()

    # Exact match
    if r1 == r2:
        return True

    # Check for common keywords
    keywords = ["performance", "network", "disk", "pool", "replication",
                "upgrade", "ha", "failover", "snapshot", "share", "smb", "nfs"]

    r1_keywords = {kw for kw in keywords if kw in r1}
    r2_keywords = {kw for kw in keywords if kw in r2}

    # If any keywords overlap
    if r1_keywords & r2_keywords:
        return True

    return False


def load_support_cases(
    file_path: str | Path,
    detect_repeats: bool = True,
    console_output: Any = None
) -> List[SupportCase]:
    """
    Load support cases from an Excel file.

    Support cases are grouped by case number, with messages aggregated.
    Optionally detects repeat issues across cases.

    Args:
        file_path: Path to Excel file (can include glob pattern like "*.xlsx")
        detect_repeats: Whether to run repeat issue detection
        console_output: Optional output handler with stream_message() method

    Returns:
        List of SupportCase dataclass instances (one per unique case)
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
        raise FileNotFoundError(f"Support case file not found: {file_path}")

    # Load Excel
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
    except Exception:
        try:
            df = pd.read_excel(file_path, engine="xlrd")
        except Exception as e:
            raise ValueError(f"Failed to load Excel file: {e}")

    if console_output:
        console_output.stream_message(f"Loaded {len(df)} support case records")

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

    cases = []
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
        earliest_date = None
        latest_date = None

        for row in rows:
            msg = _get_value(row, df, "text_body", "")
            if msg and str(msg).strip():
                messages.append(str(msg))

            from_addr = _get_value(row, df, "from_address", "")
            if from_addr and str(from_addr).strip():
                from_addresses.append(str(from_addr))

            msg_date = _parse_date(_get_value(row, df, "message_date"))
            if msg_date:
                if earliest_date is None or msg_date < earliest_date:
                    earliest_date = msg_date
                if latest_date is None or msg_date > latest_date:
                    latest_date = msg_date

        support_case = SupportCase(
            case_number=case_num,
            order_number=order_number,
            account_name=str(_get_value(first_row, df, "account_name", "Unknown")),
            serial_number=str(_get_value(first_row, df, "serial_number", "")),
            case_owner=str(_get_value(first_row, df, "case_owner", "")),
            case_age_days=_parse_int(_get_value(first_row, df, "case_age_days", 0)),
            message_date=latest_date or _parse_date(_get_value(first_row, df, "message_date")),
            created_date=earliest_date or _parse_date(_get_value(first_row, df, "created_date")),
            severity=_parse_severity(_get_value(first_row, df, "severity")),
            case_reason=str(_get_value(first_row, df, "case_reason", "")),
            status=str(_get_value(first_row, df, "status", "")),
            product_series=_parse_product_series(_get_value(first_row, df, "product_series")),
            product_model=str(_get_value(first_row, df, "product_model", "")),
            support_level=_parse_support_level(_get_value(first_row, df, "support_level")),
            messages=messages,
            from_addresses=list(set(from_addresses)),  # Unique addresses
        )

        cases.append(support_case)

    if console_output:
        console_output.stream_message(
            f"Parsed {len(cases)} support cases "
            f"({skipped_no_order} skipped - no order number)"
        )

    # Detect repeat issues
    if detect_repeats and cases:
        _detect_repeat_issues(cases)
        repeat_count = sum(1 for c in cases if c.is_repeat_issue)
        if console_output and repeat_count > 0:
            console_output.stream_message(f"Detected {repeat_count} repeat issues")

    return cases
