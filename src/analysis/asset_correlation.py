"""
Asset correlation analysis for TrueNAS Sentiment Analysis.
Tracks serial numbers across cases to identify recurring hardware issues.
"""

import re
from typing import Any, Dict, List

from ..core import streaming_output


def extract_serials_from_text(text: str) -> List[Dict]:
    """
    Extract serial numbers from message text.

    Returns list of dicts with:
    - serial: The serial number
    - component_type: Detected component type
    - is_refurb: Whether it appears to be refurbished
    - refurb_level: R1/R2/R3 if refurbished
    """
    if not text:
        return []

    serials = []

    # TrueNAS chassis serial patterns
    chassis_patterns = [
        r'(A1-\d{6,})',  # New chassis
        r'(R[123]-\d{6,})',  # Refurbished chassis
    ]

    # Drive serial patterns
    drive_patterns = [
        r'(WD[A-Z0-9]{8,})',  # Western Digital
        r'(ST[A-Z0-9]{8,})',  # Seagate
        r'(SAMSUNG[A-Z0-9]{6,})',  # Samsung
        r'([A-Z0-9]{12,20})',  # Generic long serial
    ]

    # Extract chassis serials
    for pattern in chassis_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            serial = match.upper()
            is_refurb = serial.startswith('R')
            refurb_level = serial[:2] if is_refurb else None

            serials.append({
                'serial': serial,
                'component_type': 'Chassis',
                'is_refurb': is_refurb,
                'refurb_level': refurb_level
            })

    # Extract drive serials (less aggressive matching)
    for pattern in drive_patterns[:3]:  # Only named patterns
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            serial = match.upper()
            serials.append({
                'serial': serial,
                'component_type': 'Drive',
                'is_refurb': False,
                'refurb_level': None
            })

    return serials


def analyze_asset_correlations(
    case_analysis: List[Dict],
    console_output: Any = None
) -> Dict:
    """
    Analyze asset correlations across cases.

    Identifies:
    - Serial numbers appearing in multiple cases
    - Refurbished component usage patterns
    - Potential hardware problem patterns

    Args:
        case_analysis: List of case dictionaries
        console_output: Object with stream_message() method

    Returns:
        Dictionary with correlation analysis results
    """
    if console_output is None:
        console_output = streaming_output

    console_output.stream_message("\nAnalyzing asset correlations...")

    # Track serial -> cases mapping
    serial_to_cases = {}

    total_cases = len(case_analysis)
    cases_with_asset_data = 0
    refurb_case_count = 0
    refurb_breakdown = {'R1': 0, 'R2': 0, 'R3': 0}

    for case in case_analysis:
        case_serials = set()

        # Get asset serial from case data
        asset_serial = str(case.get('asset_serial', '')).strip()
        if asset_serial and asset_serial.lower() not in ['', 'nan', 'none']:
            extracted = extract_serials_from_text(asset_serial)
            for item in extracted:
                case_serials.add(item['serial'])

        # Extract serials from messages
        messages = case.get('messages_full', '')
        if messages:
            extracted = extract_serials_from_text(messages)
            for item in extracted:
                case_serials.add(item['serial'])

        if case_serials:
            cases_with_asset_data += 1

        # Map serials to cases
        for serial in case_serials:
            if serial not in serial_to_cases:
                serial_to_cases[serial] = []

            # Get serial metadata
            serial_info = extract_serials_from_text(serial)
            component_type = serial_info[0]['component_type'] if serial_info else 'Unknown'
            is_refurb = serial_info[0]['is_refurb'] if serial_info else False
            refurb_level = serial_info[0]['refurb_level'] if serial_info else None

            serial_to_cases[serial].append({
                'case_number': case['case_number'],
                'criticality_score': case['criticality_score'],
                'severity': case['severity'],
                'component_type': component_type,
                'is_refurb': is_refurb,
                'refurb_level': refurb_level,
            })

            # Track refurb usage
            if is_refurb and refurb_level:
                refurb_case_count += 1
                refurb_breakdown[refurb_level] = refurb_breakdown.get(refurb_level, 0) + 1

    # Find serials appearing in multiple cases
    recurring_serials = []
    for serial, cases in serial_to_cases.items():
        if len(cases) >= 2:
            avg_criticality = sum(c['criticality_score'] for c in cases) / len(cases)
            component_type = cases[0]['component_type']
            is_refurb = cases[0]['is_refurb']
            refurb_level = cases[0]['refurb_level']

            recurring_serials.append({
                'serial': serial,
                'case_count': len(cases),
                'cases': cases,
                'avg_criticality': avg_criticality,
                'component_type': component_type,
                'is_refurb': is_refurb,
                'refurb_level': refurb_level,
            })

    # Sort by case count (most recurring first)
    recurring_serials.sort(key=lambda x: (-x['case_count'], -x['avg_criticality']))

    coverage_percent = (cases_with_asset_data / total_cases * 100) if total_cases > 0 else 0

    result = {
        'total_cases': total_cases,
        'cases_with_asset_data': cases_with_asset_data,
        'coverage_percent': round(coverage_percent, 1),
        'total_serials_tracked': len(serial_to_cases),
        'serials_with_multiple_cases': len(recurring_serials),
        'recurring_serials': recurring_serials,
        'refurb_case_count': refurb_case_count,
        'refurb_breakdown': refurb_breakdown,
    }

    console_output.stream_message(f"  Total serials tracked: {result['total_serials_tracked']}")
    console_output.stream_message(f"  Serials in 2+ cases: {result['serials_with_multiple_cases']}")
    console_output.stream_message(f"  Asset coverage: {result['coverage_percent']:.0f}%")

    return result


