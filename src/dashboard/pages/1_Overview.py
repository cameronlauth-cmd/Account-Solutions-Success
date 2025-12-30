"""
Overview Page - Health score gauge and key metrics
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.branding import COLORS, get_health_color, get_health_status, get_logo_html
from src.dashboard.styles import get_global_css

# Apply global styling
st.markdown(get_global_css(), unsafe_allow_html=True)

# Get data from session state
data = st.session_state.get("analysis_data", {})
summary = data.get("summary", {})

if not summary:
    st.warning("No analysis data loaded. Please select an analysis from the sidebar.")
    st.stop()

# Branded header
account_name = summary.get("account_name", "Unknown")
analysis_date = summary.get('analysis_date', 'N/A')

logo_html = get_logo_html(height=50)
st.markdown(f"""
<div style="background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
            padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;
            border: 1px solid #30363d; border-left: 4px solid #0095D5;">
    <div style="display: flex; align-items: center; gap: 1.5rem;">
        <div>{logo_html}</div>
        <div style="border-left: 2px solid #30363d; padding-left: 1.5rem;">
            <h1 style="color: {COLORS['primary']}; margin: 0; font-size: 1.8rem; font-weight: 600;">Account Health Report</h1>
            <p style="color: #8b949e; margin: 5px 0 0 0; font-size: 1.1rem;">{account_name} | {analysis_date}</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Health Score Section
health_score = summary.get("account_health_score", 0)
health_color = get_health_color(health_score)
health_status = get_health_status(health_score)

# Determine status description
if health_score >= 80:
    status_desc = "Healthy - Low Risk"
elif health_score >= 60:
    status_desc = "At Risk - Monitor Closely"
elif health_score >= 40:
    status_desc = "Moderate Risk - Action Recommended"
else:
    status_desc = "Critical - Immediate Action Required"

# Create gauge chart with dark theme
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=health_score,
    number={'font': {'color': health_color, 'size': 48}},
    domain={'x': [0, 1], 'y': [0, 1]},
    title={'text': f"<b style='color:{COLORS['white']}'>{account_name}</b><br><span style='font-size:0.8em;color:{health_color}'>{status_desc}</span>",
           'font': {'color': COLORS['white']}},
    gauge={
        'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': COLORS['text_muted'],
                 'tickfont': {'color': COLORS['text_muted']}},
        'bar': {'color': health_color},
        'bgcolor': COLORS['surface'],
        'borderwidth': 2,
        'bordercolor': COLORS['border'],
        'steps': [
            {'range': [0, 40], 'color': '#2d1515'},
            {'range': [40, 60], 'color': '#2d2315'},
            {'range': [60, 80], 'color': '#1a2d30'},
            {'range': [80, 100], 'color': '#152d15'}
        ],
        'threshold': {
            'line': {'color': COLORS['white'], 'width': 3},
            'thickness': 0.75,
            'value': health_score
        }
    }
))

fig_gauge.update_layout(
    height=320,
    paper_bgcolor=COLORS['background'],
    plot_bgcolor=COLORS['background'],
    font={'color': COLORS['white']}
)
st.plotly_chart(fig_gauge, use_container_width=True)

# Key Metrics Row
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Key Metrics
</h2>
""", unsafe_allow_html=True)

claude_stats = summary.get("claude_statistics", {})

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Cases",
        summary.get("total_cases", 0),
        help="Total number of support cases analyzed"
    )

with col2:
    high_frust = claude_stats.get("high_frustration", 0)
    st.metric(
        "High Frustration",
        high_frust,
        delta=f"-{high_frust}" if high_frust > 0 else None,
        delta_color="inverse",
        help="Cases with frustration score >= 7"
    )

with col3:
    avg_frust = claude_stats.get("avg_frustration_score", 0)
    st.metric(
        "Avg Frustration",
        f"{avg_frust:.1f}/10",
        help="Average frustration score across all cases"
    )

with col4:
    frustrated_pct = 0
    total_msgs = claude_stats.get("total_messages_analyzed", 0)
    frustrated_msgs = claude_stats.get("frustrated_messages_count", 0)
    if total_msgs > 0:
        frustrated_pct = (frustrated_msgs / total_msgs) * 100
    st.metric(
        "Frustrated Messages",
        f"{frustrated_pct:.1f}%",
        help=f"{frustrated_msgs} of {total_msgs} messages showed frustration"
    )

st.markdown("---")

# Score Breakdown
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Health Score Breakdown
</h2>
""", unsafe_allow_html=True)

score_breakdown = summary.get("score_breakdown", {})

