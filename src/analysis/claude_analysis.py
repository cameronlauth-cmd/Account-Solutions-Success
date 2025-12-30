"""
Claude AI analysis for TrueNAS Sentiment Analysis.
Adapted from Parts 1 and 2 of the original Abacus AI workflow.

Handles:
- Claude 3.5 Haiku: Message-by-message frustration scoring (Stage 1)
- Claude 3.5 Sonnet: Quick pattern scoring (Stage 2A)
- Claude 3.5 Sonnet: Detailed timeline generation (Stage 2B)
"""

import json
import time
import re
from typing import Any, Dict, List, Tuple, Optional

import numpy as np
import pandas as pd

from ..core import get_claude_client, streaming_output, Config
from .data_loader import build_tech_map_for_case


# TrueNAS-specific analysis context
DEFAULT_ANALYSIS_CONTEXT = """
COMPANY & PRODUCT CONTEXT:
TrueNAS is an enterprise open-source storage company serving Fortune 500 customers globally.
Products: TrueNAS F-Series (high-performance NVMe), M-Series (high-capacity all-flash/hybrid),
H-Series (versatile & power-efficient), R-Series (single controller appliance).
Technology: ZFS file system, self-healing architecture, unified storage for virtualization and backup.

SUPPORT TIER CONTEXT:
- Gold Support: 24x7 for S1/S2, 4-hour on-site response, proactive monitoring
- Silver Support: 24x5 for S1/S2, next business day on-site response
- Bronze Support: 12x5 business hours, email support, next business day parts

SEVERITY LEVEL DEFINITIONS:
- S1: System not serving data OR severe performance degradation critically disrupting business operations
  -> CRITICAL: Production down, data inaccessible, business impact
  -> SLA: 2-hour response, 24x7 (Gold/Silver)

- S2: Performance degradation in production OR intermittent faults affecting operations
  -> HIGH: System functional but degraded, impacting productivity
  -> SLA: 4-hour response, 24x7 (Gold), 24x5 (Silver)

- S3: Issue or defect causing minimal business impact
  -> MEDIUM: Minor problems, workarounds available
  -> SLA: 4-hour email response during business hours

- S4: Information requests or administrative questions
  -> LOW: General inquiries, how-to questions
  -> SLA: Next business day response

CUSTOMER PROFILE:
Enterprise B2B customers with mission-critical storage needs. Customers expect:
- Fast response for production issues (S1/S2)
- Expert technical knowledge of ZFS, storage, and enterprise infrastructure
- Professional communication with minimal back-and-forth
- Clear escalation paths and regular updates
- Hardware replacement within SLA commitments

COMMON ISSUES TO RECOGNIZE:
- Storage performance problems (IOPS, latency, throughput)
- Data integrity concerns (scrub errors, disk failures)
- Replication/backup issues affecting disaster recovery
- Hardware failures (drives, controllers, power supplies)
- Software upgrade complications
- Network connectivity or configuration issues

CHURN RISK INDICATORS:
- Threats to switch to competitors (NetApp, Dell EMC, Pure Storage)
- Mentions of contract renewal concerns
- Executive escalation requests
- Repeated issues without resolution
- SLA violations or missed commitments
- Loss of trust in product or support team
"""


def extract_frustrated_excerpts(case_data: pd.DataFrame, frustrated_phrases: List[str]) -> List[Dict]:
    """
    Extract message excerpts containing frustrated phrases.

    Args:
        case_data: DataFrame with case messages
        frustrated_phrases: List of phrases to find

    Returns:
        List of excerpt dictionaries with highlighted phrases
    """
    excerpts = []
    messages_list = case_data["Message"].tolist()

    for phrase in frustrated_phrases:
        if not phrase or len(phrase) < 10:
            continue

        phrase_lower = phrase.lower()

        for msg in messages_list:
            if pd.isna(msg):
                continue
            msg_str = str(msg).strip()
            msg_lower = msg_str.lower()

            if phrase_lower in msg_lower:
                phrase_pos = msg_lower.find(phrase_lower)
                start = max(0, phrase_pos - 200)
                end = min(len(msg_str), phrase_pos + len(phrase) + 200)

                excerpt_text = msg_str[start:end].strip()

                if start > 0:
                    excerpt_text = "..." + excerpt_text
                if end < len(msg_str):
                    excerpt_text = excerpt_text + "..."

                # HTML escape
                excerpt_text = excerpt_text.replace('&', '&amp;')
                excerpt_text = excerpt_text.replace('<', '&lt;')
                excerpt_text = excerpt_text.replace('>', '&gt;')

                escaped_phrase = phrase.replace('&', '&amp;')
                escaped_phrase = escaped_phrase.replace('<', '&lt;')
                escaped_phrase = escaped_phrase.replace('>', '&gt;')

                excerpt_lower = excerpt_text.lower()
                escaped_phrase_lower = escaped_phrase.lower()
                phrase_start = excerpt_lower.find(escaped_phrase_lower)

                if phrase_start != -1:
                    before = excerpt_text[:phrase_start]
                    matched = excerpt_text[phrase_start:phrase_start + len(escaped_phrase)]
                    after = excerpt_text[phrase_start + len(escaped_phrase):]

                    highlighted = f'{before}<font color="#DC2626"><b>{matched}</b></font>{after}'
                    excerpts.append({
                        'phrase': phrase,
                        'excerpt': highlighted,
                        'raw_excerpt': excerpt_text
                    })
                else:
                    excerpts.append({
                        'phrase': phrase,
                        'excerpt': excerpt_text,
                        'raw_excerpt': excerpt_text
                    })

                break  # Only one excerpt per phrase

    return excerpts


