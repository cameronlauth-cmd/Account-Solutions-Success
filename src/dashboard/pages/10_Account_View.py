"""
Account-Centric View - Full Analysis Dashboard
Aggregates all data by customer account.
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

from src.dashboard.branding import COLORS, get_logo_html, get_health_color
from src.dashboard.styles import get_global_css

# Page config
st.set_page_config(
    page_title="Account View - Full Analysis",
    page_icon="🏢",
    layout="wide",
)

# Apply global styling
st.markdown(get_global_css(), unsafe_allow_html=True)

# Get data from session state
data = st.session_state.get("analysis_data", {})

if data.get("analysis_type") != "full":
    st.warning("This page requires a Full Analysis. Please select a full analysis from the home page.")
    st.stop()

account_metrics = data.get("account_metrics", {})

if not account_metrics:
    st.warning("No account metrics data available.")
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
                Account-Centric View
            </h1>
            <p style="color: #8b949e; margin: 5px 0 0 0; font-size: 1.1rem;">
                Customer Health & Journey Analysis
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Get accounts - handle both dict and list formats
accounts_data = account_metrics.get("accounts", {})

if isinstance(accounts_data, dict):
    accounts = list(accounts_data.values())
    account_names = list(accounts_data.keys())
elif isinstance(accounts_data, list):
    accounts = accounts_data
    account_names = [a.get("account_name", f"Account {i}") for i, a in enumerate(accounts)]
else:
    accounts = []
    account_names = []

if not accounts:
    st.info("No account data available for analysis.")
    st.stop()

# Account selector
selected_account_name = st.selectbox("Select Account", account_names)

# Find selected account data
if isinstance(accounts_data, dict):
    selected_data = accounts_data.get(selected_account_name, {})
else:
    selected_data = next((a for a in accounts if a.get("account_name") == selected_account_name), {})

if selected_data:
    st.markdown("---")

    # Account Health Score
    health_score = selected_data.get("account_health_score", 0)
    churn_risk = selected_data.get("churn_risk", "Unknown")
    health_color = get_health_color(health_score)

    # Risk color
    risk_colors = {
        "Low": COLORS['success'],
        "Medium": COLORS['warning'],
        "High": "#fd7e14",
        "Critical": COLORS['critical'],
    }
    risk_color = risk_colors.get(churn_risk, COLORS['text_muted'])

    # Health overview card
    st.markdown(f"""
    <div style="background: {COLORS['surface']}; padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;
                border-left: 4px solid {health_color};">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h2 style="color: {COLORS['white']}; margin: 0;">{selected_account_name}</h2>
                <p style="color: {COLORS['text_muted']}; margin: 0.5rem 0 0 0;">
                    {selected_data.get('total_orders', 0)} orders |
                    ${selected_data.get('total_spend', 0):,.0f} total spend
                </p>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 2.5rem; font-weight: 700; color: {health_color};">
                    {health_score:.0f}
                </div>
                <div style="color: {risk_color}; font-weight: 600;">
                    {churn_risk} Risk
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Key metrics
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Orders", selected_data.get("total_orders", 0))

    with col2:
        st.metric("Deployments", selected_data.get("total_deployments", 0))

    with col3:
        st.metric("Support Cases", selected_data.get("total_support_cases", 0))

    with col4:
        st.metric("S1 Cases", selected_data.get("s1_cases", 0))

    with col5:
        st.metric("Escalations", selected_data.get("escalation_count", 0))

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
                "Successful (>70)",
                "Success Rate",
                "Avg Deployment Score",
                "Service Deploys",
                "Self Deploys"
            ],
            "Value": [
                selected_data.get("total_deployments", 0),
                selected_data.get("successful_deployments", 0),
                f"{selected_data.get('deployment_success_rate', 0):.1f}%",
                f"{selected_data.get('avg_deployment_score', 0):.1f}",
                selected_data.get("service_deploys", 0),
                selected_data.get("self_deploys", 0)
            ]
        }
        st.dataframe(pd.DataFrame(deploy_metrics), use_container_width=True, hide_index=True)

    with col2:
        st.markdown(f"""
        <h3 style="color: {COLORS['secondary']};">Support Experience</h3>
        """, unsafe_allow_html=True)

        support_metrics = {
            "Metric": [
                "Total Cases",
                "Open Cases",
                "S1 Cases",
                "S2 Cases",
                "Avg Frustration",
                "Repeat Issues"
            ],
            "Value": [
                selected_data.get("total_support_cases", 0),
                selected_data.get("open_cases", 0),
                selected_data.get("s1_cases", 0),
                selected_data.get("s2_cases", 0),
                f"{selected_data.get('avg_frustration_score', 0):.1f}/10",
                selected_data.get("repeat_issues", 0)
            ]
        }
        st.dataframe(pd.DataFrame(support_metrics), use_container_width=True, hide_index=True)

    # Issue categories
    issue_cats = selected_data.get("issue_categories", {})
    if issue_cats:
        st.markdown("---")
        st.markdown(f"""
        <h3 style="color: {COLORS['secondary']};">Issue Categories</h3>
        """, unsafe_allow_html=True)

        sorted_cats = sorted(issue_cats.items(), key=lambda x: x[1], reverse=True)

        fig_cats = go.Figure(go.Bar(
            x=[c[1] for c in sorted_cats],
            y=[c[0] for c in sorted_cats],
            orientation='h',
            marker_color=COLORS['warning'],
            text=[c[1] for c in sorted_cats],
            textposition='outside',
            textfont={'color': COLORS['text']}
        ))
        fig_cats.update_layout(
            height=max(200, len(sorted_cats) * 35),
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            xaxis={'color': COLORS['text_muted']},
            yaxis={'color': COLORS['text']},
            margin=dict(l=0, r=60, t=10, b=40),
        )
        st.plotly_chart(fig_cats, use_container_width=True)

    # Critical findings and actions
    critical_findings = selected_data.get("critical_findings", [])
    positive_signals = selected_data.get("positive_signals", [])
    recommended_actions = selected_data.get("recommended_actions", [])

    if critical_findings or positive_signals or recommended_actions:
        st.markdown("---")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
            <h3 style="color: {COLORS['critical']};">Critical Findings</h3>
            """, unsafe_allow_html=True)
            if critical_findings:
                for finding in critical_findings:
                    st.markdown(f"- {finding}")
            else:
                st.info("No critical findings")

        with col2:
            st.markdown(f"""
            <h3 style="color: {COLORS['success']};">Positive Signals</h3>
            """, unsafe_allow_html=True)
            if positive_signals:
                for signal in positive_signals:
                    st.markdown(f"- {signal}")
            else:
                st.info("No positive signals identified")

        with col3:
            st.markdown(f"""
            <h3 style="color: {COLORS['primary']};">Recommended Actions</h3>
            """, unsafe_allow_html=True)
            if recommended_actions:
                for action in recommended_actions:
                    st.markdown(f"- {action}")
            else:
                st.info("No actions recommended")

st.markdown("---")

# All Accounts Overview
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    All Accounts Overview
</h2>
""", unsafe_allow_html=True)

