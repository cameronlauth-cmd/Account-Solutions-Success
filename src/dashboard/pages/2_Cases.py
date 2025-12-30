"""
Cases Page - Browse all cases with AI analysis details
Click a row in the table to view detailed analysis.
"""

import streamlit as st
import pandas as pd
import re
import html
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.branding import COLORS, get_health_color, get_frustration_color, get_logo_html
from src.dashboard.styles import get_global_css


def clean_text(text):
    """Remove markdown artifacts and HTML tags from AI output."""
    if not text:
        return ""
    cleaned = str(text).strip()
    # Remove ** markdown
    while cleaned.startswith('**'):
        cleaned = cleaned[2:].strip()
    while cleaned.endswith('**'):
        cleaned = cleaned[:-2].strip()
    # Remove HTML tags
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    # Decode HTML entities
    cleaned = html.unescape(cleaned)
    return cleaned


# Apply global styling
st.markdown(get_global_css(), unsafe_allow_html=True)

# Get data from session state
data = st.session_state.get("analysis_data", {})
cases_data = data.get("cases", {})
cases = cases_data.get("cases", [])

if not cases:
    st.warning("No case data available. Please select an analysis from the sidebar.")
    st.stop()

# Branded header
account_name = cases_data.get('account_name', 'Unknown')
analysis_date = cases_data.get('analysis_date', 'N/A')

