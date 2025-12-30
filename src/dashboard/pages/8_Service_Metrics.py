"""
Service Metrics Page - Full Analysis Dashboard
Compares Professional Services deployments vs Self-deployments.
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
    page_title="Service Metrics - Full Analysis",
    page_icon="📊",
    layout="wide",
)

# Apply global styling
st.markdown(get_global_css(), unsafe_allow_html=True)

# Get data from session state
data = st.session_state.get("analysis_data", {})

if data.get("analysis_type") != "full":
    st.warning("This page requires a Full Analysis. Please select a full analysis from the home page.")
    st.stop()

service_data = data.get("service_metrics", {})

if not service_data:
    st.warning("No service metrics data available.")
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
                Service Team Effectiveness
            </h1>
            <p style="color: #8b949e; margin: 5px 0 0 0; font-size: 1.1rem;">
                Professional Services vs Self-Deploy Comparison
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Get comparison data
service_metrics = service_data.get("service_deploy", {})
self_metrics = service_data.get("self_deploy", {})
comparison = service_data.get("comparison", {})

# Service Value-Add Score
value_add_score = comparison.get("service_value_add_score", 50)
recommendation = comparison.get("recommendation", "No recommendation available.")

# Determine score color
if value_add_score >= 70:
    score_color = COLORS['success']
elif value_add_score >= 50:
    score_color = COLORS['primary']
elif value_add_score >= 30:
    score_color = COLORS['warning']
else:
    score_color = COLORS['critical']

# Value-Add Score Card
st.markdown(f"""
<div style="background: linear-gradient(135deg, {COLORS['surface']} 0%, #1a1f29 100%);
            padding: 2rem; border-radius: 12px; margin-bottom: 1.5rem;
            border: 2px solid {score_color}; text-align: center;">
    <div style="font-size: 3rem; font-weight: 700; color: {score_color};">
        {value_add_score:.0f}
    </div>
    <div style="font-size: 1.2rem; color: {COLORS['text_muted']}; margin-top: 0.5rem;">
        Service Value-Add Score
    </div>
    <div style="font-size: 0.9rem; color: {COLORS['text']}; margin-top: 1rem; max-width: 600px; margin-left: auto; margin-right: auto;">
        {recommendation}
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Comparison Metrics
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Head-to-Head Comparison
</h2>
""", unsafe_allow_html=True)

# Key metrics comparison
col1, col2, col3, col4 = st.columns(4)

with col1:
    delta = comparison.get("success_rate_delta", 0)
    delta_str = f"+{delta:.1f}%" if delta > 0 else f"{delta:.1f}%"
    st.metric(
        "Success Rate Delta",
        delta_str,
        help="Service Deploy success rate - Self Deploy success rate (positive = service better)"
    )

with col2:
    delta = comparison.get("support_intensity_delta", 0)
    delta_str = f"+{delta:.2f}" if delta > 0 else f"{delta:.2f}"
    st.metric(
        "Support Intensity Delta",
        delta_str,
        help="Cases per deployment difference (positive = service has fewer support cases)"
    )

with col3:
    delta = comparison.get("frustration_delta", 0)
    delta_str = f"+{delta:.1f}" if delta > 0 else f"{delta:.1f}"
    st.metric(
        "Frustration Delta",
        delta_str,
        help="Frustration score difference (positive = service has lower frustration)"
    )

with col4:
    delta = comparison.get("journey_health_delta", 0)
    delta_str = f"+{delta:.1f}" if delta > 0 else f"{delta:.1f}"
    st.metric(
        "Journey Health Delta",
        delta_str,
        help="Journey health score difference (positive = service is healthier)"
    )

st.markdown("---")

# Side-by-side comparison table
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Detailed Metrics Comparison
</h2>
""", unsafe_allow_html=True)

# Build comparison table
metrics_rows = [
    ("Total Deployments", service_metrics.get("total_deployments", 0), self_metrics.get("total_deployments", 0)),
    ("Unique Accounts", service_metrics.get("unique_accounts", 0), self_metrics.get("unique_accounts", 0)),
    ("Total Revenue", f"${service_metrics.get('total_revenue', 0):,.0f}", f"${self_metrics.get('total_revenue', 0):,.0f}"),
    ("Avg Deployment Score", f"{service_metrics.get('avg_deployment_score', 0):.1f}", f"{self_metrics.get('avg_deployment_score', 0):.1f}"),
    ("Success Rate (%)", f"{service_metrics.get('deployment_success_rate', 0):.1f}%", f"{self_metrics.get('deployment_success_rate', 0):.1f}%"),
    ("Avg Deployment Days", f"{service_metrics.get('avg_deployment_days', 0):.1f}", f"{self_metrics.get('avg_deployment_days', 0):.1f}"),
    ("Support Cases", service_metrics.get("total_support_cases", 0), self_metrics.get("total_support_cases", 0)),
    ("Cases per Deploy", f"{service_metrics.get('support_cases_per_deployment', 0):.2f}", f"{self_metrics.get('support_cases_per_deployment', 0):.2f}"),
    ("Avg Frustration", f"{service_metrics.get('avg_frustration_score', 0):.1f}", f"{self_metrics.get('avg_frustration_score', 0):.1f}"),
    ("S1 Cases", service_metrics.get("s1_cases", 0), self_metrics.get("s1_cases", 0)),
    ("Escalations", service_metrics.get("escalation_count", 0), self_metrics.get("escalation_count", 0)),
    ("Avg Journey Health", f"{service_metrics.get('avg_journey_health', 0):.0f}", f"{self_metrics.get('avg_journey_health', 0):.0f}"),
    ("High Churn Risk", service_metrics.get("high_churn_risk_count", 0), self_metrics.get("high_churn_risk_count", 0)),
]