if score_breakdown:
    # Maximum points per category
    MAX_POINTS = {
        "Frustration": 30,
        "High Frustration": 20,
        "Critical Case Load": 20,
        "Systemic Issues": 15,
        "Resolution Complexity": 15,
    }

    # Get earned points per category
    earned = {
        "Frustration": score_breakdown.get("frustration_component", 30),
        "High Frustration": score_breakdown.get("high_frustration_penalty", 20),
        "Critical Case Load": score_breakdown.get("critical_load_component", 20),
        "Systemic Issues": score_breakdown.get("systemic_issues_component", 15),
        "Resolution Complexity": score_breakdown.get("resolution_complexity_component", 15),
    }

    # Calculate points LOST per category
    losses = {name: MAX_POINTS[name] - earned[name] for name in MAX_POINTS}

    # Get base score and temporal penalty
    base_score = score_breakdown.get("base_health_score", health_score)
    temporal_penalty = score_breakdown.get("temporal_clustering_penalty", 0)

    # Show the score calculation flow
    st.markdown("#### Score Calculation")

    # Base score explanation
    total_earned = sum(earned.values())
    total_lost = sum(losses.values())

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Base Score", f"{base_score:.0f}/100",
                  help="Sum of points earned across all categories")
    with col2:
        if temporal_penalty > 0:
            penalty_pct = temporal_penalty * 100
            st.metric("Temporal Penalty", f"-{penalty_pct:.0f}%",
                      help="Penalty for multiple concerning cases in short timeframe")
        else:
            st.metric("Temporal Penalty", "None",
                      help="No penalty - cases are spread out over time")
    with col3:
        st.metric("Final Health Score", f"{health_score:.0f}/100",
                  delta=f"{health_score - 100:.0f}" if health_score < 100 else None,
                  delta_color="inverse")

    if temporal_penalty > 0:
        st.caption(f"*Final Score = Base Score ({base_score:.0f}) × (1 - {temporal_penalty*100:.0f}% penalty) = {health_score:.0f}*")

    st.markdown("---")
    st.markdown("#### Points Lost by Category")

    # Filter to only show categories with losses
    loss_items = [(name, loss) for name, loss in losses.items() if loss > 0.5]

    if loss_items:
        names = [item[0] for item in loss_items]
        values = [item[1] for item in loss_items]

        fig_breakdown = go.Figure(go.Bar(
            x=values,
            y=names,
            orientation='h',
            marker_color=COLORS['critical'],
            text=[f"-{v:.1f} pts" for v in values],
            textposition='outside',
            textfont={'color': COLORS['text']}
        ))

        fig_breakdown.update_layout(
            xaxis_title="Points Lost (from max possible)",
            yaxis_title="",
            height=max(200, len(loss_items) * 50),
            margin=dict(l=0, r=60, t=10, b=40),
            xaxis=dict(range=[0, max(values) * 1.3], color=COLORS['text_muted']) if values else None,
            yaxis=dict(color=COLORS['text']),
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']}
        )

        st.plotly_chart(fig_breakdown, use_container_width=True)

        # Show the math
        st.markdown(f"<p style='color: {COLORS['text_muted']}; font-style: italic;'>Total points lost: {total_lost:.1f} → Base score: 100 - {total_lost:.1f} = {base_score:.0f}</p>", unsafe_allow_html=True)
    else:
        st.success("No significant deductions - account is in excellent health!")

st.markdown("---")

# Two-column layout for distributions
col1, col2 = st.columns(2)

with col1:
    st.markdown(f"<h3 style='color: {COLORS['secondary']};'>Severity Distribution</h3>", unsafe_allow_html=True)
    severity_dist = summary.get("severity_distribution", {})

    if severity_dist:
        # Order by severity
        ordered_sev = ["S1", "S2", "S3", "S4"]
        labels = [s for s in ordered_sev if s in severity_dist]
        values = [severity_dist[s] for s in labels]

        colors = {
            "S1": COLORS['critical'],
            "S2": "#fd7e14",
            "S3": COLORS['warning'],
            "S4": COLORS['success'],
        }

        fig_severity = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker_colors=[colors.get(s, COLORS['gray']) for s in labels],
            textfont={'color': COLORS['white']}
        )])

        fig_severity.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            legend={'font': {'color': COLORS['text']}}
        )

        st.plotly_chart(fig_severity, use_container_width=True)
    else:
        st.info("No severity data available")

with col2:
    st.markdown(f"<h3 style='color: {COLORS['secondary']};'>Support Level Distribution</h3>", unsafe_allow_html=True)
    support_dist = summary.get("support_level_distribution", {})

    if support_dist:
        labels = list(support_dist.keys())
        values = list(support_dist.values())

        colors = {
            "Gold": "#ffd700",
            "Silver": "#c0c0c0",
            "Bronze": "#cd7f32",
        }

        fig_support = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker_colors=[colors.get(s, COLORS['gray']) for s in labels],
            textfont={'color': COLORS['white']}
        )])

        fig_support.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            legend={'font': {'color': COLORS['text']}}
        )

        st.plotly_chart(fig_support, use_container_width=True)
    else:
        st.info("No support level data available")

# Analysis metadata
st.markdown("---")
st.markdown(f"""
<h3 style="color: {COLORS['secondary']};">Analysis Details</h3>
""", unsafe_allow_html=True)

deepseek_stats = summary.get("deepseek_statistics", {})

st.markdown(f"""
<div style="background-color: {COLORS['surface']}; padding: 1rem; border-radius: 8px;
            border: 1px solid {COLORS['border']};">
    <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
        <div>
            <span style="color: {COLORS['text_muted']}; font-size: 0.85rem;">Analysis Date</span><br>
            <span style="color: {COLORS['text']}; font-weight: 600;">{summary.get('analysis_date', 'N/A')}</span>
        </div>
        <div>
            <span style="color: {COLORS['text_muted']}; font-size: 0.85rem;">Processing Time</span><br>
            <span style="color: {COLORS['text']}; font-weight: 600;">{summary.get('analysis_time_seconds', 0):.0f} seconds</span>
        </div>
        <div>
            <span style="color: {COLORS['text_muted']}; font-size: 0.85rem;">Cases Analyzed</span><br>
            <span style="color: {COLORS['text']}; font-weight: 600;">{summary.get('total_cases', 0)}</span>
        </div>
        <div>
            <span style="color: {COLORS['text_muted']}; font-size: 0.85rem;">Detailed Timelines</span><br>
            <span style="color: {COLORS['text']}; font-weight: 600;">{deepseek_stats.get('total_analyzed', 0)}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
