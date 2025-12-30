"""
Use Case-Centric View - Full Analysis Dashboard
Aggregates all data by customer use case/workload type.
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
    page_title="Use Case View - Full Analysis",
    page_icon="🎯",
    layout="wide",
)

# Apply global styling
st.markdown(get_global_css(), unsafe_allow_html=True)

# Get data from session state
data = st.session_state.get("analysis_data", {})

if data.get("analysis_type") != "full":
    st.warning("This page requires a Full Analysis. Please select a full analysis from the home page.")
    st.stop()

usecase_metrics = data.get("usecase_metrics", {})

if not usecase_metrics:
    st.warning("No use case metrics data available.")
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
                Use Case-Centric View
            </h1>
            <p style="color: #8b949e; margin: 5px 0 0 0; font-size: 1.1rem;">
                Performance Analysis by Workload Type
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Get use cases - handle both dict format
use_cases_data = usecase_metrics.get("use_cases", {})

if isinstance(use_cases_data, dict):
    use_cases = list(use_cases_data.values())
    use_case_names = list(use_cases_data.keys())
else:
    use_cases = []
    use_case_names = []

if not use_cases:
    st.info("No use case data available. Use cases are extracted from opportunity analysis.")
    st.stop()

# Use Case Overview
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Use Case Distribution
</h2>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])

with col1:
    # Orders by use case pie chart
    orders_by_case = {uc.get("use_case", "Unknown"): uc.get("total_orders", 0) for uc in use_cases}

    if orders_by_case:
        fig_pie = go.Figure(data=[go.Pie(
            labels=list(orders_by_case.keys()),
            values=list(orders_by_case.values()),
            hole=0.4,
            textfont={'color': COLORS['white']}
        )])
        fig_pie.update_layout(
            title={'text': 'Orders by Use Case', 'font': {'color': COLORS['white']}},
            height=350,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            legend={'font': {'color': COLORS['text']}}
        )
        st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    # Revenue by use case bar chart
    revenue_data = [(uc.get("use_case", "Unknown"), uc.get("total_revenue", 0)) for uc in use_cases]
    revenue_data.sort(key=lambda x: x[1], reverse=True)

    if revenue_data:
        fig_bar = go.Figure(go.Bar(
            x=[r[1] for r in revenue_data],
            y=[r[0] for r in revenue_data],
            orientation='h',
            marker_color=COLORS['success'],
            text=[f"${r[1]:,.0f}" for r in revenue_data],
            textposition='outside',
            textfont={'color': COLORS['text']}
        ))
        fig_bar.update_layout(
            title={'text': 'Revenue by Use Case', 'font': {'color': COLORS['white']}},
            height=350,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            xaxis={'color': COLORS['text_muted']},
            yaxis={'color': COLORS['text']},
            margin=dict(l=0, r=80, t=40, b=40),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# Use Case Selector
selected_use_case = st.selectbox("Select Use Case for Details", use_case_names)

# Find selected use case data
selected_data = use_cases_data.get(selected_use_case, {})

if selected_data:
    st.markdown("---")

    # Key metrics for selected use case
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Orders", selected_data.get("total_orders", 0))

    with col2:
        st.metric("Revenue", f"${selected_data.get('total_revenue', 0):,.0f}")

    with col3:
        st.metric("Unique Accounts", selected_data.get("unique_accounts", 0))

    with col4:
        st.metric("Deployments", selected_data.get("total_deployments", 0))

    with col5:
        st.metric("Support Cases", selected_data.get("total_support_cases", 0))

    st.markdown("---")

    # Detailed metrics
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(f"""
        <h3 style="color: {COLORS['secondary']};">Deployment Performance</h3>
        """, unsafe_allow_html=True)

        deploy_metrics = {
            "Metric": [
                "Total Deployments",
                "Avg Deployment Score",
                "Success Rate (>70)",
                "Service Deploy Rate",
                "Support Intensity"
            ],
            "Value": [
                selected_data.get("total_deployments", 0),
                f"{selected_data.get('avg_deployment_score', 0):.1f}",
                f"{selected_data.get('deployment_success_rate', 0):.1f}%",
                f"{selected_data.get('service_deploy_rate', 0):.1f}%",
                f"{selected_data.get('support_intensity', 0):.2f} cases/deploy"
            ]
        }
        st.dataframe(pd.DataFrame(deploy_metrics), use_container_width=True, hide_index=True)

        # Best/worst products
        best_product = selected_data.get("best_performing_product", "N/A")
        worst_product = selected_data.get("worst_performing_product", "N/A")

        st.markdown(f"""
        <div style="background: {COLORS['surface']}; padding: 1rem; border-radius: 8px; margin-top: 1rem;">
            <p style="color: {COLORS['success']}; margin: 0;"><b>Best Performing:</b> {best_product}</p>
            <p style="color: {COLORS['warning']}; margin: 0.5rem 0 0 0;"><b>Needs Attention:</b> {worst_product}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <h3 style="color: {COLORS['secondary']};">Support Experience</h3>
        """, unsafe_allow_html=True)

        support_metrics = {
            "Metric": [
                "Total Cases",
                "S1 Cases",
                "Avg Frustration",
                "Escalation Rate",
                "High Churn Risk"
            ],
            "Value": [
                selected_data.get("total_support_cases", 0),
                selected_data.get("s1_case_count", 0),
                f"{selected_data.get('avg_frustration_score', 0):.1f}/10",
                f"{selected_data.get('escalation_rate', 0):.1f}%",
                selected_data.get("high_churn_risk_count", 0)
            ]
        }
        st.dataframe(pd.DataFrame(support_metrics), use_container_width=True, hide_index=True)

        # Recommended products
        recommended = selected_data.get("recommended_products", [])
        if recommended:
            st.markdown(f"""
            <div style="background: {COLORS['surface']}; padding: 1rem; border-radius: 8px; margin-top: 1rem;">
                <p style="color: {COLORS['primary']}; margin: 0;"><b>Recommended Products:</b></p>
                <p style="color: {COLORS['text']}; margin: 0.5rem 0 0 0;">{', '.join(recommended)}</p>
            </div>
            """, unsafe_allow_html=True)

    # Top issues for this use case
    top_issues = selected_data.get("top_issues", [])
    issue_dist = selected_data.get("issue_distribution", {})

    if issue_dist:
        st.markdown("---")
        st.markdown(f"""
        <h3 style="color: {COLORS['secondary']};">Common Issues for {selected_use_case}</h3>
        """, unsafe_allow_html=True)

        sorted_issues = sorted(issue_dist.items(), key=lambda x: x[1], reverse=True)[:8]

        fig_issues = go.Figure(go.Bar(
            x=[i[1] for i in sorted_issues],
            y=[i[0][:35] for i in sorted_issues],
            orientation='h',
            marker_color=COLORS['warning'],
            text=[i[1] for i in sorted_issues],
            textposition='outside',
            textfont={'color': COLORS['text']}
        ))
        fig_issues.update_layout(
            height=max(200, len(sorted_issues) * 35),
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            xaxis={'color': COLORS['text_muted']},
            yaxis={'color': COLORS['text']},
            margin=dict(l=0, r=60, t=10, b=40),
        )
        st.plotly_chart(fig_issues, use_container_width=True)

    # Common pain points
    pain_points = selected_data.get("common_pain_points", [])
    if pain_points:
        st.markdown(f"""
        <h3 style="color: {COLORS['secondary']};">Common Pain Points</h3>
        """, unsafe_allow_html=True)
        for point in pain_points:
            st.markdown(f"- {point}")

st.markdown("---")

# All Use Cases Comparison
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Use Case Comparison Matrix
</h2>
""", unsafe_allow_html=True)

