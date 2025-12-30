"""
Timeline Page - View interaction timelines for critical cases
Enhanced headers show key info when collapsed; verbose excerpts show source material
"""

import streamlit as st
import re
import html
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.branding import COLORS, get_frustration_color, get_logo_html
from src.dashboard.styles import get_global_css


def clean_text(text):
    """Remove markdown artifacts and HTML tags from AI output."""
    if not text:
        return ""
    # Handle None string
    if str(text).strip().lower() == 'none':
        return ""
    cleaned = str(text).strip()
    # Remove ** markdown
    while cleaned.startswith('**'):
        cleaned = cleaned[2:].strip()
    while cleaned.endswith('**'):
        cleaned = cleaned[:-2].strip()
    while cleaned.startswith('*'):
        cleaned = cleaned[1:].strip()
    while cleaned.endswith('*'):
        cleaned = cleaned[:-1].strip()
    # Remove HTML tags
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    # Decode HTML entities
    cleaned = html.unescape(cleaned)
    # Clean up any remaining artifacts
    cleaned = cleaned.replace('[cid:', '').replace(']', '')
    return cleaned.strip()


# Apply global styling
st.markdown(get_global_css(), unsafe_allow_html=True)

# Get data from session state
data = st.session_state.get("analysis_data", {})
cases_data = data.get("cases", {})
cases = cases_data.get("cases", [])

if not cases:
    st.warning("No case data available. Please select an analysis from the sidebar.")
    st.stop()

# Filter to cases with timeline entries
cases_with_timelines = [
    c for c in cases
    if (c.get("deepseek_analysis") or {}).get("timeline_entries")
]

if not cases_with_timelines:
    st.info("No detailed timelines available. Timelines are generated for top critical cases during detailed analysis.")
    st.stop()

