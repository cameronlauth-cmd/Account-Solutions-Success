"""
Trends Page - Visualize patterns over time
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path
import sys

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.branding import COLORS, get_logo_html
from src.dashboard.styles import get_global_css

# Apply global styling
st.markdown(get_global_css(), unsafe_allow_html=True)

# Get data from session state
data = st.session_state.get("analysis_data", {})
cases_data = data.get("cases", {})
cases = cases_data.get("cases", [])
summary = data.get("summary", {})
charts = data.get("charts", {})

if not cases:
    st.warning("No case data available. Please select an analysis from the sidebar.")
    st.stop()

# Branded header
account_name = cases_data.get("account_name", "Unknown")

logo_html = get_logo_html(height=50)
st.markdown(f"""
<div style="background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
            padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;
            border: 1px solid #30363d; border-left: 4px solid #0095D5;">
    <div style="display: flex; align-items: center; gap: 1.5rem;">
        <div>{logo_html}</div>
        <div style="border-left: 2px solid #30363d; padding-left: 1.5rem;">
            <h1 style="color: {COLORS['primary']}; margin: 0; font-size: 1.8rem; font-weight: 600;">Trends & Patterns</h1>
            <p style="color: #8b949e; margin: 5px 0 0 0; font-size: 1.1rem;">{account_name} | Case Analytics</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Prepare data for charts
df_cases = pd.DataFrame([
    {
        "case_number": c.get("case_number"),
        "created_date": pd.to_datetime(c.get("created_date")),
        "severity": c.get("severity"),
        "frustration": (c.get("claude_analysis") or {}).get("frustration_score", 0),
        "criticality": c.get("criticality_score", 0),
        "issue_class": (c.get("claude_analysis") or {}).get("issue_class", "Unknown"),
        "status": c.get("status"),
        "support_level": c.get("support_level"),
    }
    for c in cases
])

# Top Critical Cases Chart
st.markdown(f"<h2 style='color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;'>Top Critical Cases</h2>", unsafe_allow_html=True)

top_cases = df_cases.nlargest(10, 'criticality')

fig_critical = go.Figure(go.Bar(
    x=top_cases['criticality'],
    y=[f"Case {cn}" for cn in top_cases['case_number']],
    orientation='h',
    marker_color=[COLORS['critical'] if c >= 180 else COLORS['warning'] if c >= 100 else COLORS['success'] for c in top_cases['criticality']],
    text=[f"{c:.0f}" for c in top_cases['criticality']],
    textposition='outside',
    textfont={'color': COLORS['text']}
))

fig_critical.update_layout(
    yaxis={'categoryorder': 'total ascending', 'color': COLORS['text']},
    xaxis_title="Criticality Score",
    xaxis={'color': COLORS['text_muted']},
    height=400,
    margin=dict(l=0, r=50, t=20, b=40),
    paper_bgcolor=COLORS['background'],
    plot_bgcolor=COLORS['background'],
    font={'color': COLORS['text']}
)

st.plotly_chart(fig_critical, use_container_width=True)

st.markdown("---")

# Two-column layout
col1, col2 = st.columns(2)

with col1:
    st.markdown(f"<h3 style='color: {COLORS['secondary']};'>Frustration Distribution</h3>", unsafe_allow_html=True)

    # Create histogram of frustration scores
    fig_frust = px.histogram(
        df_cases,
        x='frustration',
        nbins=10,
        color_discrete_sequence=[COLORS['primary']]
    )

    fig_frust.update_layout(
        xaxis_title="Frustration Score (0-10)",
        yaxis_title="Number of Cases",
        bargap=0.1,
        height=300,
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['background'],
        font={'color': COLORS['text']},
        xaxis={'color': COLORS['text_muted']},
        yaxis={'color': COLORS['text_muted']}
    )

    st.plotly_chart(fig_frust, use_container_width=True)

with col2:
    st.markdown(f"<h3 style='color: {COLORS['secondary']};'>Issue Categories</h3>", unsafe_allow_html=True)

    issue_counts = df_cases['issue_class'].value_counts()

    fig_issues = go.Figure(data=[go.Pie(
        labels=issue_counts.index,
        values=issue_counts.values,
        hole=0.4,
        textfont={'color': COLORS['white']}
    )])

    fig_issues.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['background'],
        font={'color': COLORS['text']},
        legend={'font': {'color': COLORS['text']}}
    )

    st.plotly_chart(fig_issues, use_container_width=True)