df = pd.DataFrame(metrics_rows, columns=["Metric", "Service Deploy", "Self Deploy"])
st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")

# Visual Comparison Charts
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Visual Comparison
</h2>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    # Deployment Score Comparison
    fig_score = go.Figure()
    fig_score.add_trace(go.Bar(
        name='Service Deploy',
        x=['Deployment Score', 'Success Rate'],
        y=[service_metrics.get('avg_deployment_score', 0), service_metrics.get('deployment_success_rate', 0)],
        marker_color=COLORS['primary']
    ))
    fig_score.add_trace(go.Bar(
        name='Self Deploy',
        x=['Deployment Score', 'Success Rate'],
        y=[self_metrics.get('avg_deployment_score', 0), self_metrics.get('deployment_success_rate', 0)],
        marker_color=COLORS['secondary']
    ))

    fig_score.update_layout(
        title={'text': 'Deployment Quality', 'font': {'color': COLORS['white']}},
        barmode='group',
        height=300,
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['background'],
        font={'color': COLORS['text']},
        legend={'font': {'color': COLORS['text']}},
        yaxis={'title': 'Score / Percentage', 'color': COLORS['text_muted']},
    )
    st.plotly_chart(fig_score, use_container_width=True)

with col2:
    # Support Intensity Comparison
    fig_support = go.Figure()
    fig_support.add_trace(go.Bar(
        name='Service Deploy',
        x=['Cases per Deploy', 'Avg Frustration', 'S1 Cases'],
        y=[service_metrics.get('support_cases_per_deployment', 0),
           service_metrics.get('avg_frustration_score', 0),
           service_metrics.get('s1_cases', 0)],
        marker_color=COLORS['primary']
    ))
    fig_support.add_trace(go.Bar(
        name='Self Deploy',
        x=['Cases per Deploy', 'Avg Frustration', 'S1 Cases'],
        y=[self_metrics.get('support_cases_per_deployment', 0),
           self_metrics.get('avg_frustration_score', 0),
           self_metrics.get('s1_cases', 0)],
        marker_color=COLORS['secondary']
    ))

    fig_support.update_layout(
        title={'text': 'Support Impact (Lower = Better)', 'font': {'color': COLORS['white']}},
        barmode='group',
        height=300,
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['background'],
        font={'color': COLORS['text']},
        legend={'font': {'color': COLORS['text']}},
        yaxis={'title': 'Value', 'color': COLORS['text_muted']},
    )
    st.plotly_chart(fig_support, use_container_width=True)

st.markdown("---")

# Product Distribution by Deploy Type
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Product Distribution by Deployment Type
</h2>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

service_products = service_metrics.get("products_deployed", {})
self_products = self_metrics.get("products_deployed", {})

with col1:
    if service_products:
        fig_service_prod = go.Figure(data=[go.Pie(
            labels=list(service_products.keys()),
            values=list(service_products.values()),
            hole=0.4,
            textfont={'color': COLORS['white']}
        )])
        fig_service_prod.update_layout(
            title={'text': 'Service Deploy Products', 'font': {'color': COLORS['white']}},
            height=300,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            legend={'font': {'color': COLORS['text']}}
        )
        st.plotly_chart(fig_service_prod, use_container_width=True)
    else:
        st.info("No service deploy product data available.")

with col2:
    if self_products:
        fig_self_prod = go.Figure(data=[go.Pie(
            labels=list(self_products.keys()),
            values=list(self_products.values()),
            hole=0.4,
            textfont={'color': COLORS['white']}
        )])
        fig_self_prod.update_layout(
            title={'text': 'Self Deploy Products', 'font': {'color': COLORS['white']}},
            height=300,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            legend={'font': {'color': COLORS['text']}}
        )
        st.plotly_chart(fig_self_prod, use_container_width=True)
    else:
        st.info("No self deploy product data available.")

# Key Insights
st.markdown("---")
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Key Insights
</h2>
""", unsafe_allow_html=True)

insights = []

# Generate insights based on data
success_delta = comparison.get("success_rate_delta", 0)
if success_delta > 10:
    insights.append(f"Service deploys have a significantly higher success rate (+{success_delta:.1f}%)")
elif success_delta < -10:
    insights.append(f"Self deploys are performing better on success rate ({success_delta:.1f}%)")

intensity_delta = comparison.get("support_intensity_delta", 0)
if intensity_delta > 0.5:
    insights.append(f"Service deploys generate fewer support cases per deployment")
elif intensity_delta < -0.5:
    insights.append(f"Self deploys generate fewer support cases per deployment")

frustration_delta = comparison.get("frustration_delta", 0)
if frustration_delta > 1:
    insights.append(f"Service deploy customers report lower frustration levels")
elif frustration_delta < -1:
    insights.append(f"Self deploy customers report lower frustration levels")

if insights:
    for insight in insights:
        st.markdown(f"""
        <div style="background: {COLORS['surface']}; padding: 1rem; border-radius: 8px;
                    border-left: 3px solid {COLORS['primary']}; margin-bottom: 0.5rem;">
            <span style="color: {COLORS['text']};">{insight}</span>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Service and Self deploy show comparable performance across metrics.")
