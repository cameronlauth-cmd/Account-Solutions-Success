"""
Product-Centric View - Full Analysis Dashboard
Aggregates all data by product line/series.
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
    page_title="Product View - Full Analysis",
    page_icon="📦",
    layout="wide",
)

# Apply global styling
st.markdown(get_global_css(), unsafe_allow_html=True)

# Get data from session state
data = st.session_state.get("analysis_data", {})

if data.get("analysis_type") != "full":
    st.warning("This page requires a Full Analysis. Please select a full analysis from the home page.")
    st.stop()

product_metrics = data.get("product_metrics", {})

if not product_metrics:
    st.warning("No product metrics data available.")
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
                Product-Centric View
            </h1>
            <p style="color: #8b949e; margin: 5px 0 0 0; font-size: 1.1rem;">
                Performance Metrics by Product Line
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Get products list
products = product_metrics.get("products", [])

if not products:
    st.info("No product data available for analysis.")
    st.stop()

# Product selector
product_names = [p.get("product_series", "Unknown") for p in products]
selected_product = st.selectbox("Select Product", product_names)

# Find selected product data
selected_data = next((p for p in products if p.get("product_series") == selected_product), None)

if selected_data:
    st.markdown("---")

    # Key metrics for selected product
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Deployments", selected_data.get("total_deployments", 0))

    with col2:
        st.metric("Revenue", f"${selected_data.get('total_revenue', 0):,.0f}")

    with col3:
        st.metric("Deployment Success", f"{selected_data.get('deployment_success_rate', 0):.1f}%")

    with col4:
        st.metric("Support Cases", selected_data.get("total_support_cases", 0))

    with col5:
        st.metric("Avg Frustration", f"{selected_data.get('avg_frustration_score', 0):.1f}/10")

    st.markdown("---")

    # Product details
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(f"""
        <h3 style="color: {COLORS['secondary']};">Deployment Metrics</h3>
        """, unsafe_allow_html=True)

        deploy_data = {
            "Metric": [
                "Total Deployments",
                "Avg Deployment Score",
                "Success Rate (>70)",
                "Service Deploys",
                "Self Deploys",
                "Avg Deployment Days"
            ],
            "Value": [
                selected_data.get("total_deployments", 0),
                f"{selected_data.get('avg_deployment_score', 0):.1f}",
                f"{selected_data.get('deployment_success_rate', 0):.1f}%",
                selected_data.get("service_deploys", 0),
                selected_data.get("self_deploys", 0),
                f"{selected_data.get('avg_deployment_days', 0):.1f}"
            ]
        }
        st.dataframe(pd.DataFrame(deploy_data), use_container_width=True, hide_index=True)

    with col2:
        st.markdown(f"""
        <h3 style="color: {COLORS['secondary']};">Support Metrics</h3>
        """, unsafe_allow_html=True)

        support_data = {
            "Metric": [
                "Total Cases",
                "S1 Cases",
                "S2 Cases",
                "Cases per Deploy",
                "Avg Frustration",
                "Escalations"
            ],
            "Value": [
                selected_data.get("total_support_cases", 0),
                selected_data.get("s1_cases", 0),
                selected_data.get("s2_cases", 0),
                f"{selected_data.get('support_cases_per_deployment', 0):.2f}",
                f"{selected_data.get('avg_frustration_score', 0):.1f}",
                selected_data.get("escalation_count", 0)
            ]
        }
        st.dataframe(pd.DataFrame(support_data), use_container_width=True, hide_index=True)

    # Issue distribution
    issue_dist = selected_data.get("issue_distribution", {})
    if issue_dist:
        st.markdown("---")
        st.markdown(f"""
        <h3 style="color: {COLORS['secondary']};">Common Issues for {selected_product}</h3>
        """, unsafe_allow_html=True)

        sorted_issues = sorted(issue_dist.items(), key=lambda x: x[1], reverse=True)[:10]

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
            height=max(250, len(sorted_issues) * 35),
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            xaxis={'color': COLORS['text_muted']},
            yaxis={'color': COLORS['text']},
            margin=dict(l=0, r=60, t=10, b=40),
        )
        st.plotly_chart(fig_issues, use_container_width=True)

st.markdown("---")

# Product Comparison Table
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    All Products Comparison
</h2>
""", unsafe_allow_html=True)

# Build comparison table
comparison_data = []
for product in products:
    comparison_data.append({
        "Product": product.get("product_series", "Unknown"),
        "Deployments": product.get("total_deployments", 0),
        "Revenue": f"${product.get('total_revenue', 0):,.0f}",
        "Deploy Score": f"{product.get('avg_deployment_score', 0):.1f}",
        "Success %": f"{product.get('deployment_success_rate', 0):.1f}%",
        "Support Cases": product.get("total_support_cases", 0),
        "Cases/Deploy": f"{product.get('support_cases_per_deployment', 0):.2f}",
        "Frustration": f"{product.get('avg_frustration_score', 0):.1f}",
        "S1 Cases": product.get("s1_cases", 0),
    })

if comparison_data:
    df_compare = pd.DataFrame(comparison_data)
    st.dataframe(df_compare, use_container_width=True, hide_index=True)

# Visual comparison
st.markdown("---")
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Product Performance Visualization
</h2>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    # Deployment success by product
    fig_success = go.Figure(go.Bar(
        x=[p.get("product_series", "")[:15] for p in products],
        y=[p.get("deployment_success_rate", 0) for p in products],
        marker_color=COLORS['success'],
        text=[f"{p.get('deployment_success_rate', 0):.0f}%" for p in products],
        textposition='outside',
        textfont={'color': COLORS['text']}
    ))
    fig_success.update_layout(
        title={'text': 'Deployment Success Rate by Product', 'font': {'color': COLORS['white']}},
        height=300,
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['background'],
        font={'color': COLORS['text']},
        xaxis={'color': COLORS['text_muted']},
        yaxis={'title': 'Success Rate %', 'color': COLORS['text_muted']},
    )
    st.plotly_chart(fig_success, use_container_width=True)

with col2:
    # Support intensity by product
    fig_intensity = go.Figure(go.Bar(
        x=[p.get("product_series", "")[:15] for p in products],
        y=[p.get("support_cases_per_deployment", 0) for p in products],
        marker_color=COLORS['warning'],
        text=[f"{p.get('support_cases_per_deployment', 0):.1f}" for p in products],
        textposition='outside',
        textfont={'color': COLORS['text']}
    ))
    fig_intensity.update_layout(
        title={'text': 'Support Intensity by Product (Lower = Better)', 'font': {'color': COLORS['white']}},
        height=300,
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['background'],
        font={'color': COLORS['text']},
        xaxis={'color': COLORS['text_muted']},
        yaxis={'title': 'Cases per Deployment', 'color': COLORS['text_muted']},
    )
    st.plotly_chart(fig_intensity, use_container_width=True)