# Build accounts table
table_data = []
for acc in accounts:
    acc_name = acc.get("account_name", "Unknown")
    health = acc.get("account_health_score", 0)
    risk = acc.get("churn_risk", "Unknown")

    table_data.append({
        "Account": acc_name,
        "Health Score": f"{health:.0f}",
        "Churn Risk": risk,
        "Orders": acc.get("total_orders", 0),
        "Total Spend": f"${acc.get('total_spend', 0):,.0f}",
        "Deployments": acc.get("total_deployments", 0),
        "Support Cases": acc.get("total_support_cases", 0),
        "S1 Cases": acc.get("s1_cases", 0),
        "Frustration": f"{acc.get('avg_frustration_score', 0):.1f}",
    })

if table_data:
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

# Account health distribution
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    # Health score distribution
    health_scores = [a.get("account_health_score", 0) for a in accounts]

    if health_scores:
        fig_health = go.Figure(go.Histogram(
            x=health_scores,
            nbinsx=10,
            marker_color=COLORS['primary']
        ))
        fig_health.update_layout(
            title={'text': 'Account Health Score Distribution', 'font': {'color': COLORS['white']}},
            height=300,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            xaxis={'title': 'Health Score', 'color': COLORS['text_muted']},
            yaxis={'title': 'Count', 'color': COLORS['text_muted']},
        )
        st.plotly_chart(fig_health, use_container_width=True)

with col2:
    # Churn risk distribution
    risk_counts = {}
    for acc in accounts:
        risk = acc.get("churn_risk", "Unknown")
        risk_counts[risk] = risk_counts.get(risk, 0) + 1

    if risk_counts:
        risk_order = ["Low", "Medium", "High", "Critical", "Unknown"]
        labels = [r for r in risk_order if r in risk_counts]
        values = [risk_counts[r] for r in labels]
        colors = [risk_colors.get(r, COLORS['text_muted']) for r in labels]

        fig_risk = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker_colors=colors,
            textfont={'color': COLORS['white']}
        )])
        fig_risk.update_layout(
            title={'text': 'Churn Risk Distribution', 'font': {'color': COLORS['white']}},
            height=300,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            legend={'font': {'color': COLORS['text']}}
        )
        st.plotly_chart(fig_risk, use_container_width=True)