def build_enhanced_message_history(case_data: pd.DataFrame) -> str:
    """
    Build message history with ownership attribution and delay information.

    Args:
        case_data: DataFrame with case messages sorted by date

    Returns:
        String with enhanced message history including [CUSTOMER]/[SUPPORT] tags
    """
    case_data_sorted = case_data.sort_values('Message Date')

    messages = []
    prev_date = None
    prev_is_customer = None

    for idx, row in case_data_sorted.iterrows():
        msg = row.get('Message', '')
        if pd.isna(msg):
            continue

        msg_date = row.get('Message Date')
        msg_str = str(msg).strip()

        # Determine if this is a customer or support message
        # Heuristic: Look for common patterns
        is_customer = False
        msg_lower = msg_str.lower()

        # Customer indicators
        customer_indicators = [
            '@' in msg_str and 'truenas' not in msg_lower and 'ixsystems' not in msg_lower,
            'thank you' in msg_lower and 'we thank' not in msg_lower,
            'please help' in msg_lower,
            'we are experiencing' in msg_lower,
            'our ' in msg_lower and ('system' in msg_lower or 'server' in msg_lower),
        ]

        # Support indicators
        support_indicators = [
            'truenas' in msg_lower or 'ixsystems' in msg_lower,
            'i have' in msg_lower and 'reviewed' in msg_lower,
            'please let me know' in msg_lower,
            'i will' in msg_lower,
            'we will' in msg_lower and 'dispatch' in msg_lower,
        ]

        if any(customer_indicators):
            is_customer = True
        elif any(support_indicators):
            is_customer = False
        else:
            # Default to alternating
            is_customer = not prev_is_customer if prev_is_customer is not None else True

        # Calculate delay
        delay_info = ""
        if prev_date is not None and msg_date is not None:
            try:
                days_diff = (msg_date - prev_date).days
                if days_diff > 0:
                    if is_customer and not prev_is_customer:
                        delay_info = f" ({days_diff}d delay - CUSTOMER not responding)"
                    elif not is_customer and prev_is_customer:
                        delay_info = f" ({days_diff}d delay - SUPPORT responsible)"
            except:
                pass

        ownership = "[CUSTOMER]" if is_customer else "[SUPPORT]"
        date_str = msg_date.strftime('%b %d, %Y') if isinstance(msg_date, pd.Timestamp) else 'Unknown'

        messages.append(f"{ownership} [{date_str}]{delay_info}\n{msg_str[:2000]}")

        prev_date = msg_date
        prev_is_customer = is_customer

    return "\n\n---\n\n".join(messages)


