"""
Data loading and preparation for TrueNAS Sentiment Analysis.
Adapted from Part 1 of the original Abacus AI workflow.

Handles:
- Loading Excel files from local paths
- Column mapping and normalization
- Date parsing and validation
- Duplicate case detection and merging
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional, Dict, Any

import pandas as pd

from ..core import print_progress, print_success, print_warning, streaming_output


def extract_tech_info_from_message(message_text: str) -> Optional[Dict[str, str]]:
    """Extract tech name and role from email signature."""
    if pd.isna(message_text):
        return None

    msg_str = str(message_text).lower()

    # Look for common signature patterns at the end of message
    lines = message_text.split('\n')
    signature_lines = lines[-10:] if len(lines) > 10 else lines

    for i, line in enumerate(signature_lines):
        line_lower = line.lower()
        # Look for support role keywords
        if any(keyword in line_lower for keyword in [
            'tier 1', 'tier 2', 'tier 3', 'support engineer',
            'technical support', 'senior support', 'support specialist',
            'software support', 'hardware support', 'escalation engineer'
        ]):
            # The name is likely in the line above or same line
            if i > 0:
                potential_name = signature_lines[i-1].strip()
                # Check if it looks like a name (2-4 words, capitalized, no @)
                if potential_name and '@' not in potential_name and len(potential_name.split()) <= 4:
                    # Clean up common email artifacts
                    potential_name = re.sub(
                        r'(regards|thanks|best|sincerely),?\s*',
                        '',
                        potential_name,
                        flags=re.IGNORECASE
                    )
                    if len(potential_name) > 2:
                        return {
                            'name': potential_name.strip(),
                            'role': line.strip()
                        }

            # Check if name and role are on same line
            match = re.search(r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*[,\-]\s*', line)
            if match:
                return {
                    'name': match.group(1).strip(),
                    'role': line.strip()
                }

    return None


def build_tech_map_for_case(case_data: pd.DataFrame) -> Dict[str, Dict[str, str]]:
    """Build a map of tech emails to their names/roles from message signatures."""
    tech_map = {}

    for _, row in case_data.iterrows():
        msg = row.get('Message', '')
        if pd.isna(msg):
            continue

        msg_str = str(msg)

        # Check if this looks like a tech response
        if '@ixsystems.com' in msg_str.lower():
            # Extract the email
            emails = re.findall(r'([\w\.-]+@ixsystems\.com)', msg_str, re.IGNORECASE)

            # Extract tech info from signature
            tech_info = extract_tech_info_from_message(msg_str)

            if tech_info and emails:
                for email in emails:
                    if email.lower() not in tech_map:
                        tech_map[email.lower()] = tech_info

    return tech_map


def load_and_prepare_data(
    file_path: str | Path,
    console_output: Any = None
) -> Tuple[pd.DataFrame, datetime]:
    """
    Load Excel file and prepare dataframe.

    Args:
        file_path: Path to Excel file (local file path)
        console_output: Object with stream_message() method for output (optional)

    Returns:
        Tuple of (prepared DataFrame, current_date)
    """
    if console_output is None:
        console_output = streaming_output

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")

    # Load Excel file
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
        console_output.stream_message(f"Loaded Excel file: {len(df)} records")
    except Exception as e:
        try:
            df = pd.read_excel(file_path, engine="xlrd")
            console_output.stream_message(f"Loaded Excel file (xlrd): {len(df)} records")
        except Exception as e2:
            raise ValueError(f"Failed to load Excel file: {str(e)}")

    current_date = datetime.now()

    # Normalize column names
    df.columns = df.columns.str.strip()
    column_mapping = {col.lower(): col for col in df.columns}

    # Define required column mappings
    required_columns_map = {
        "case number": ["case number", "case_number", "casenumber", "case no", "case#"],
        "customer name": ["account name", "account_name", "accountname", "customer name",
                         "customer_name", "customername", "customer"],
        "message": ["text body", "text_body", "textbody", "message", "messages",
                   "description", "comment", "text", "body"],
        "message date": ["message date", "message_date", "messagedate", "email date",
                        "email_date", "date", "timestamp", "message timestamp"],
        "severity": ["severity", "priority", "level"],
        "support level": ["support level", "support_level", "supportlevel", "tier", "support tier"],
        "created date": ["created date", "created_date", "createddate", "date created",
                        "create date", "opened date"],
        "last modified date": ["last modified date", "last_modified_date", "lastmodifieddate",
                              "modified date", "updated date", "last updated"],
        "status": ["status", "state", "case status"],
        "case age days": ["case age days", "case_age_days", "caseagedays", "age days",
                         "age_days", "agedays", "case age", "case_age"],
        "asset serial": ["asset serial", "asset_serial", "assetserial", "serial number",
                        "serial_number", "system serial", "asset"],
    }

    # Find actual columns
    actual_columns = {}
    for required_col, possible_names in required_columns_map.items():
        found = False
        for possible_name in possible_names:
            if possible_name in column_mapping:
                actual_columns[required_col] = column_mapping[possible_name]
                found = True
                break
        if not found:
            for col_lower, col_actual in column_mapping.items():
                if any(pn in col_lower for pn in possible_names):
                    actual_columns[required_col] = col_actual
                    found = True
                    break
        if not found and required_col not in [
            "case age days", "created date", "last modified date",
            "status", "support level", "message date", "asset serial"
        ]:
            raise ValueError(f"Missing required column: {required_col}. Available: {list(df.columns)}")

    # Build rename dictionary
    rename_dict = {
        actual_columns["case number"]: "Case Number",
        actual_columns["customer name"]: "Customer Name",
        actual_columns["message"]: "Message",
        actual_columns["severity"]: "Severity",
    }

    if "support level" in actual_columns:
        rename_dict[actual_columns["support level"]] = "Support Level"
    if "asset serial" in actual_columns:
        rename_dict[actual_columns["asset serial"]] = "Asset Serial"
    if "message date" in actual_columns:
        rename_dict[actual_columns["message date"]] = "Message Date"
    if "created date" in actual_columns:
        rename_dict[actual_columns["created date"]] = "Created Date"
    if "last modified date" in actual_columns:
        rename_dict[actual_columns["last modified date"]] = "Last Modified Date"
    if "case age days" in actual_columns:
        rename_dict[actual_columns["case age days"]] = "Case Age Days"
    if "status" in actual_columns:
        rename_dict[actual_columns["status"]] = "Status"

    df = df.rename(columns=rename_dict)

    # Clean data
    df = df.dropna(subset=["Case Number", "Message"])
    df["Customer Name"] = df["Customer Name"].fillna("Unknown Customer")
    df["Severity"] = df["Severity"].fillna("S4")

    if "Support Level" not in df.columns:
        df["Support Level"] = "Unknown"
    else:
        df["Support Level"] = df["Support Level"].fillna("Unknown")

    if "Asset Serial" not in df.columns:
        df["Asset Serial"] = ""
    else:
        df["Asset Serial"] = df["Asset Serial"].fillna("")

    # Parse dates
    if "Message Date" in df.columns:
        try:
            df["Message Date"] = pd.to_datetime(df["Message Date"], errors="coerce")
        except:
            df["Message Date"] = pd.NaT
        df["Message Date"] = df["Message Date"].fillna(current_date)
    else:
        if "Created Date" in df.columns:
            df["Message Date"] = df["Created Date"]
        else:
            df["Message Date"] = current_date

    if "Status" not in df.columns:
        df["Status"] = "Unknown"
    else:
        df["Status"] = df["Status"].fillna("Unknown")

    if "Created Date" in df.columns:
        try:
            df["Created Date"] = pd.to_datetime(df["Created Date"], errors="coerce")
        except:
            df["Created Date"] = pd.NaT
        df["Created Date"] = df["Created Date"].fillna(current_date)
    else:
        df["Created Date"] = current_date

    if "Last Modified Date" in df.columns:
        try:
            df["Last Modified Date"] = pd.to_datetime(df["Last Modified Date"], errors="coerce")
        except:
            df["Last Modified Date"] = pd.NaT
        df["Last Modified Date"] = df["Last Modified Date"].fillna(current_date)
    else:
        df["Last Modified Date"] = current_date

    if "Case Age Days" in df.columns:
        df["case_age_days"] = pd.to_numeric(df["Case Age Days"], errors="coerce").fillna(0).astype(int)
    else:
        df["case_age_days"] = (current_date - df["Created Date"]).dt.days
        df["case_age_days"] = df["case_age_days"].fillna(0).astype(int)

    # Normalize severity
    def extract_severity(severity_str):
        severity_str = str(severity_str).upper()
        if "S1" in severity_str:
            return "S1"
        elif "S2" in severity_str:
            return "S2"
        elif "S3" in severity_str:
            return "S3"
        elif "S4" in severity_str:
            return "S4"
        else:
            return "S4"

    df["Severity"] = df["Severity"].apply(extract_severity)

    return df, current_date


def detect_and_merge_case_relationships(
    df: pd.DataFrame,
    console_output: Any = None
) -> pd.DataFrame:
    """
    Detect duplicate relationships and merge child cases into parents.

    Args:
        df: DataFrame with case data
        console_output: Object with stream_message() method for output

    Returns:
        Modified dataframe with merged cases
    """
    if console_output is None:
        console_output = streaming_output

    # Build case number to messages map
    case_groups = df.groupby('Case Number')

    parent_map = {}  # child_case_num -> parent_case_num
    duplicate_cases = set()

    console_output.stream_message("\nDetecting case relationships (duplicates/escalations)...")

    # PHASE 1: Detect relationships
    for case_num, case_data in case_groups:
        messages_text = ' '.join(case_data['Message'].dropna().astype(str)).lower()

        # Look for duplicate indicators
        duplicate_indicators = [
            'duplicate case',
            'closing as duplicate',
            'duplicate ticket',
            'closed as duplicate',
            'this is a duplicate of',
            'related open case',
            'closing this case as a duplicate',
        ]

        is_duplicate = any(indicator in messages_text for indicator in duplicate_indicators)

        if is_duplicate:
            # Extract parent case reference
            patterns = [
                r'case\s*id:?\s*#?0*(\d{5,8})',
                r'ticket\s*#?0*(\d{5,8})',
                r'case\s*#0*(\d{5,8})',
                r'open\s+case\s+id:?\s*#?0*(\d{5,8})',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, messages_text)
                for match in matches:
                    parent_num = int(match)

                    # Normalize current case number for comparison
                    try:
                        current_case_normalized = int(case_num)
                    except (ValueError, TypeError):
                        current_case_normalized = case_num

                    # Verify it's not self-reference
                    if parent_num == current_case_normalized:
                        continue

                    # Check if parent exists
                    parent_exists = False
                    for check_num in [parent_num, str(parent_num), f"{parent_num:08d}"]:
                        if check_num in case_groups.groups:
                            parent_exists = True
                            parent_num = check_num
                            break

                    if parent_exists:
                        parent_map[case_num] = parent_num
                        duplicate_cases.add(case_num)
                        console_output.stream_message(f"  Case {case_num} is duplicate of {parent_num}")
                        break
                    else:
                        if case_num not in parent_map:
                            console_output.stream_message(
                                f"  Case {case_num} references parent {parent_num} (not in dataset)"
                            )

                if case_num in parent_map:
                    break

    if len(duplicate_cases) == 0:
        console_output.stream_message("  No duplicate relationships detected")
        return df

    console_output.stream_message(f"\n  Found {len(duplicate_cases)} duplicate cases to merge")

    # PHASE 2: Merge duplicates into parents
    merged_rows = []

    for case_num, case_data in case_groups:
        if case_num in duplicate_cases:
            # This is a duplicate - merge into parent
            parent_num = parent_map[case_num]

            # Create escalation event marker
            escalation_event = pd.DataFrame([{
                'Case Number': parent_num,
                'Customer Name': case_data.iloc[0]['Customer Name'],
                'Message': f"[ESCALATION EVENT] Customer spawned duplicate case {case_num} "
                          f"indicating lack of response on this case. Messages from duplicate case follow below.",
                'Message Date': case_data['Message Date'].min(),
                'Severity': case_data.iloc[0]['Severity'],
                'Support Level': case_data.iloc[0]['Support Level'],
                'Created Date': case_data.iloc[0]['Created Date'],
                'Last Modified Date': case_data.iloc[0]['Last Modified Date'],
                'Status': case_data.iloc[0]['Status'],
                'Case Age Days': case_data.iloc[0].get('Case Age Days', 0),
            }])

            merged_rows.append(escalation_event)

            # Merge duplicate messages into parent
            duplicate_messages = case_data.copy()
            duplicate_messages['Case Number'] = parent_num
            duplicate_messages['Message'] = (
                "[DUPLICATE CASE " + str(case_num) + "] " +
                duplicate_messages['Message'].astype(str)
            )

            merged_rows.append(duplicate_messages)

            console_output.stream_message(
                f"  Merged {len(case_data)} messages from case {case_num} -> parent {parent_num}"
            )
        else:
            # Not a duplicate - include as-is
            merged_rows.append(case_data)

    # Combine all rows
    df_merged = pd.concat(merged_rows, ignore_index=True)

    # Sort by case number and message date
    df_merged = df_merged.sort_values(['Case Number', 'Message Date'])

    original_case_count = len(case_groups)
    merged_case_count = df_merged['Case Number'].nunique()

    console_output.stream_message(f"\nMerge complete:")
    console_output.stream_message(f"  Original cases: {original_case_count}")
    console_output.stream_message(f"  After merging: {merged_case_count}")
    console_output.stream_message(f"  Duplicates merged: {len(duplicate_cases)}")

    return df_merged
