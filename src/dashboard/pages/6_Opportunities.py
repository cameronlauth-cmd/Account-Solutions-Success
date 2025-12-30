"""
Opportunities Page - Full Analysis Dashboard
Shows opportunity analysis from the 4-layer pipeline.
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
    page_title="Opportunities - Full Analysis",
    page_icon="💰",
    layout="wide",
)

# Apply global styling
st.markdown(get_global_css(), unsafe_allow_html=True)

# Get data from session state
data = st.session_state.get("analysis_data", {})

if data.get("analysis_type") != "full":
    st.warning("This page requires a Full Analysis. Please select a full analysis from the home page.")
    st.stop()

opportunities_data = data.get("opportunities", {})
link_summary = data.get("link_summary", {})

if not opportunities_data:
    st.warning("No opportunity data available.")
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
                Opportunities Analysis
            </h1>
            <p style="color: #8b949e; margin: 5px 0 0 0; font-size: 1.1rem;">
                Layer 1: Customer Expectations & Use Cases
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Summary metrics
total_opps = opportunities_data.get("total", 0)
analyzed_opps = opportunities_data.get("analyzed", 0)
opps_list = opportunities_data.get("opportunities", [])

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Opportunities", total_opps)

with col2:
    st.metric("Analyzed", analyzed_opps)

with col3:
    total_revenue = sum(o.get("amount", 0) for o in opps_list)
    st.metric("Total Revenue", f"${total_revenue:,.0f}")

with col4:
    linked = link_summary.get("orders_with_opportunity", 0)
    total_orders = link_summary.get("total_orders", 0)
    st.metric("Linked to Orders", f"{linked}/{total_orders}")

st.markdown("---")

# Use Case Distribution
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Use Case Distribution
</h2>
""", unsafe_allow_html=True)

# Extract use cases from analysis results
use_case_counts = {}
for opp in opps_list:
    analysis = opp.get("analysis")
    if analysis:
        use_case = analysis.get("use_case_category", "Unknown")
        use_case_counts[use_case] = use_case_counts.get(use_case, 0) + 1

if use_case_counts:
    col1, col2 = st.columns([1, 1])

    with col1:
        # Pie chart
        fig_pie = go.Figure(data=[go.Pie(
            labels=list(use_case_counts.keys()),
            values=list(use_case_counts.values()),
            hole=0.4,
            textfont={'color': COLORS['white']}
        )])
        fig_pie.update_layout(
            height=300,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            legend={'font': {'color': COLORS['text']}}
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        # Bar chart
        sorted_cases = sorted(use_case_counts.items(), key=lambda x: x[1], reverse=True)
        fig_bar = go.Figure(go.Bar(
            x=[c[1] for c in sorted_cases],
            y=[c[0] for c in sorted_cases],
            orientation='h',
            marker_color=COLORS['primary'],
            text=[c[1] for c in sorted_cases],
            textposition='outside',
            textfont={'color': COLORS['text']}
        ))
        fig_bar.update_layout(
            height=300,
            paper_bgcolor=COLORS['background'],
            plot_bgcolor=COLORS['background'],
            font={'color': COLORS['text']},
            xaxis={'color': COLORS['text_muted']},
            yaxis={'color': COLORS['text']},
            margin=dict(l=0, r=60, t=10, b=40),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# Opportunities Table
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Opportunity Details
</h2>
""", unsafe_allow_html=True)

# Build table data
table_data = []
for opp in opps_list:
    analysis = opp.get("analysis", {})
    table_data.append({
        "Order #": opp.get("order_number", "N/A"),
        "Account": opp.get("account_name", "N/A"),
        "Opportunity": opp.get("opportunity_name", "N/A")[:40] + "..." if len(opp.get("opportunity_name", "")) > 40 else opp.get("opportunity_name", "N/A"),
        "Amount": f"${opp.get('amount', 0):,.0f}",
        "Product": opp.get("primary_product", "N/A"),
        "Use Case": analysis.get("use_case_category", "Unknown") if analysis else "Not Analyzed",
        "Clarity Score": f"{analysis.get('opportunity_score', 0)}/100" if analysis else "N/A",
    })

if table_data:
    df = pd.DataFrame(table_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")

# Detailed Opportunity Cards
st.markdown(f"""
<h2 style="color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
    Opportunity Insights
</h2>
""", unsafe_allow_html=True)

# Show expandable details for each opportunity
for idx, opp in enumerate(opps_list[:10]):  # Limit to first 10
    analysis = opp.get("analysis", {})
    if not analysis:
        continue

    with st.expander(f"{opp.get('account_name', 'Unknown')} - {opp.get('opportunity_name', 'N/A')[:50]}"):
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"**Use Case Summary:** {analysis.get('use_case_extracted', 'N/A')}")
            st.markdown(f"**Business Need:** {analysis.get('business_need_extracted', 'N/A')}")

            pain_points = analysis.get('pain_points_extracted', [])
            if pain_points:
                st.markdown("**Pain Points:**")
                for point in pain_points:
                    st.markdown(f"- {point}")

            expectations = analysis.get('customer_expectations', [])
            if expectations:
                st.markdown("**Customer Expectations:**")
                for exp in expectations:
                    st.markdown(f"- {exp}")

        with col2:
            st.metric("Amount", f"${opp.get('amount', 0):,.0f}")
            st.metric("Use Case Category", analysis.get('use_case_category', 'Unknown'))
            st.metric("Clarity Score", f"{analysis.get('opportunity_score', 0)}/100")