def run_claude_analysis(
    df: pd.DataFrame,
    analysis_context: str = None,
    console_output: Any = None
) -> Tuple[List[Dict], Dict, Dict, Dict, float]:
    """
    Run Claude 3.5 Haiku analysis on all cases with message-by-message scoring.
    """
    if console_output is None:
        console_output = streaming_output
    if analysis_context is None:
        analysis_context = DEFAULT_ANALYSIS_CONTEXT

    client = get_claude_client()

    unique_cases = df["Case Number"].unique()
    total_cases = len(unique_cases)

    customer_name = df["Customer Name"].iloc[0] if len(df) > 0 else "Unknown Customer"

    console_output.stream_message("=" * 70)
    console_output.stream_message("STAGE 1: CLAUDE 3.5 HAIKU ANALYSIS")
    console_output.stream_message(f"Account: {customer_name}")
    console_output.stream_message(f"Analyzing {total_cases} cases for this customer")
    console_output.stream_message("=" * 70 + "\n")

    case_analysis = []
    issue_categories = {}
    support_level_distribution = {}
    claude_statistics = {
        "total_analyzed": 0,
        "high_frustration": 0,
        "medium_frustration": 0,
        "low_frustration": 0,
        "no_frustration": 0,
        "avg_frustration_score": 0,
        "total_frustration_score": 0,
        "api_errors": 0,
        "analysis_time_seconds": 0,
        "total_messages_analyzed": 0,
        "frustrated_messages_count": 0,
    }

    start_time = time.time()

    for idx, case_num in enumerate(unique_cases, 1):
        case_data = df[df["Case Number"] == case_num].copy()

        if idx % 5 == 0 or idx == 1:
            progress_pct = (idx / total_cases) * 100
            console_output.stream_message(f"[{idx}/{total_cases}] ({progress_pct:.1f}%) Claude analyzing...")

        first_row = case_data.iloc[0]
        customer_name_case = str(first_row["Customer Name"])
        severity = first_row["Severity"]
        created_date = first_row["Created Date"]
        last_modified = first_row["Last Modified Date"]
        status = str(first_row["Status"])
        case_age = int(first_row["case_age_days"])

        # Parse support level
        support_level_raw = str(first_row["Support Level"]).upper()
        if "GOLD" in support_level_raw:
            support_level = "Gold"
        elif "SILVER" in support_level_raw:
            support_level = "Silver"
        elif "BRONZE" in support_level_raw:
            support_level = "Bronze"
        elif "BASIC" in support_level_raw or "M-F" in support_level_raw or "8-5" in support_level_raw:
            support_level = "Basic"
        else:
            support_level = "Unknown"

        support_level_distribution[support_level] = support_level_distribution.get(support_level, 0) + 1

        interaction_count = len(case_data)

        # Sort and prepare messages
        case_data_sorted = case_data.sort_values('Message Date')
        case_messages = case_data_sorted["Message"].tolist()
        case_dates = case_data_sorted["Message Date"].tolist()

        # Build full message text
        all_messages_text = "\n\n---MESSAGE---\n\n".join([
            f"[{case_dates[i].strftime('%b %d, %Y %I:%M %p') if isinstance(case_dates[i], pd.Timestamp) else 'Date Unknown'}] "
            f"Msg {i+1}: {str(msg)}"
            for i, msg in enumerate(case_messages)
            if not pd.isna(msg)
        ])

        # Prepare messages for batch analysis
        messages_to_analyze = []
        for i, msg in enumerate(case_messages):
            if pd.isna(msg):
                continue
            msg_str = str(msg).strip()
            if len(msg_str) > 2000:
                msg_str = msg_str[:2000] + "..."
            messages_to_analyze.append({
                'index': i + 1,
                'date': case_dates[i].strftime('%b %d, %Y') if isinstance(case_dates[i], pd.Timestamp) else 'Unknown',
                'text': msg_str
            })

        messages_json = json.dumps(messages_to_analyze, indent=2)

        # ORIGINAL HAIKU PROMPT - ENHANCED FOR BUSINESS IMPACT DETECTION
        claude_prompt = f"""Analyze EACH message in this support case individually for frustration level.

CASE CONTEXT:
Customer: {customer_name_case}
Support Level: {support_level} tier
Case Duration: {case_age} days
Total Messages: {interaction_count}
Severity: {severity}

{analysis_context}

MESSAGES TO ANALYZE:
{messages_json}

CRITICAL FRUSTRATION SIGNALS TO DETECT:
Watch for these HIGH PRIORITY signals that indicate significant frustration (score 7+):
- Executive mentions: "execs", "management", "leadership", "CEO", "CTO", "board"
- Replacement threats: "replace", "switch", "consider other options", "looking at alternatives"
- Impatience: "impatient", "frustrated", "unacceptable", "too long", "how much longer"
- Trust erosion: "losing confidence", "concerned about", "questioning", "disappointed"
- Business impact: "production", "downtime", "affecting operations", "costing us"
- Escalation: "escalate", "manager", "supervisor", "higher up"
- Ultimatums: "last chance", "final attempt", "if this doesn't work"

SCORING GUIDE (0-10):
- 0: Neutral/positive, thankful, satisfied
- 1-2: Minor concern, patient inquiry, polite follow-up
- 3-4: Some impatience, mild disappointment, timeline concerns
- 5-6: Clear disappointment, repeated issues, patience wearing thin
- 7-8: Frustration visible, executive involvement, questioning value, escalation threats
- 9-10: Extreme anger, trust broken, threats to leave, legal/contract mentions

IMPORTANT: If a message contains EXECUTIVE INVOLVEMENT or REPLACEMENT CONSIDERATIONS, score it 7+ minimum.

Respond with a JSON structure for EACH message:
[
  {{"msg": 1, "score": X, "reason": "brief reason"}},
  {{"msg": 2, "score": Y, "reason": "brief reason"}},
  ...
]

Then provide overall assessment:
ISSUE_CLASS: [What type of problem is this?]
- Systemic: Overall system not meeting performance/reliability expectations
- Environmental: Issues with how system fits in their environment (integration, compatibility)
- Component: Specific hardware/software component problem
- Procedural: Configuration issue, user error, or knowledge gap

RESOLUTION_OUTLOOK: [How likely is permanent resolution?]
- Challenging: May require significant changes or have no clear fix
- Manageable: Can be resolved but may take time/effort
- Straightforward: Clear path to resolution

KEY_PHRASE: [Most concerning customer statement - especially executive mentions or replacement threats]"""

        try:
            claude_response = client.evaluate_prompt(
                prompt=claude_prompt,
                system_message="You are analyzing customer support messages for frustration patterns. "
                              "Evaluate EACH message independently for emotional signals, then identify overall patterns. "
                              "Be precise and objective in scoring individual messages.",
                llm_name="CLAUDE_V3_5_HAIKU",
            )

            claude_content = claude_response.content.strip()

            # Parse message scores from JSON response
            message_scores = []
            try:
                json_match = re.search(r'\[.*?\]', claude_content, re.DOTALL)
                if json_match:
                    scores_json = json_match.group()
                    message_scores = json.loads(scores_json)
                    claude_statistics["total_messages_analyzed"] += len(message_scores)

                    # Count frustrated messages (score >= 4)
                    frustrated_count = len([s for s in message_scores if s.get('score', 0) >= 4])
                    claude_statistics["frustrated_messages_count"] += frustrated_count
            except:
                message_scores = []

            # Calculate metrics for hybrid scoring
            if message_scores:
                scores_only = [s.get('score', 0) for s in message_scores]

                average_score = np.mean(scores_only)
                peak_score = max(scores_only)
                frustrated_messages = [s for s in scores_only if s >= 4]
                frustration_frequency = len(frustrated_messages) / len(scores_only)

                # Apply hybrid formula - ENHANCED to weight peak signals properly
                # Critical insight: Even ONE executive escalation message should drive score up
                if peak_score >= 8:
                    # Extreme frustration detected - peak dominates
                    final_score = (peak_score * 0.8) + (average_score * 0.2)
                elif peak_score >= 7:
                    # High frustration signal (executive mention, replacement threat)
                    # Don't let low average dilute the score below 5
                    final_score = max(5, (peak_score * 0.6) + (average_score * 0.4))
                elif frustration_frequency > 0.5:
                    final_score = (peak_score * 0.7) + (average_score * 0.3)
                elif frustration_frequency > 0.2:
                    final_score = (peak_score * 0.4) + (average_score * 0.6)
                else:
                    # Low frequency but check for any concerning signals
                    if peak_score >= 5:
                        final_score = max(3, (peak_score * 0.3) + (average_score * 0.7))
                    else:
                        final_score = average_score

                final_score = round(final_score)

                frustration_metrics = {
                    'average_score': round(average_score, 2),
                    'peak_score': peak_score,
                    'frustration_frequency': round(frustration_frequency * 100, 1),
                    'frustrated_message_count': len(frustrated_messages),
                    'total_messages': len(scores_only),
                    'message_scores': message_scores[:10]
                }
            else:
                final_score = 5
                frustration_metrics = {
                    'average_score': 5,
                    'peak_score': 5,
                    'frustration_frequency': 50,
                    'frustrated_message_count': 1,
                    'total_messages': len(messages_to_analyze),
                    'message_scores': []
                }

            claude_analysis = {
                "frustration_score": min(10, max(0, final_score)),
                "frustration_metrics": frustration_metrics,
                "issue_class": "Procedural",
                "resolution_outlook": "Straightforward",
                "key_phrase": "",
                "analysis_model": "Claude 3.5 Haiku (Hybrid)",
                "analysis_successful": True,
            }

            for line in claude_content.split('\n'):
                line = line.strip()

                if line.startswith('ISSUE_CLASS:'):
                    class_text = line.replace('ISSUE_CLASS:', '').strip()
                    if 'Systemic' in class_text:
                        claude_analysis['issue_class'] = 'Systemic'
                    elif 'Environmental' in class_text:
                        claude_analysis['issue_class'] = 'Environmental'
                    elif 'Component' in class_text:
                        claude_analysis['issue_class'] = 'Component'
                    elif 'Procedural' in class_text:
                        claude_analysis['issue_class'] = 'Procedural'

                elif line.startswith('RESOLUTION_OUTLOOK:'):
                    outlook_text = line.replace('RESOLUTION_OUTLOOK:', '').strip()
                    if 'Challenging' in outlook_text:
                        claude_analysis['resolution_outlook'] = 'Challenging'
                    elif 'Manageable' in outlook_text:
                        claude_analysis['resolution_outlook'] = 'Manageable'
                    elif 'Straightforward' in outlook_text:
                        claude_analysis['resolution_outlook'] = 'Straightforward'

                elif line.startswith('KEY_PHRASE:'):
                    phrase = line.replace('KEY_PHRASE:', '').strip()
                    if phrase.lower() != "none":
                        claude_analysis['key_phrase'] = phrase.strip('"').strip("'")

            # Extract excerpt for key phrase
            claude_excerpt = None
            if claude_analysis.get('key_phrase') and claude_analysis['key_phrase']:
                phrase = claude_analysis['key_phrase']
                phrase_lower = phrase.lower()

                for msg in case_messages:
                    if pd.isna(msg):
                        continue
                    msg_str = str(msg).strip()
                    msg_lower = msg_str.lower()

                    if phrase_lower in msg_lower:
                        phrase_pos = msg_lower.find(phrase_lower)
                        start = max(0, phrase_pos - 250)
                        end = min(len(msg_str), phrase_pos + len(phrase) + 250)

                        excerpt_text = msg_str[start:end].strip()
                        if start > 0:
                            excerpt_text = "..." + excerpt_text
                        if end < len(msg_str):
                            excerpt_text = excerpt_text + "..."

                        excerpt_lower = excerpt_text.lower()
                        phrase_start = excerpt_lower.find(phrase_lower)

                        if phrase_start != -1:
                            before = excerpt_text[:phrase_start]
                            matched = excerpt_text[phrase_start:phrase_start + len(phrase)]
                            after = excerpt_text[phrase_start + len(phrase):]
                            claude_excerpt = f'{before}<font color="#EA580C"><b>{matched}</b></font>{after}'
                        else:
                            claude_excerpt = excerpt_text

                        break

            claude_analysis['excerpt'] = claude_excerpt
            claude_statistics["total_analyzed"] += 1
            claude_statistics["total_frustration_score"] += claude_analysis['frustration_score']

            if claude_analysis['frustration_score'] >= 7:
                claude_statistics["high_frustration"] += 1
            elif claude_analysis['frustration_score'] >= 4:
                claude_statistics["medium_frustration"] += 1
            elif claude_analysis['frustration_score'] >= 1:
                claude_statistics["low_frustration"] += 1
            else:
                claude_statistics["no_frustration"] += 1

        except Exception as e:
            claude_analysis = {
                "frustration_score": 0,
                "frustration_metrics": {
                    'average_score': 0,
                    'peak_score': 0,
                    'frustration_frequency': 0,
                    'frustrated_message_count': 0,
                    'total_messages': len(messages_to_analyze),
                    'message_scores': []
                },
                "issue_class": "Unknown",
                "resolution_outlook": "Unknown",
                "key_phrase": "",
                "excerpt": None,
                "analysis_model": "Claude 3.5 Haiku (Error)",
                "analysis_successful": False,
            }
            claude_statistics["api_errors"] += 1

        # Track issue categories
        issue_category = claude_analysis.get('issue_class', 'Unknown')
        issue_categories[issue_category] = issue_categories.get(issue_category, 0) + 1

        customer_engagement_ratio = 0.6 if interaction_count > 2 else 0.3

        # Build tech map from message signatures
        tech_map = build_tech_map_for_case(case_data)

        # Extract asset serial
        asset_serial_raw = str(first_row.get("Asset Serial", "")).strip()

        case_analysis.append({
            "case_number": int(case_num) if not pd.isna(case_num) else case_num,
            "customer_name": customer_name_case,
            "severity": severity,
            "support_level": support_level,
            "asset_serial": asset_serial_raw,
            "created_date": (
                created_date.strftime("%Y-%m-%d")
                if isinstance(created_date, pd.Timestamp)
                else str(created_date)
            ),
            "last_modified_date": (
                last_modified.strftime("%Y-%m-%d")
                if isinstance(last_modified, pd.Timestamp)
                else str(last_modified)
            ),
            "status": status,
            "case_age_days": case_age,
            "interaction_count": interaction_count,
            "customer_engagement_ratio": float(customer_engagement_ratio),
            "issue_category": issue_category,
            "claude_analysis": claude_analysis,
            "deepseek_analysis": None,
            "messages_full": all_messages_text,
            "case_data": case_data,
            "tech_map": tech_map,
        })

    claude_time = time.time() - start_time
    claude_statistics["analysis_time_seconds"] = claude_time
    claude_statistics["avg_frustration_score"] = (
        claude_statistics["total_frustration_score"] / claude_statistics["total_analyzed"]
        if claude_statistics["total_analyzed"] > 0 else 0
    )

    console_output.stream_message("\n" + "=" * 70)
    console_output.stream_message(f"STAGE 1 COMPLETE: {claude_time:.1f} seconds")
    console_output.stream_message(f"  Analyzed: {claude_statistics['total_analyzed']} cases")
    console_output.stream_message(f"  Total Messages: {claude_statistics['total_messages_analyzed']}")
    msg_pct = (claude_statistics['frustrated_messages_count'] /
               max(1, claude_statistics['total_messages_analyzed']) * 100)
    console_output.stream_message(f"  Frustrated Messages: {claude_statistics['frustrated_messages_count']} ({msg_pct:.1f}%)")
    console_output.stream_message(f"  High Frustration Cases: {claude_statistics['high_frustration']}")
    console_output.stream_message(f"  Average Score: {claude_statistics['avg_frustration_score']:.2f}/10")
    console_output.stream_message("=" * 70 + "\n")

    return case_analysis, claude_statistics, issue_categories, support_level_distribution, claude_time