logo_html = get_logo_html(height=50)
st.markdown(f"""
<div style="background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
            padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;
            border: 1px solid #30363d; border-left: 4px solid #0095D5;">
    <div style="display: flex; align-items: center; gap: 1.5rem;">
        <div>{logo_html}</div>
        <div style="border-left: 2px solid #30363d; padding-left: 1.5rem;">
            <h1 style="color: {COLORS['primary']}; margin: 0; font-size: 1.8rem; font-weight: 600;">Case Browser</h1>
            <p style="color: #8b949e; margin: 5px 0 0 0; font-size: 1.1rem;">{account_name} | {analysis_date}</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Filters in sidebar
st.sidebar.markdown("### Filters")

# Severity filter
severities = list(set(c.get("severity", "Unknown") for c in cases))
selected_severities = st.sidebar.multiselect(
    "Severity",
    options=sorted(severities),
    default=sorted(severities)
)

# Status filter
statuses = list(set(c.get("status", "Unknown") for c in cases))
selected_statuses = st.sidebar.multiselect(
    "Status",
    options=sorted(statuses),
    default=sorted(statuses)
)

# Frustration filter
min_frustration = st.sidebar.slider(
    "Min Frustration Score",
    min_value=0,
    max_value=10,
    value=0
)

# Filter cases
filtered_cases = [
    c for c in cases
    if c.get("severity") in selected_severities
    and c.get("status") in selected_statuses
    and (c.get("claude_analysis") or {}).get("frustration_score", 0) >= min_frustration
]

st.markdown(f"Showing **{len(filtered_cases)}** of {len(cases)} cases")
st.caption("Click a row to view detailed AI analysis below")

# Create summary table with row selection
if filtered_cases:
    table_data = []
    for case in filtered_cases:
        claude = case.get("claude_analysis") or {}
        deepseek = case.get("deepseek_analysis") or {}

        table_data.append({
            "Case #": case.get("case_number"),
            "Severity": case.get("severity"),
            "Support": case.get("support_level"),
            "Status": case.get("status"),
            "Age": case.get("case_age_days"),
            "Frustration": claude.get('frustration_score', 0),
            "Criticality": case.get("criticality_score", 0),
            "Issue Type": claude.get("issue_class", "Unknown"),
        })

    df = pd.DataFrame(table_data)

    # Display as interactive table with row selection
    selection = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        column_config={
            "Case #": st.column_config.NumberColumn(format="%d"),
            "Age": st.column_config.NumberColumn(format="%d days"),
            "Frustration": st.column_config.ProgressColumn(
                min_value=0,
                max_value=10,
                format="%d/10"
            ),
            "Criticality": st.column_config.ProgressColumn(
                min_value=0,
                max_value=200,
                format="%d pts"
            ),
        }
    )

    # Get selected case from row selection
    selected_idx = None
    if selection and hasattr(selection, 'selection') and selection.selection.rows:
        selected_idx = selection.selection.rows[0]

    # Default to first case if none selected
    if selected_idx is not None:
        selected_case = filtered_cases[selected_idx]
    else:
        selected_case = filtered_cases[0]
        st.info("Select a row above to view case details")

    st.markdown("---")

    # Case Header
    claude = selected_case.get("claude_analysis") or {}
    deepseek = selected_case.get("deepseek_analysis") or {}

    case_num = selected_case.get('case_number')
    issue_class = claude.get('issue_class', 'Unknown')
    crit_score = selected_case.get('criticality_score', 0)
    frust_score = claude.get('frustration_score', 0)
    age_days = selected_case.get('case_age_days', 0)

    # Determine frustration color
    frust_color = get_frustration_color(frust_score)

    # Prominent case header with branded styling
    st.markdown(f"""
    <div style="background-color: {COLORS['surface']}; padding: 20px; border-radius: 8px;
                margin-bottom: 20px; border-left: 4px solid {COLORS['primary']};
                border: 1px solid {COLORS['border']};">
        <h2 style="color: {COLORS['white']}; margin: 0;">CASE #{case_num} - {issue_class}</h2>
        <p style="color: {COLORS['text_muted']}; margin: 5px 0 0 0;">
            Criticality: <b style="color: {COLORS['white']};">{crit_score:.0f} pts</b> |
            Frustration: <b style="color: {frust_color};">{frust_score}/10</b> |
            Age: <b style="color: {COLORS['white']};">{age_days} days</b> |
            Status: <b style="color: {COLORS['secondary']};">{selected_case.get('status')}</b>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Quick metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Customer", selected_case.get('customer_name', 'N/A'))
    with col2:
        st.metric("Severity", selected_case.get('severity'))
    with col3:
        st.metric("Support Level", selected_case.get('support_level'))
    with col4:
        st.metric("Resolution Outlook", claude.get('resolution_outlook', 'Unknown'))

    st.markdown("---")

    # AI ANALYSIS SECTION - Verbose and prominent
    st.markdown(f"""
    <h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
        AI Analysis
    </h2>
    """, unsafe_allow_html=True)

    # EXECUTIVE SUMMARY - Most important, show first
    # Fall back to root_cause for backward compatibility with old analyses
    exec_summary = clean_text(deepseek.get("executive_summary", "")) or clean_text(deepseek.get("root_cause", ""))
    if exec_summary and len(exec_summary) > 10:
        st.markdown(f"<h3 style='color: {COLORS['secondary']};'>Executive Summary</h3>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background-color: {COLORS['surface']}; border-left: 4px solid {COLORS['primary']};
                    padding: 15px; margin: 10px 0; font-size: 1.1em; color: {COLORS['text']};
                    border-radius: 0 8px 8px 0;">
            {exec_summary}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"<h3 style='color: {COLORS['secondary']};'>Executive Summary</h3>", unsafe_allow_html=True)
        st.info("No executive summary available for this case")

    # PAIN POINTS
    pain_points = clean_text(deepseek.get("pain_points", ""))
    if pain_points and len(pain_points) > 10:
        st.markdown(f"<h3 style='color: {COLORS['secondary']};'>Pain Points</h3>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background-color: #2d1515; border-left: 4px solid {COLORS['critical']};
                    padding: 15px; margin: 10px 0; color: {COLORS['text']};
                    border-radius: 0 8px 8px 0;">
            {pain_points}
        </div>
        """, unsafe_allow_html=True)

    # SENTIMENT TREND with visual indicator
    sentiment = clean_text(deepseek.get("sentiment_trend", ""))
    if sentiment and len(sentiment) > 5:
        st.markdown(f"<h3 style='color: {COLORS['secondary']};'>Sentiment Trend</h3>", unsafe_allow_html=True)
        # Determine trend direction
        sentiment_lower = sentiment.lower()
        if "declin" in sentiment_lower or "worsen" in sentiment_lower or "increas" in sentiment_lower and "frustrat" in sentiment_lower:
            trend_icon = "📉"
            trend_color = COLORS['critical']
        elif "improv" in sentiment_lower or "resolv" in sentiment_lower or "better" in sentiment_lower:
            trend_icon = "📈"
            trend_color = COLORS['success']
        else:
            trend_icon = "📊"
            trend_color = COLORS['warning']

        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; padding: 15px;
                    border-left: 4px solid {trend_color}; background-color: {COLORS['surface']};
                    color: {COLORS['text']}; border-radius: 0 8px 8px 0;">
            <span style="font-size: 2em;">{trend_icon}</span>
            <span>{sentiment}</span>
        </div>
        """, unsafe_allow_html=True)

    # RECOMMENDED ACTION - Call to action box (uses accent green)
    recommendation = clean_text(deepseek.get("recommended_action", ""))
    if recommendation and len(recommendation) > 10:
        st.markdown(f"<h3 style='color: {COLORS['secondary']};'>Recommended Action</h3>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background-color: #152d15; border: 2px solid {COLORS['accent']};
                    padding: 15px; margin: 10px 0; border-radius: 8px; color: {COLORS['text']};">
            <strong style="color: {COLORS['accent']};">ACTION REQUIRED:</strong><br/>
            {recommendation}
        </div>
        """, unsafe_allow_html=True)

    # KEY CUSTOMER QUOTE
    key_phrase = clean_text(claude.get("key_phrase", ""))
    if key_phrase and len(key_phrase) > 10:
        st.markdown(f"<h3 style='color: {COLORS['secondary']};'>Key Customer Quote</h3>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background-color: {COLORS['surface']}; border-left: 4px solid {COLORS['warning']};
                    padding: 15px; margin: 10px 0; font-style: italic; font-size: 1.1em;
                    color: {COLORS['text']}; border-radius: 0 8px 8px 0;">
            "{key_phrase}"
        </div>
        """, unsafe_allow_html=True)

    # CRITICAL INFLECTION POINTS
    inflection = clean_text(deepseek.get("critical_inflection_points", ""))
    if inflection and len(inflection) > 10:
        st.markdown(f"<h3 style='color: {COLORS['secondary']};'>Critical Inflection Points</h3>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background-color: #2d2315; border-left: 4px solid {COLORS['warning']};
                    padding: 15px; margin: 10px 0; color: {COLORS['text']};
                    border-radius: 0 8px 8px 0;">
            {inflection}
        </div>
        """, unsafe_allow_html=True)

    # Frustration Metrics
    st.markdown("---")
    st.markdown(f"<h3 style='color: {COLORS['secondary']};'>Frustration Metrics</h3>", unsafe_allow_html=True)

    metrics = claude.get("frustration_metrics", {})
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Overall Score", f"{frust_score}/10")
    with col2:
        st.metric("Peak Score", f"{metrics.get('peak_score', 0)}/10")
    with col3:
        total_msgs = metrics.get('total_messages', 0)
        frust_msgs = metrics.get('frustrated_message_count', 0)
        st.metric("Frustrated Messages", f"{frust_msgs}/{total_msgs}")
    with col4:
        if total_msgs > 0:
            frust_pct = (frust_msgs / total_msgs) * 100
        else:
            frust_pct = 0
        st.metric("Frustration Rate", f"{frust_pct:.0f}%")

    # Message-level scores (collapsible)
    message_scores = metrics.get("message_scores", [])
    if message_scores:
        with st.expander(f"View Message-Level Scores ({len(message_scores)} messages)", expanded=False):
            msg_data = []
            for msg in message_scores:
                score = msg.get("score", 0)
                if score >= 7:
                    indicator = "🔴"
                elif score >= 4:
                    indicator = "🟡"
                else:
                    indicator = "🟢"

                msg_data.append({
                    "Msg": msg.get("msg"),
                    "": indicator,
                    "Score": f"{score}/10",
                    "Reason": msg.get("reason", "")
                })

            msg_df = pd.DataFrame(msg_data)
            st.dataframe(msg_df, use_container_width=True, hide_index=True)

    # Link to Timeline if available
    if deepseek.get("timeline_entries"):
        st.markdown("---")
        st.info(f"This case has detailed timeline analysis. Go to **Timeline** page to view the full interaction history.")

else:
    st.info("No cases match the current filters")