def build_account_intelligence_brief(
    case_analysis: List[Dict],
    asset_correlations: Dict = None,
    mode: str = 'full'
) -> str:
    """
    Build account intelligence brief for Claude prompts.

    Args:
        case_analysis: List of case dictionaries
        asset_correlations: Asset correlation data (optional)
        mode: 'light' for quick scoring, 'full' for detailed timelines

    Returns:
        String brief for injection into Claude prompts
    """
    if not case_analysis:
        return "No case history available."

    total_cases = len(case_analysis)
    customer_name = case_analysis[0]['customer_name']

    # Calculate metrics
    avg_frustration = sum(
        c['claude_analysis']['frustration_score'] for c in case_analysis
    ) / total_cases

    high_frustration_count = len([
        c for c in case_analysis
        if c['claude_analysis']['frustration_score'] >= 7
    ])

    critical_count = len([
        c for c in case_analysis
        if c['criticality_score'] >= 180
    ])

    systemic_count = len([
        c for c in case_analysis
        if c['claude_analysis'].get('issue_class') == 'Systemic'
    ])

    # Get severity distribution
    severity_dist = {}
    for case in case_analysis:
        sev = case['severity']
        severity_dist[sev] = severity_dist.get(sev, 0) + 1

    brief = f"""ACCOUNT: {customer_name}
CASE HISTORY: {total_cases} total cases analyzed
AVERAGE FRUSTRATION: {avg_frustration:.1f}/10
HIGH FRUSTRATION CASES: {high_frustration_count}
CRITICAL CASES (>=180): {critical_count}
SYSTEMIC ISSUES: {systemic_count}
SEVERITY DISTRIBUTION: {', '.join(f'{k}: {v}' for k, v in sorted(severity_dist.items()))}
"""

    if mode == 'full' and asset_correlations:
        recurring = asset_correlations.get('recurring_serials', [])
        if recurring:
            brief += f"\nRECURRING HARDWARE ISSUES: {len(recurring)} serials appear in multiple cases"
            for item in recurring[:3]:
                brief += f"\n  - {item['serial']}: {item['case_count']} cases (avg criticality: {item['avg_criticality']:.0f})"

        refurb_count = asset_correlations.get('refurb_case_count', 0)
        if refurb_count > 0:
            brief += f"\n\nREFURBISHED COMPONENTS: {refurb_count} cases involve refurbished parts"

    return brief