st.markdown("---")

# Severity vs Frustration scatter
st.markdown(f"<h2 style='color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;'>Severity vs Frustration Analysis</h2>", unsafe_allow_html=True)

severity_order = {"S1": 1, "S2": 2, "S3": 3, "S4": 4}
df_cases['severity_num'] = df_cases['severity'].map(severity_order)

fig_scatter = px.scatter(
    df_cases,
    x='severity',
    y='frustration',
    size='criticality',
    color='issue_class',
    hover_data=['case_number', 'status'],
)

fig_scatter.update_layout(
    xaxis_title="Severity",
    yaxis_title="Frustration Score",
    height=400,
    paper_bgcolor=COLORS['background'],
    plot_bgcolor=COLORS['surface'],
    font={'color': COLORS['text']},
    xaxis={'color': COLORS['text_muted'], 'gridcolor': COLORS['border']},
    yaxis={'color': COLORS['text_muted'], 'gridcolor': COLORS['border']},
    legend={'font': {'color': COLORS['text']}}
)

st.plotly_chart(fig_scatter, use_container_width=True)

st.markdown("---")

# Score Breakdown Waterfall
st.markdown(f"<h2 style='color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;'>Health Score Waterfall</h2>", unsafe_allow_html=True)

score_breakdown = summary.get("score_breakdown", {})

if score_breakdown:
    base_score = 100
    components = [
        ("Starting Score", base_score, "total"),
        ("Frustration", -score_breakdown.get("frustration_component", 0), "relative"),
        ("High Frustration", -score_breakdown.get("high_frustration_penalty", 0), "relative"),
        ("Critical Load", -score_breakdown.get("critical_load_component", 0), "relative"),
        ("Systemic Issues", -score_breakdown.get("systemic_issues_component", 0), "relative"),
        ("Resolution Complexity", -score_breakdown.get("resolution_complexity_component", 0), "relative"),
        ("Temporal Clustering", -score_breakdown.get("temporal_clustering_penalty", 0), "relative"),
        ("Final Score", summary.get("account_health_score", 0), "total"),
    ]

    # Filter out zero values except totals
    components = [(n, v, t) for n, v, t in components if v != 0 or t == "total"]

    fig_waterfall = go.Figure(go.Waterfall(
        x=[c[0] for c in components],
        y=[c[1] for c in components],
        measure=[c[2] for c in components],
        connector={"line": {"color": COLORS['border']}},
        decreasing={"marker": {"color": COLORS['critical']}},
        increasing={"marker": {"color": COLORS['success']}},
        totals={"marker": {"color": COLORS['primary']}},
        textfont={'color': COLORS['text']}
    ))

    fig_waterfall.update_layout(
        yaxis_title="Score",
        height=400,
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['background'],
        font={'color': COLORS['text']},
        xaxis={'color': COLORS['text_muted']},
        yaxis={'color': COLORS['text_muted']}
    )

    st.plotly_chart(fig_waterfall, use_container_width=True)

st.markdown("---")

# Status distribution
st.markdown(f"<h3 style='color: {COLORS['secondary']};'>Case Status Overview</h3>", unsafe_allow_html=True)

status_counts = df_cases['status'].value_counts()

fig_status = go.Figure(data=[go.Bar(
    x=status_counts.index,
    y=status_counts.values,
    marker_color=COLORS['primary'],
    textfont={'color': COLORS['text']}
)])

fig_status.update_layout(
    xaxis_title="Status",
    yaxis_title="Number of Cases",
    height=300,
    paper_bgcolor=COLORS['background'],
    plot_bgcolor=COLORS['background'],
    font={'color': COLORS['text']},
    xaxis={'color': COLORS['text_muted']},
    yaxis={'color': COLORS['text_muted']}
)

st.plotly_chart(fig_status, use_container_width=True)

# Show original charts if available
st.markdown("---")
st.markdown(f"<h3 style='color: {COLORS['secondary']};'>Original Analysis Charts</h3>", unsafe_allow_html=True)

if charts:
    chart_cols = st.columns(2)
    for i, (name, path) in enumerate(charts.items()):
        with chart_cols[i % 2]:
            st.image(path, caption=name.replace("_", " ").title(), use_container_width=True)
else:
    st.info("Original PNG charts not available")