def run_deepseek_quick_scoring(
    case_analysis: List[Dict],
    analysis_context: str,
    console_output: Any = None,
    account_brief: str = ""
) -> Tuple[Dict, float]:
    """
    Run Claude 3.5 Sonnet quick scoring on top 25 cases.
    Stage 2A of the hybrid analysis - ORIGINAL PROMPT.
    """
    if console_output is None:
        console_output = streaming_output
    if analysis_context is None:
        analysis_context = DEFAULT_ANALYSIS_CONTEXT

    client = get_claude_client()

    console_output.stream_message("\n" + "=" * 70)
    console_output.stream_message("STAGE 2A: CLAUDE 3.5 SONNET - QUICK PATTERN SCORING")

    # Score ALL cases or just top N based on config
    if Config.SONNET_SCORE_ALL_CASES:
        cases_to_score = case_analysis
        console_output.stream_message(f"Scoring ALL {len(cases_to_score)} cases for pattern analysis")
    else:
        cases_to_score = case_analysis[:Config.TOP_N_QUICK_SCORING]
        console_output.stream_message(f"Scoring top {len(cases_to_score)} cases for pattern analysis")

    console_output.stream_message("=" * 70 + "\n")

    start_time = time.time()

    statistics = {
        "total_scored": 0,
        "api_errors": 0,
    }

    for idx, case in enumerate(cases_to_score, 1):
        if idx % 5 == 0 or idx == 1:
            console_output.stream_message(f"[{idx}/{len(cases_to_score)}] Sonnet scoring case {case['case_number']}...")

        # Get message history - prioritize recent messages and key phrases
        messages_full = case.get('messages_full', '')
        haiku_analysis = case.get('claude_analysis', {})
        key_phrase = haiku_analysis.get('key_phrase', '')
        peak_score = haiku_analysis.get('frustration_metrics', {}).get('peak_score', 0)

        # If there's a key phrase with high frustration, include the end of conversation too
        if peak_score >= 7 and len(messages_full) > 12000:
            # Include first 6000 chars + last 6000 chars to catch both context and escalation
            messages_for_deepseek = messages_full[:6000] + "\n\n[...middle messages omitted...]\n\n" + messages_full[-6000:]
        else:
            messages_for_deepseek = messages_full[:12000]

        # ENHANCED SONNET QUICK SCORING PROMPT
        quick_prompt = f"""Assess this customer support case for prioritization scoring.

CASE OVERVIEW:
Customer: {case['customer_name']}
Support Level: {case['support_level']}
Duration: {case['case_age_days']} days
Messages: {case['interaction_count']}
Initial Frustration Score: {haiku_analysis.get('frustration_score', 0)}/10
Peak Frustration Detected: {peak_score}/10
Severity: {case['severity']}

KEY PHRASE DETECTED BY INITIAL ANALYSIS:
"{key_phrase}"

{analysis_context}

CRITICAL SIGNALS TO WATCH FOR:
- Executive involvement: "execs", "management", "CEO", "CTO", "board"
- Replacement threats: "replace", "switch", "consider alternatives"
- Trust erosion: "losing confidence", "disappointed", "concerned"
- Business impact: "production", "downtime", "costing us"

MESSAGE HISTORY (chronological):
{messages_for_deepseek}

SCORING ASSESSMENT:
Based on patterns in the messages AND the key phrase detected, provide:

FRUSTRATION_FREQUENCY: [What % of messages show customer frustration? 0-100]
RELATIONSHIP_DAMAGE_FREQUENCY: [What % of interactions damaged confidence? 0-100]
CUSTOMER_PRIORITY: [Critical/High/Medium/Low based on relationship risk]
JUSTIFICATION: [2-3 sentences explaining priority level]

IMPORTANT: If the key phrase mentions executives, replacement, or impatience, score FRUSTRATION_FREQUENCY at 20+ and mark as High/Critical priority."""

        try:
            response = client.evaluate_prompt(
                prompt=quick_prompt,
                system_message="You are analyzing customer support cases for prioritization. "
                              "Focus on identifying patterns and risk levels efficiently. "
                              "Maintain objective, factual language.",
                llm_name="CLAUDE_V3_5_SONNET"
            )

            content = response.content.strip()

            scoring = {
                'frustration_frequency': 0,
                'damage_frequency': 0,
                'priority': 'Medium',
                'justification': '',
                'analysis_model': 'Claude 3.5 Sonnet Quick Scoring',
                'analysis_successful': True
            }

            for line in content.split('\n'):
                line_stripped = line.strip()
                if 'FRUSTRATION_FREQUENCY:' in line_stripped:
                    nums = [int(s) for s in line_stripped.split() if s.isdigit()]
                    if nums:
                        scoring['frustration_frequency'] = min(100, max(0, nums[0]))
                elif 'RELATIONSHIP_DAMAGE_FREQUENCY:' in line_stripped:
                    nums = [int(s) for s in line_stripped.split() if s.isdigit()]
                    if nums:
                        scoring['damage_frequency'] = min(100, max(0, nums[0]))
                elif 'CUSTOMER_PRIORITY:' in line_stripped:
                    for priority in ['Critical', 'High', 'Medium', 'Low']:
                        if priority in line_stripped:
                            scoring['priority'] = priority
                            break
                elif 'JUSTIFICATION:' in line_stripped:
                    scoring['justification'] = line_stripped.split(':', 1)[1].strip() if ':' in line_stripped else ''

            case['deepseek_quick_scoring'] = scoring
            statistics["total_scored"] += 1

        except Exception as e:
            case['deepseek_quick_scoring'] = {
                'frustration_frequency': 0,
                'damage_frequency': 0,
                'priority': 'Medium',
                'justification': 'Scoring failed',
                'analysis_model': 'Claude 3.5 Sonnet (Error)',
                'analysis_successful': False
            }
            statistics["api_errors"] += 1

    quick_time = time.time() - start_time

    console_output.stream_message(f"\nStage 2A complete: {quick_time:.1f}s")
    console_output.stream_message(f"  Scored: {statistics['total_scored']} cases")

    return statistics, quick_time