# Build comparison table
comparison_data = []
for uc_name, uc in use_cases_data.items():
    comparison_data.append({
        "Use Case": uc_name,
        "Orders": uc.get("total_orders", 0),
        "Revenue": f"${uc.get('total_revenue', 0):,.0f}",
        "Accounts": uc.get("unique_accounts", 0),
        "Deploy Score": f"{uc.get('avg_deployment_score', 0):.1f}",
        "Success %": f"{uc.get('deployment_success_rate', 0):.1f}%",
        "Support Cases": uc.get("total_support_cases", 0),
        "Support Intensity": f"{uc.get('support_intensity', 0):.2f}",
        "Frustration": f"{uc.get('avg_frustration_score', 0):.1f}",
        "Best Product": uc.get("best_performing_product", "N/A"),
    })

if comparison_data:
    df = pd.DataFrame(comparison_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

# Visual comparisons
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    # Success rate by use case
    success_data = [(uc.get("use_case", "Unknown"), uc.get("deployment_success_rate", 0)) for uc in use_cases]
    success_data.sort(key=lambda x: x[1], reverse=True)

    if success_data:
        fig_success = go.Figure(go.Bar(
            x=[s[0][:20] for s in success_data],
            y=[s[1] for s in success_data],
            marker_color=COLORS['success'],
            text=[f"{s[1]:.0f}%" for s in success_data],
            textposition='outside',
            textfont={'color': COLORS['text']}
        ))
        fig_success.update_layout(
            title={'text': 'Deployment Success by Use Case', 'font': {'color': COLORS['white']}},
            height=300,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            xaxis={'color': COLORS['text_muted']},
            yaxis={'title': 'Success Rate %', 'color': COLORS['text_muted']},
        )
        st.plotly_chart(fig_success, use_container_width=True)

with col2:
    # Support intensity by use case
    intensity_data = [(uc.get("use_case", "Unknown"), uc.get("support_intensity", 0)) for uc in use_cases]
    intensity_data.sort(key=lambda x: x[1], reverse=True)

    if intensity_data:
        fig_intensity = go.Figure(go.Bar(
            x=[i[0][:20] for i in intensity_data],
            y=[i[1] for i in intensity_data],
            marker_color=COLORS['warning'],
            text=[f"{i[1]:.2f}" for i in intensity_data],
            textposition='outside',
            textfont={'color': COLORS['text']}
        ))
        fig_intensity.update_layout(
            title={'text': 'Support Intensity by Use Case (Lower = Better)', 'font': {'color': COLORS['white']}},
            height=300,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            xaxis={'color': COLORS['text_muted']},
            yaxis={'title': 'Cases per Deploy', 'color': COLORS['text_muted']},
        )
        st.plotly_chart(fig_intensity, use_container_width=True)
