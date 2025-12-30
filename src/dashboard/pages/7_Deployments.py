"""
Deployments Page - Full Analysis Dashboard
Shows deployment analysis from the 4-layer pipeline.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.branding import COLORS, get_logo_html
from src.dashboard.styles import get_global_css

# Page config
st.set_page_config(
    page_title="Deployments - Full Analysis",
    page_icon="🚀",
    layout="wide",
)

# Apply global styling
st.markdown(get_global_css(), unsafe_allow_html=True)

# Get data from session state
data = st.session_state.get("analysis_data", {})

if data.get("analysis_type") != "full":
    st.warning("This page requires a Full Analysis. Please select a full analysis from the home page.")
    st.stop()

deployments_data = data.get("deployments", {})
link_summary = data.get("link_summary", {})

if not deployments_data:
    st.warning("No deployment data available.")
    st.stop()

# Header
logo_html = get_logo_html(height=40)
st.markdown(f"""
<div style="background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
            padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;
            border: 1px solid #30363d; border-left: 4px solid #0095D5;">
    <div style="display: flex; align-items: center; gap: 1.5rem;">
        <div>{logo_html}</div>
        <div style="border-left: 2px solid #30363d; padding-left: 1.5rem;">
            <h1 style="color: {COLORS['primary']}; margin: 0; font-size: 1.8rem; font-weight: 600;">
                Deployments Analysis
            </h1>
            <p style="color: #8b949e; margin: 5px 0 0 0; font-size: 1.1rem;">
                Layer 2: Installation Quality & Service Effectiveness
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Summary metrics
total_deps = deployments_data.get("total", 0)
analyzed_deps = deployments_data.get("analyzed", 0)
deps_list = deployments_data.get("deployments", [])

# Calculate metrics
service_deploys = 0
successful_deploys = 0
total_score = 0
scored_count = 0

for dep in deps_list:
    analysis = dep.get("analysis", {})
    if analysis:
        if analysis.get("is_service_deploy"):
            service_deploys += 1
        score = analysis.get("deployment_score", 0)
        if score > 0:
            total_score += score
            scored_count += 1
            if score > 70:
                successful_deploys += 1

avg_score = total_score / scored_count if scored_count > 0 else 0

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Deployments", total_deps)

with col2:
    st.metric("Avg Deployment Score", f"{avg_score:.0f}/100")

with col3:
    success_rate = (successful_deploys / scored_count * 100) if scored_count > 0 else 0
    st.metric("Success Rate (>70)", f"{success_rate:.0f}%")

with col4:
    service_rate = (service_deploys / total_deps * 100) if total_deps > 0 else 0
    st.metric("Service Deploy Rate", f"{service_rate:.0f}%")

st.markdown("---")

# Deployment Type Comparison
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Service vs Self-Deploy Comparison
</h2>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])

with col1:
    # Service vs Self deploy pie
    service_count = service_deploys
    self_count = total_deps - service_deploys

    if service_count > 0 or self_count > 0:
        fig_type = go.Figure(data=[go.Pie(
            labels=['Service Deploy', 'Self Deploy'],
            values=[service_count, self_count],
            hole=0.4,
            marker_colors=[COLORS['primary'], COLORS['secondary']],
            textfont={'color': COLORS['white']}
        )])
        fig_type.update_layout(
            title={'text': 'Deployment Type Distribution', 'font': {'color': COLORS['white']}},
            height=300,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            legend={'font': {'color': COLORS['text']}}
        )
        st.plotly_chart(fig_type, use_container_width=True)

with col2:
    # Score distribution by type
    service_scores = []
    self_scores = []

    for dep in deps_list:
        analysis = dep.get("analysis", {})
        if analysis:
            score = analysis.get("deployment_score", 0)
            if score > 0:
                if analysis.get("is_service_deploy"):
                    service_scores.append(score)
                else:
                    self_scores.append(score)

    if service_scores or self_scores:
        fig_scores = go.Figure()
        if service_scores:
            fig_scores.add_trace(go.Box(
                y=service_scores,
                name="Service Deploy",
                marker_color=COLORS['primary']
            ))
        if self_scores:
            fig_scores.add_trace(go.Box(
                y=self_scores,
                name="Self Deploy",
                marker_color=COLORS['secondary']
            ))

        fig_scores.update_layout(
            title={'text': 'Deployment Score Distribution', 'font': {'color': COLORS['white']}},
            height=300,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            yaxis={'title': 'Deployment Score', 'color': COLORS['text_muted']},
        )
        st.plotly_chart(fig_scores, use_container_width=True)