def run_deepseek_detailed_timeline(
    case_analysis: List[Dict],
    analysis_context: str,
    console_output: Any = None,
    account_brief: str = "",
    asset_correlations: Dict = None
) -> Tuple[Dict, float]:
    """
    Run Claude 3.5 Sonnet detailed timeline analysis on critical cases.
    Stage 2B: Two-step approach - Timeline first, then Executive Summary.
    ORIGINAL PROMPTS - FRAGILE.
    """
    if console_output is None:
        console_output = streaming_output
    if analysis_context is None:
        analysis_context = DEFAULT_ANALYSIS_CONTEXT

    client = get_claude_client()

    console_output.stream_message("\n" + "=" * 70)
    console_output.stream_message("STAGE 2B: CLAUDE 3.5 SONNET - DETAILED TIMELINES")
    console_output.stream_message(f"Threshold-based selection: Score >= {Config.TIMELINE_SCORE_THRESHOLD}")
    console_output.stream_message("=" * 70 + "\n")

    start_time = time.time()

    # SCORE THRESHOLD SELECTION - cases with combined Haiku+Sonnet score >= threshold
    cases_for_timeline = [
        c for c in case_analysis
        if c.get('criticality_score', 0) >= Config.TIMELINE_SCORE_THRESHOLD
    ]

    # Apply safety cap
    if len(cases_for_timeline) > Config.MAX_TIMELINE_CASES:
        console_output.stream_message(f"  Note: Capping at {Config.MAX_TIMELINE_CASES} cases (had {len(cases_for_timeline)} above threshold)")
        cases_for_timeline = cases_for_timeline[:Config.MAX_TIMELINE_CASES]

    console_output.stream_message(f"Selected {len(cases_for_timeline)} cases scoring >= {Config.TIMELINE_SCORE_THRESHOLD} for detailed timeline")

    statistics = {
        "total_analyzed": 0,
        "api_errors": 0,
    }

    for idx, case in enumerate(cases_for_timeline, 1):
        console_output.stream_message(f"[{idx}/{len(cases_for_timeline)}] Building timeline for case {case['case_number']}...")

        case_data = case.get('case_data')
        if case_data is None or case_data.empty:
            continue

        # Build enhanced message history with ownership (150K to capture all messages)
        enhanced_message_history = build_enhanced_message_history(case_data)[:150000]

        # Asset section
        asset_section = ""
        if asset_correlations and case.get('asset_serial'):
            serial = case['asset_serial']
            if serial in asset_correlations.get('serial_to_cases', {}):
                related = asset_correlations['serial_to_cases'][serial]
                if len(related) > 1:
                    asset_section = f"\nASSET CORRELATION: This asset ({serial}) appears in {len(related)} cases.\n"

        account_brief_full = account_brief[:2500] if account_brief else "Enterprise storage customer."

        # STEP 1: ORIGINAL TIMELINE PROMPT
        timeline_prompt = f"""{account_brief_full}
{asset_section}

Analyze this customer support case to assess relationship health and identify areas requiring attention.

CASE OVERVIEW:
Customer: {case['customer_name']}
Support Level: {case['support_level']}
Issue Severity: {case['severity']}
Case Status: {case['status']}
Case Duration: {case['case_age_days']} days
Message Count: {case['interaction_count']} messages
Initial Assessment: {case['claude_analysis']['frustration_score']}/10 frustration score

{analysis_context}

RESPONSE OWNERSHIP CONTEXT (CRITICAL):
Each message below is marked with [CUSTOMER] or [SUPPORT] and includes delay attribution.

INTERPRETING DELAYS:
- "(Xd delay - SUPPORT responsible)" = Customer sent last message, we took X days to respond
  → This IS a support quality issue if it violates SLA (S1 = same day, S2 = next business day)

- "(Xd delay - CUSTOMER not responding)" = We sent last message, customer took X days to respond
  → This is NOT a support quality issue - customer is not engaging
  → Multiple support follow-ups to silent customer = PROACTIVE support (POSITIVE)
  → Do NOT penalize support for customer non-responsiveness

COMPLETE MESSAGE HISTORY (chronological with ownership):
{enhanced_message_history}

ANALYSIS REQUIREMENTS:

Create a DETAILED chronological timeline covering ALL messages. Use FINE GRANULARITY:
- Group routine messages in small batches (2-8 messages per group)
- Use SINGLE MESSAGE entries for any critical moment: escalations, outages, frustration spikes, executive mentions, failures, resolutions
- A 95-message case should have 15-25+ timeline entries, NOT 5-10

CRITICAL MOMENTS requiring individual Message entries:
- Production outages or incidents
- Executive escalation or mentions ("execs", "management", "CEO")
- Hardware replacement discussions
- Failed remediation attempts
- Customer expressing anxiety, fear, or strong frustration
- Major tone shifts
- Resolution milestones

For each timeline entry, use this format:

TIMELINE_ENTRY: [Messages X-Y - Date: MMM DD-DD, YYYY] OR [Message X - Date: MMM DD, YYYY]
SUMMARY: [Detailed factual description - include specific technical details and customer quotes]
CUSTOMER_TONE: [Observed tone - be specific: "Professional, cooperative", "Anxious, seeking reassurance", "Alarmed, managing crisis"]
FRUSTRATION_DETECTED: [Yes/No]
FRUSTRATION_DETAIL: [If yes: Include the EXACT customer quote in quotation marks, e.g., "Outlook... sigh" or "Our execs are asking at what point we replace the offending Storage Controller"]
POSITIVE_ACTION_DETECTED: [Yes/No]
POSITIVE_ACTION_DETAIL: [If yes: Include specific quote or action, e.g., Msg 3: "Debug attached to case" - customer immediately provided requested data]
SUPPORT_QUALITY: [Assessment with specifics]
RELATIONSHIP_IMPACT: [Effect on customer confidence]
FAILURE_PATTERN_DETECTED: [Yes/No]
FAILURE_PATTERN_DETAIL: [If yes: Show the CHAIN/SEQUENCE, e.g., "Third incident in sequence: Dec 2 outage → Dec 3 failed sync → controller panic" or "67-day case with multiple failed remediation attempts escalating to executive concern"]
ANALYSIS: [For critical moments only - key insight about this interaction, e.g., "clear executive-level frustration and pressure for resolution" or "unplanned production outage from support-recommended action"]

IMPORTANT RULES:
1. Include EXACT customer quotes in quotation marks for frustration and positive actions
2. Track failure patterns as CHAINS showing progression (first incident → second → third)
3. Single-message entries for ANY executive mention, outage, or major escalation
4. Cover ALL messages - verify your last entry includes the final messages
5. For long cases (50+ messages), you MUST have 15+ timeline entries

Base all statements strictly on what appears in the messages. Direct quotes must be verbatim."""

        try:
            # STEP 1: Generate timeline
            timeline_response = client.evaluate_prompt(
                prompt=timeline_prompt,
                system_message="You are an enterprise customer experience analyst providing objective assessments of support interactions. "
                              "Your role is to identify patterns, assess relationship health, and provide actionable insights. "
                              "Maintain a professional, analytical tone suitable for executive review.",
                llm_name="CLAUDE_V3_5_SONNET",
            )

            timeline_content = timeline_response.content.strip()

            # Debug: Log first 500 chars of response to see format
            console_output.stream_message(f"  Response preview: {timeline_content[:300]}...")

            # Parse timeline entries - handle both same-line and multi-line formats
            lines = timeline_content.split('\n')
            timeline_entries = []
            current_timeline_entry = None
            current_field = None  # Track which field we're accumulating content for

            field_markers = {
                'SUMMARY': 'summary',
                'CUSTOMER_TONE': 'customer_tone',
                'CUSTOMER TONE': 'customer_tone',
                'FRUSTRATION_DETECTED': 'frustration_detected',
                'FRUSTRATION DETECTED': 'frustration_detected',
                'FRUSTRATION_DETAIL': 'frustration_detail',
                'FRUSTRATION DETAIL': 'frustration_detail',
                'POSITIVE_ACTION_DETECTED': 'positive_action_detected',
                'POSITIVE ACTION DETECTED': 'positive_action_detected',
                'POSITIVE_ACTION_DETAIL': 'positive_action_detail',
                'POSITIVE ACTION DETAIL': 'positive_action_detail',
                'SUPPORT_QUALITY': 'support_quality',
                'SUPPORT QUALITY': 'support_quality',
                'RELATIONSHIP_IMPACT': 'relationship_impact',
                'RELATIONSHIP IMPACT': 'relationship_impact',
                'FAILURE_PATTERN_DETECTED': 'failure_pattern_detected',
                'FAILURE PATTERN DETECTED': 'failure_pattern_detected',
                'FAILURE_PATTERN_DETAIL': 'failure_pattern_detail',
                'FAILURE PATTERN DETAIL': 'failure_pattern_detail',
                'ANALYSIS': 'analysis',
            }

            for line in lines:
                line_stripped = line.strip()
                if not line_stripped:
                    continue

                # Clean markdown formatting
                line_cleaned = line_stripped.replace('**', '').replace('###', '').replace('##', '').replace('---', '').strip()
                if not line_cleaned:
                    continue

                # Check for new timeline entry
                if 'TIMELINE_ENTRY' in line_cleaned.upper():
                    if current_timeline_entry and current_timeline_entry.get('entry_label'):
                        timeline_entries.append(current_timeline_entry)

                    # Extract entry label - handle various formats
                    entry_label = 'Unknown'
                    if ':' in line_cleaned:
                        parts = line_cleaned.split(':', 1)
                        if len(parts) > 1:
                            entry_label = parts[1].strip().strip('[]')

                    current_timeline_entry = {
                        'entry_label': entry_label,
                        'summary': '',
                        'customer_tone': '',
                        'frustration_detected': '',
                        'frustration_detail': '',
                        'positive_action_detected': '',
                        'positive_action_detail': '',
                        'support_quality': '',
                        'relationship_impact': '',
                        'failure_pattern_detected': '',
                        'failure_pattern_detail': '',
                        'analysis': '',
                        'message_excerpt': None
                    }
                    current_field = None
                    continue

                if current_timeline_entry is not None:
                    # Check if this line starts a new field
                    field_found = False
                    for marker, field in field_markers.items():
                        # Check for marker at start of line (with or without colon)
                        line_upper = line_cleaned.upper()
                        if line_upper.startswith(marker):
                            field_found = True
                            current_field = field
                            # Extract content after the marker
                            content = ''
                            if ':' in line_cleaned:
                                content = line_cleaned.split(':', 1)[1].strip()
                            current_timeline_entry[field] = content
                            break

                    # If no new field marker and we have a current field, append content
                    if not field_found and current_field and line_cleaned:
                        # This is continuation of previous field
                        existing = current_timeline_entry.get(current_field, '')
                        if existing:
                            current_timeline_entry[current_field] = existing + ' ' + line_cleaned
                        else:
                            current_timeline_entry[current_field] = line_cleaned

            if current_timeline_entry and current_timeline_entry.get('entry_label'):
                timeline_entries.append(current_timeline_entry)

            # Debug: Show sample entry content
            if timeline_entries:
                sample = timeline_entries[0]
                console_output.stream_message(f"  Sample entry summary: {sample.get('summary', 'EMPTY')[:100]}...")

            console_output.stream_message(f"  Parsed {len(timeline_entries)} timeline entries")

            # STEP 2: Generate executive summary from timeline
            if len(timeline_entries) > 0:
                timeline_summary = "\n\n".join([
                    f"TIMELINE_ENTRY: {entry.get('entry_label', 'Unknown')}\n"
                    f"Summary: {entry.get('summary', 'N/A')}\n"
                    f"Customer Tone: {entry.get('customer_tone', 'N/A')}\n"
                    f"Frustration: {entry.get('frustration_detected', 'N/A')} - {entry.get('frustration_detail', '')}\n"
                    f"Failure Pattern: {entry.get('failure_pattern_detected', 'N/A')} - {entry.get('failure_pattern_detail', '')}"
                    for entry in timeline_entries
                ])[:15000]

                summary_prompt = f"""Based on the chronological timeline analysis of this support case, provide an executive summary.

CASE CONTEXT:
Customer: {case['customer_name']}
Support Level: {case['support_level']}
Issue Severity: {case['severity']}
Case Status: {case['status']}
Case Duration: {case['case_age_days']} days
Total Messages: {case['interaction_count']}

TIMELINE ANALYSIS:
{timeline_summary}

Provide executive summary using the exact format below:

EXECUTIVE_SUMMARY: [2-3 sentence synthesis for an executive with no context: What happened, current relationship state, and what needs to happen next.]
PAIN_POINTS: [Key customer concerns based on communication patterns - 2-3 sentences]
SENTIMENT_TREND: [Evolution of customer sentiment throughout interaction - 1-2 sentences]
CRITICAL_INFLECTION_POINTS: [2-3 specific moments where relationship trajectory changed]
CUSTOMER_PRIORITY: [Urgency level based on analysis: Critical/High/Medium/Low]
RECOMMENDED_ACTION: [Specific next action to advance or resolve the case - 1-2 sentences]

Base your assessment on the timeline patterns identified above."""

                summary_response = client.evaluate_prompt(
                    prompt=summary_prompt,
                    system_message="You are an enterprise customer experience analyst providing executive insights. "
                                  "Identify patterns, assess relationship health, and provide actionable recommendations.",
                    llm_name="CLAUDE_V3_5_SONNET",
                )

                summary_content = summary_response.content.strip()
            else:
                summary_content = ""

            # Parse executive summary
            deepseek_analysis = {
                "executive_summary": "",
                "pain_points": "",
                "sentiment_trend": "",
                "critical_inflection_points": "",
                "customer_priority": "Medium",
                "recommended_action": "",
                "timeline_entries": timeline_entries,
                "analysis_model": "Claude 3.5 Sonnet",
                "analysis_successful": True,
            }

            # Parse summary fields
            if summary_content:
                field_patterns = {
                    'EXECUTIVE_SUMMARY:': 'executive_summary',
                    'EXECUTIVE SUMMARY:': 'executive_summary',
                    'PAIN_POINTS:': 'pain_points',
                    'PAIN POINTS:': 'pain_points',
                    'SENTIMENT_TREND:': 'sentiment_trend',
                    'SENTIMENT TREND:': 'sentiment_trend',
                    'CRITICAL_INFLECTION_POINTS:': 'critical_inflection_points',
                    'CRITICAL INFLECTION POINTS:': 'critical_inflection_points',
                    'CUSTOMER_PRIORITY:': 'customer_priority',
                    'CUSTOMER PRIORITY:': 'customer_priority',
                    'RECOMMENDED_ACTION:': 'recommended_action',
                    'RECOMMENDED ACTION:': 'recommended_action',
                }

                for line in summary_content.split('\n'):
                    line = line.strip()
                    for pattern, field in field_patterns.items():
                        if pattern in line:
                            value = line.split(':', 1)[1].strip() if ':' in line else ''
                            if field == 'customer_priority':
                                for priority in ['Critical', 'High', 'Medium', 'Low']:
                                    if priority in value:
                                        deepseek_analysis[field] = priority
                                        break
                            else:
                                deepseek_analysis[field] = value
                            break

            # Extract message excerpts for timeline entries
            case_data_sorted = case_data.sort_values('Message Date')
            messages_list = case_data_sorted["Message"].tolist()

            for entry in timeline_entries:
                # Extract frustrated excerpts
                frustration_detail = entry.get('frustration_detail', '')
                quoted_text = re.findall(r'"([^"]+)"', frustration_detail)
                if not quoted_text:
                    quoted_text = re.findall(r"'([^']+)'", frustration_detail)

                if quoted_text and len(quoted_text[0]) > 10:
                    frustrated_quote = quoted_text[0]
                    quote_lower = frustrated_quote.lower()

                    for msg in messages_list:
                        if pd.isna(msg):
                            continue
                        msg_str = str(msg).strip()
                        msg_lower = msg_str.lower()

                        if quote_lower in msg_lower:
                            quote_pos = msg_lower.find(quote_lower)
                            start = max(0, quote_pos - 200)
                            end = min(len(msg_str), quote_pos + len(frustrated_quote) + 200)

                            excerpt_text = msg_str[start:end].strip()
                            if start > 0:
                                excerpt_text = "..." + excerpt_text
                            if end < len(msg_str):
                                excerpt_text = excerpt_text + "..."

                            # HTML escape
                            excerpt_text = excerpt_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                            escaped_quote = frustrated_quote.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

                            excerpt_lower = excerpt_text.lower()
                            escaped_quote_lower = escaped_quote.lower()
                            quote_start = excerpt_lower.find(escaped_quote_lower)

                            if quote_start != -1:
                                before = excerpt_text[:quote_start]
                                matched = excerpt_text[quote_start:quote_start + len(escaped_quote)]
                                after = excerpt_text[quote_start + len(escaped_quote):]

                                frustration_detected = entry.get('frustration_detected', '').lower()
                                color = '#DC2626' if 'yes' in frustration_detected else '#ea580c'

                                entry['message_excerpt'] = f'{before}<font color="{color}"><b>{matched}</b></font>{after}'
                            else:
                                entry['message_excerpt'] = excerpt_text
                            break

                # Extract positive excerpts
                positive_detail = entry.get('positive_action_detail', '')
                quoted_text = re.findall(r'"([^"]+)"', positive_detail)
                if not quoted_text:
                    quoted_text = re.findall(r"'([^']+)'", positive_detail)

                if quoted_text and len(quoted_text[0]) > 10:
                    positive_quote = quoted_text[0]
                    quote_lower = positive_quote.lower()

                    for msg in messages_list:
                        if pd.isna(msg):
                            continue
                        msg_str = str(msg).strip()
                        msg_lower = msg_str.lower()

                        if quote_lower in msg_lower:
                            quote_pos = msg_lower.find(quote_lower)
                            start = max(0, quote_pos - 200)
                            end = min(len(msg_str), quote_pos + len(positive_quote) + 200)

                            excerpt_text = msg_str[start:end].strip()
                            if start > 0:
                                excerpt_text = "..." + excerpt_text
                            if end < len(msg_str):
                                excerpt_text = excerpt_text + "..."

                            excerpt_text = excerpt_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                            escaped_quote = positive_quote.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

                            excerpt_lower = excerpt_text.lower()
                            escaped_quote_lower = escaped_quote.lower()
                            quote_start = excerpt_lower.find(escaped_quote_lower)

                            if quote_start != -1:
                                before = excerpt_text[:quote_start]
                                matched = excerpt_text[quote_start:quote_start + len(escaped_quote)]
                                after = excerpt_text[quote_start + len(escaped_quote):]

                                entry['positive_excerpt'] = f'{before}<font color="#16a34a"><b>{matched}</b></font>{after}'
                            else:
                                entry['positive_excerpt'] = excerpt_text
                            break

            case['deepseek_analysis'] = deepseek_analysis
            statistics["total_analyzed"] += 1

            console_output.stream_message(f"  -> Timeline: {len(timeline_entries)} entries | Priority: {deepseek_analysis['customer_priority']}")

        except Exception as e:
            import traceback
            console_output.stream_message(f"  X Failed: {str(e)}")
            console_output.stream_message(f"    Traceback: {traceback.format_exc()[:200]}")
            case['deepseek_analysis'] = {
                "pain_points": "Analysis failed",
                "sentiment_trend": "Unknown",
                "critical_inflection_points": "",
                "customer_priority": "Medium",
                "recommended_action": "Manual review required",
                "root_cause": "Analysis error",
                "timeline_entries": [],
                "analysis_model": "Claude 3.5 Sonnet (Error)",
                "analysis_successful": False,
            }
            statistics["api_errors"] += 1

    timeline_time = time.time() - start_time

    console_output.stream_message(f"\nStage 2B complete: {timeline_time:.1f}s")
    console_output.stream_message(f"  Timelines generated: {statistics['total_analyzed']}")

    return statistics, timeline_time