# Branded header
logo_html = get_logo_html(height=50)
st.markdown(f"""
<div style="background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
            padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;
            border: 1px solid #30363d; border-left: 4px solid #0095D5;">
    <div style="display: flex; align-items: center; gap: 1.5rem;">
        <div>{logo_html}</div>
        <div style="border-left: 2px solid #30363d; padding-left: 1.5rem;">
            <h1 style="color: {COLORS['primary']}; margin: 0; font-size: 1.8rem; font-weight: 600;">Case Timelines</h1>
            <p style="color: #8b949e; margin: 5px 0 0 0; font-size: 1.1rem;">{len(cases_with_timelines)} cases with detailed interaction history</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Case selector
case_options = {
    f"Case {c['case_number']} - {c.get('claude_analysis', {}).get('issue_class', 'Unknown')} (Score: {c.get('criticality_score', 0):.0f})": c
    for c in cases_with_timelines
}

selected_case_label = st.selectbox(
    "Select Case to View Timeline",
    options=list(case_options.keys())
)

selected_case = case_options[selected_case_label]
deepseek = selected_case.get("deepseek_analysis") or {}
timeline_entries = deepseek.get("timeline_entries", [])
claude = selected_case.get("claude_analysis") or {}

# Case header
case_days = selected_case.get("case_age_days", 0)
case_messages = selected_case.get("interaction_count", 0)
frust_score = claude.get('frustration_score', 0)
frust_color = get_frustration_color(frust_score)

st.markdown(f"""
<div style="background-color: {COLORS['surface']}; padding: 15px; border-radius: 8px;
            margin-bottom: 20px; border-left: 4px solid {COLORS['primary']};
            border: 1px solid {COLORS['border']};">
    <h2 style="color: {COLORS['white']}; margin: 0;">CASE #{selected_case.get('case_number')} - INTERACTION TIMELINE</h2>
    <p style="color: {COLORS['text_muted']}; margin: 5px 0 0 0;">
        {case_days} days | {case_messages} messages | {len(timeline_entries)} timeline entries |
        Frustration: <span style="color: {frust_color};">{frust_score}/10</span>
    </p>
</div>
""", unsafe_allow_html=True)

# Case metrics row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Case Number", selected_case.get("case_number"))
with col2:
    st.metric("Criticality Score", f"{selected_case.get('criticality_score', 0):.0f} pts")
with col3:
    st.metric("Frustration Score", f"{claude.get('frustration_score', 0)}/10")
with col4:
    st.metric("Customer", selected_case.get("customer_name", "N/A"))

st.markdown("---")

# Count critical entries for summary
critical_count = sum(1 for e in timeline_entries
                     if "yes" in clean_text(e.get("frustration_detected", "")).lower()
                     or "yes" in clean_text(e.get("failure_pattern_detected", "")).lower())
positive_count = sum(1 for e in timeline_entries
                     if "yes" in clean_text(e.get("positive_action_detected", "")).lower())

st.caption(f"🔴 {critical_count} critical entries | 🟢 {positive_count} positive entries | 🟡 {len(timeline_entries) - critical_count - positive_count} neutral")

# Timeline entries - enhanced headers and verbose content
for i, entry in enumerate(timeline_entries):
    entry_label = clean_text(entry.get('entry_label', f'Entry {i+1}'))
    summary = clean_text(entry.get("summary", "No summary available"))
    customer_tone = clean_text(entry.get("customer_tone", "Unknown"))
    frustration = clean_text(entry.get("frustration_detected", "No"))
    frustration_detail = clean_text(entry.get("frustration_detail", ""))
    positive_action = clean_text(entry.get("positive_action_detected", "No"))
    positive_detail = clean_text(entry.get("positive_action_detail", ""))
    failure_pattern = clean_text(entry.get("failure_pattern_detected", "No"))
    failure_detail = clean_text(entry.get("failure_pattern_detail", ""))
    analysis = clean_text(entry.get("analysis", ""))
    message_excerpt = clean_text(entry.get("message_excerpt", ""))
    positive_excerpt = clean_text(entry.get("positive_excerpt", ""))

    # Determine entry status
    has_frustration = "yes" in frustration.lower()
    has_failure = "yes" in failure_pattern.lower()
    has_positive = "yes" in positive_action.lower()

    # Build informative header that shows key info when collapsed
    if has_frustration or has_failure:
        icon = "🔴"
        status_tag = "CRITICAL"
    elif has_positive:
        icon = "🟢"
        status_tag = "POSITIVE"
    else:
        icon = "🟡"
        status_tag = ""

    # Build header parts
    header_parts = [f"{icon} [{entry_label}]"]

    # Add status indicators
    if has_failure:
        header_parts.append("⚠️ Failure Pattern")
    if has_frustration:
        header_parts.append("😤 Frustrated")
    if has_positive:
        header_parts.append("✅ Positive Action")

    # Add excerpt preview (first 60 chars of most relevant excerpt)
    excerpt_preview = ""
    if message_excerpt and has_frustration:
        excerpt_preview = message_excerpt[:60]
    elif positive_excerpt and has_positive:
        excerpt_preview = positive_excerpt[:60]
    elif summary:
        excerpt_preview = summary[:60]

    if excerpt_preview:
        # Truncate at word boundary if possible
        if len(excerpt_preview) >= 60 and ' ' in excerpt_preview[40:]:
            excerpt_preview = excerpt_preview[:excerpt_preview.rfind(' ', 40)] + "..."
        elif len(excerpt_preview) >= 60:
            excerpt_preview = excerpt_preview[:57] + "..."
        header_parts.append(f'"{excerpt_preview}"')

    expander_title = " | ".join(header_parts)

    # Create collapsible entry - first 3 expanded by default
    with st.expander(expander_title, expanded=(i < 3)):

        # CUSTOMER VOICE SECTION - Most important, show first
        st.markdown(f"<h4 style='color: {COLORS['secondary']}; margin-top: 0;'>Customer Voice</h4>", unsafe_allow_html=True)

        # Use frustration_detail as the customer quote if message_excerpt is empty
        customer_quote = message_excerpt or frustration_detail
        positive_quote = positive_excerpt or positive_detail

        # Always show the customer quote prominently if available
        if customer_quote and has_frustration:
            st.markdown(f"""
            <div style="background-color: #2d2315; border-left: 4px solid {COLORS['warning']};
                        padding: 15px; margin: 10px 0; font-style: italic; color: {COLORS['text']};
                        border-radius: 0 8px 8px 0;">
                <strong style="color: {COLORS['warning']};">Customer Message:</strong><br/>
                "{customer_quote}"
            </div>
            """, unsafe_allow_html=True)
        elif customer_quote:
            st.markdown(f"""
            <div style="background-color: {COLORS['surface']}; border-left: 4px solid {COLORS['gray']};
                        padding: 15px; margin: 10px 0; font-style: italic; color: {COLORS['text']};
                        border-radius: 0 8px 8px 0;">
                <strong style="color: {COLORS['text_muted']};">Customer Message:</strong><br/>
                "{customer_quote}"
            </div>
            """, unsafe_allow_html=True)

        # Show positive excerpt if available
        if positive_quote:
            st.markdown(f"""
            <div style="background-color: #152d15; border-left: 4px solid {COLORS['success']};
                        padding: 15px; margin: 10px 0; font-style: italic; color: {COLORS['text']};
                        border-radius: 0 8px 8px 0;">
                <strong style="color: {COLORS['success']};">Positive Response:</strong><br/>
                "{positive_quote}"
            </div>
            """, unsafe_allow_html=True)

        # If no excerpts, show a note
        if not customer_quote and not positive_quote:
            st.markdown(f"<p style='color: {COLORS['text_muted']}; font-style: italic;'>No direct customer quotes captured for this entry</p>", unsafe_allow_html=True)

        # ANALYSIS SECTION
        st.markdown(f"<h4 style='color: {COLORS['secondary']};'>Analysis</h4>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {COLORS['text']};'><strong>Summary:</strong> {summary}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {COLORS['text']};'><strong>Customer Tone:</strong> {customer_tone}</p>", unsafe_allow_html=True)

        # ISSUES DETECTED SECTION
        if has_frustration or has_failure:
            st.markdown(f"<h4 style='color: {COLORS['secondary']};'>Issues Detected</h4>", unsafe_allow_html=True)

            if has_frustration and frustration_detail:
                st.markdown(f"""
                <div style="background-color: #2d1515; border-left: 4px solid {COLORS['critical']};
                            padding: 10px; margin: 5px 0; color: {COLORS['text']};
                            border-radius: 0 8px 8px 0;">
                    <strong style="color: {COLORS['critical']};">😤 Frustration:</strong> {frustration_detail}
                </div>
                """, unsafe_allow_html=True)

            if has_failure and failure_detail:
                st.markdown(f"""
                <div style="background-color: #2d1515; border-left: 4px solid {COLORS['critical']};
                            padding: 10px; margin: 5px 0; color: {COLORS['text']};
                            border-radius: 0 8px 8px 0;">
                    <strong style="color: {COLORS['critical']};">⚠️ Failure Pattern:</strong> {failure_detail}
                </div>
                """, unsafe_allow_html=True)

        # AI Analysis insight
        if analysis:
            st.markdown(f"<h4 style='color: {COLORS['secondary']};'>AI Insight</h4>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background-color: {COLORS['surface']}; border-left: 4px solid {COLORS['gray']};
                        padding: 10px; margin: 5px 0; color: {COLORS['text']};
                        border-radius: 0 8px 8px 0;">
                {analysis}
            </div>
            """, unsafe_allow_html=True)

        # POSITIVE ACTIONS SECTION
        if has_positive and positive_detail:
            st.markdown(f"<h4 style='color: {COLORS['secondary']};'>Positive Actions</h4>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background-color: #152d15; border-left: 4px solid {COLORS['success']};
                        padding: 10px; margin: 5px 0; color: {COLORS['text']};
                        border-radius: 0 8px 8px 0;">
                ✅ {positive_detail}
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# Key Customer Quote section
key_phrase = claude.get("key_phrase", "")
if key_phrase and len(key_phrase) > 10:
    st.markdown(f"""
    <div style="background-color: {COLORS['surface']}; padding: 15px; border-radius: 8px;
                margin-top: 20px; border: 1px solid {COLORS['border']};">
        <h3 style="color: {COLORS['critical']}; margin: 0;">KEY CUSTOMER QUOTE</h3>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"""
    <div style="color: {COLORS['text']}; font-size: 1.2em; font-style: italic; padding: 15px;
                border-left: 4px solid {COLORS['critical']}; background-color: #2d1515;
                border-radius: 0 8px 8px 0;">
        "{clean_text(key_phrase)}"
    </div>
    """, unsafe_allow_html=True)

# AI Executive Summary section
st.markdown("---")
st.markdown(f"<h3 style='color: {COLORS['secondary']};'>AI Executive Summary</h3>", unsafe_allow_html=True)

# Executive Summary prominently displayed (fall back to root_cause for old analyses)
exec_summary = clean_text(deepseek.get("executive_summary", "")) or clean_text(deepseek.get("root_cause", ""))
if exec_summary and len(exec_summary) > 10:
    st.markdown(f"""
    <div style="background-color: {COLORS['surface']}; border-left: 4px solid {COLORS['primary']};
                padding: 15px; margin: 10px 0; color: {COLORS['text']}; font-size: 1.1em;
                border-radius: 0 8px 8px 0;">
        {exec_summary}
    </div>
    """, unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"<strong style='color: {COLORS['text']};'>Pain Points</strong>", unsafe_allow_html=True)
    pain_points = clean_text(deepseek.get("pain_points", "None identified"))
    st.markdown(f"""
    <div style="background-color: #2d1515; border-left: 4px solid {COLORS['critical']};
                padding: 10px; margin: 5px 0; color: {COLORS['text']};
                border-radius: 0 8px 8px 0;">
        {pain_points}
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"<strong style='color: {COLORS['text']};'>Sentiment Trend</strong>", unsafe_allow_html=True)
    sentiment = clean_text(deepseek.get("sentiment_trend", "Unknown"))
    st.markdown(f"<p style='color: {COLORS['text']};'>{sentiment}</p>", unsafe_allow_html=True)

with col2:
    st.markdown(f"<strong style='color: {COLORS['text']};'>Recommended Action</strong>", unsafe_allow_html=True)
    action = clean_text(deepseek.get("recommended_action", "No recommendation"))
    st.markdown(f"""
    <div style="background-color: #152d15; border: 2px solid {COLORS['accent']};
                padding: 10px; margin: 5px 0; border-radius: 8px; color: {COLORS['text']};">
        <strong style="color: {COLORS['accent']};">ACTION:</strong> {action}
    </div>
    """, unsafe_allow_html=True)

# Critical inflection points
inflection = clean_text(deepseek.get("critical_inflection_points", ""))
if inflection and len(inflection) > 5:
    st.markdown(f"<strong style='color: {COLORS['text']};'>Critical Inflection Points</strong>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background-color: #2d2315; border-left: 4px solid {COLORS['warning']};
                padding: 10px; margin: 5px 0; color: {COLORS['text']};
                border-radius: 0 8px 8px 0;">
        {inflection}
    </div>
    """, unsafe_allow_html=True)