st.markdown("---")

# Deployments Table
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Deployment Details
</h2>
""", unsafe_allow_html=True)

# Build table data
table_data = []
for dep in deps_list:
    analysis = dep.get("analysis", {})
    table_data.append({
        "Case #": dep.get("case_number", "N/A"),
        "Order #": dep.get("order_number", "N/A"),
        "Account": dep.get("account_name", "N/A"),
        "Product": dep.get("product_model", "N/A"),
        "Status": dep.get("status", "N/A"),
        "Type": "Service" if (analysis and analysis.get("is_service_deploy")) else "Self",
        "Score": f"{analysis.get('deployment_score', 0)}/100" if analysis else "N/A",
        "Quality": analysis.get("quality_assessment", "N/A")[:30] + "..." if analysis and len(analysis.get("quality_assessment", "")) > 30 else (analysis.get("quality_assessment", "N/A") if analysis else "N/A"),
    })

if table_data:
    df = pd.DataFrame(table_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")

# Deployment Issues
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Deployment Issues & Insights
</h2>
""", unsafe_allow_html=True)

# Collect issues
all_issues = []
for dep in deps_list:
    analysis = dep.get("analysis", {})
    if analysis:
        issues = analysis.get("issues_identified", [])
        all_issues.extend(issues)

if all_issues:
    # Count issue frequency
    issue_counts = {}
    for issue in all_issues:
        issue_counts[issue] = issue_counts.get(issue, 0) + 1

    sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    fig_issues = go.Figure(go.Bar(
        x=[i[1] for i in sorted_issues],
        y=[i[0][:40] for i in sorted_issues],
        orientation='h',
        marker_color=COLORS['warning'],
        text=[i[1] for i in sorted_issues],
        textposition='outside',
        textfont={'color': COLORS['text']}
    ))
    fig_issues.update_layout(
        title={'text': 'Common Deployment Issues', 'font': {'color': COLORS['white']}},
        height=max(300, len(sorted_issues) * 40),
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['background'],
        font={'color': COLORS['text']},
        xaxis={'color': COLORS['text_muted']},
        yaxis={'color': COLORS['text']},
        margin=dict(l=0, r=60, t=40, b=40),
    )
    st.plotly_chart(fig_issues, use_container_width=True)
else:
    st.info("No deployment issues identified.")

# Detailed Deployment Cards
st.markdown("---")
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Deployment Insights
</h2>
""", unsafe_allow_html=True)

# Show expandable details for deployments with low scores
low_score_deps = [d for d in deps_list if d.get("analysis", {}).get("deployment_score", 100) < 70]

if low_score_deps:
    st.markdown(f"**{len(low_score_deps)} deployments with scores below 70:**")

    for dep in low_score_deps[:5]:  # Limit to first 5
        analysis = dep.get("analysis", {})
        score = analysis.get("deployment_score", 0)
        score_color = COLORS['critical'] if score < 50 else COLORS['warning']

        with st.expander(f"{dep.get('account_name', 'Unknown')} - Score: {score}/100"):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Quality Assessment:** {analysis.get('quality_assessment', 'N/A')}")

                issues = analysis.get('issues_identified', [])
                if issues:
                    st.markdown("**Issues Identified:**")
                    for issue in issues:
                        st.markdown(f"- {issue}")

                recommendations = analysis.get('recommendations', [])
                if recommendations:
                    st.markdown("**Recommendations:**")
                    for rec in recommendations:
                        st.markdown(f"- {rec}")

            with col2:
                st.metric("Deployment Score", f"{score}/100")
                st.metric("Type", "Service" if analysis.get("is_service_deploy") else "Self Deploy")
                st.metric("Case #", dep.get("case_number", "N/A"))
else:
    st.success("All deployments scored 70 or above!")
