"""
Export Page - Generate PDF or HTML reports
"""

import streamlit as st
import json
from pathlib import Path
from datetime import datetime
import io
import sys

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.dashboard.branding import COLORS, get_logo_html
from src.dashboard.styles import get_global_css
from src.reports.pdf_generator import generate_pdf_report

# Apply global styling
st.markdown(get_global_css(), unsafe_allow_html=True)


def generate_html_report(summary, cases_data, charts, include_charts, include_case_details, include_timelines):
    """Generate a self-contained HTML report."""

    account_name = summary.get("account_name", "Unknown")
    health_score = summary.get("account_health_score", 0)
    analysis_date = summary.get("analysis_date", "N/A")

    # Determine health status
    if health_score >= 80:
        health_color = "#28a745"
        health_status = "Healthy"
    elif health_score >= 60:
        health_color = "#ffc107"
        health_status = "At Risk"
    else:
        health_color = "#dc3545"
        health_status = "Critical"

    cases = cases_data.get("cases", [])

    # Build HTML
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sentiment Analysis Report - {account_name}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #0066cc, #004499);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{ margin: 0 0 10px 0; }}
        .header p {{ margin: 0; opacity: 0.9; }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            margin-top: 0;
            border-bottom: 2px solid #0066cc;
            padding-bottom: 10px;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .metric {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #0066cc;
        }}
        .metric-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .health-score {{
            text-align: center;
            padding: 30px;
        }}
        .health-value {{
            font-size: 4em;
            font-weight: bold;
            color: {health_color};
        }}
        .health-status {{
            font-size: 1.2em;
            color: {health_color};
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        tr:hover {{ background: #f5f5f5; }}
        .severity-S1 {{ color: #dc3545; font-weight: bold; }}
        .severity-S2 {{ color: #fd7e14; font-weight: bold; }}
        .severity-S3 {{ color: #ffc107; }}
        .severity-S4 {{ color: #28a745; }}
        .footer {{
            text-align: center;
            color: #666;
            padding: 20px;
            font-size: 0.9em;
        }}
        .case-detail {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Customer Sentiment Analysis Report</h1>
        <p><strong>{account_name}</strong> | Analysis Date: {analysis_date}</p>
    </div>

    <div class="card">
        <div class="health-score">
            <div class="health-value">{health_score:.0f}/100</div>
            <div class="health-status">{health_status}</div>
        </div>
    </div>

    <div class="card">
        <h2>Key Metrics</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{summary.get('total_cases', 0)}</div>
                <div class="metric-label">Total Cases</div>
            </div>
            <div class="metric">
                <div class="metric-value">{(summary.get('claude_statistics') or {}).get('high_frustration', 0)}</div>
                <div class="metric-label">High Frustration Cases</div>
            </div>
            <div class="metric">
                <div class="metric-value">{(summary.get('claude_statistics') or {}).get('avg_frustration_score', 0):.1f}/10</div>
                <div class="metric-label">Avg Frustration</div>
            </div>
            <div class="metric">
                <div class="metric-value">{(summary.get('claude_statistics') or {}).get('frustrated_messages_count', 0)}</div>
                <div class="metric-label">Frustrated Messages</div>
            </div>
        </div>
    </div>
"""

    # Add case table if requested
    if include_case_details and cases:
        html += """
    <div class="card">
        <h2>Case Summary</h2>
        <table>
            <thead>
                <tr>
                    <th>Case #</th>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>Frustration</th>
                    <th>Criticality</th>
                    <th>Issue Type</th>
                </tr>
            </thead>
            <tbody>
"""
        for case in cases[:25]:  # Limit to top 25
            claude = case.get("claude_analysis") or {}
            severity = case.get("severity", "")
            html += f"""
                <tr>
                    <td>{case.get('case_number')}</td>
                    <td class="severity-{severity}">{severity}</td>
                    <td>{case.get('status', 'N/A')}</td>
                    <td>{claude.get('frustration_score', 0)}/10</td>
                    <td>{case.get('criticality_score', 0)} pts</td>
                    <td>{claude.get('issue_class', 'Unknown')}</td>
                </tr>
"""
        html += """
            </tbody>
        </table>
    </div>
"""

    # Add timelines if requested
    if include_timelines:
        cases_with_timelines = [c for c in cases if (c.get("deepseek_analysis") or {}).get("timeline_entries")]
        if cases_with_timelines:
            html += """
    <div class="card">
        <h2>Critical Case Timelines</h2>
"""
            for case in cases_with_timelines[:3]:  # Top 3 with timelines
                deepseek = case.get("deepseek_analysis") or {}
                html += f"""
        <div class="case-detail">
            <h3>Case {case.get('case_number')} - Criticality: {case.get('criticality_score', 0)}</h3>
            <p><strong>Pain Points:</strong> {deepseek.get('pain_points', 'N/A')}</p>
            <p><strong>Recommended Action:</strong> {deepseek.get('recommended_action', 'N/A')}</p>
        </div>
"""
            html += """
    </div>
"""

    # Footer
    html += f"""
    <div class="footer">
        <p>Generated by TrueNAS Sentiment Analysis | {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <p>Powered by Claude AI</p>
    </div>
</body>
</html>
"""

    return html


# Page content starts here
# Get data from session state
data = st.session_state.get("analysis_data", {})
analysis_folder = st.session_state.get("analysis_folder")
summary = data.get("summary", {})
cases_data = data.get("cases", {})

if not summary:
    st.warning("No analysis data available. Please select an analysis from the sidebar.")
    st.stop()

# Branded header
account_name = summary.get("account_name", "Unknown")

logo_html = get_logo_html(height=50)
st.markdown(f"""
<div style="background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
            padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;
            border: 1px solid #30363d; border-left: 4px solid #0095D5;">
    <div style="display: flex; align-items: center; gap: 1.5rem;">
        <div>{logo_html}</div>
        <div style="border-left: 2px solid #30363d; padding-left: 1.5rem;">
            <h1 style="color: {COLORS['primary']}; margin: 0; font-size: 1.8rem; font-weight: 600;">Export Report</h1>
            <p style="color: #8b949e; margin: 5px 0 0 0; font-size: 1.1rem;">{account_name} | Generate shareable reports</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Report options
st.markdown(f"<h2 style='color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;'>Report Options</h2>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    include_charts = st.checkbox("Include Charts", value=True)
    include_case_details = st.checkbox("Include Case Details", value=True)

with col2:
    include_timelines = st.checkbox("Include Timelines", value=True)
    include_raw_data = st.checkbox("Include Raw Data", value=False)

st.markdown("---")

# Export buttons
st.markdown(f"<h2 style='color: {COLORS['white']}; border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;'>Download Report</h2>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

# PDF Export (Primary - uses accent green CTA color)
with col1:
    st.markdown(f"<h3 style='color: {COLORS['secondary']};'>PDF Report</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: {COLORS['text_muted']};'>Professional branded report for executives</p>", unsafe_allow_html=True)

    if st.button("Generate PDF", type="primary", use_container_width=True):
        with st.spinner("Generating PDF report..."):
            try:
                pdf_bytes = generate_pdf_report(summary, cases_data)
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name=f"account_health_report_{summary.get('account_name', 'unknown')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("PDF generated successfully!")
            except Exception as e:
                st.error(f"Error generating PDF: {str(e)}")

# HTML Export
with col2:
    st.markdown(f"<h3 style='color: {COLORS['secondary']};'>HTML Report</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: {COLORS['text_muted']};'>Interactive report for browsers</p>", unsafe_allow_html=True)

    if st.button("Generate HTML", use_container_width=True):
        with st.spinner("Generating HTML report..."):
            html_content = generate_html_report(
                summary, cases_data, data.get("charts", {}),
                include_charts, include_case_details, include_timelines
            )

            st.download_button(
                label="Download HTML",
                data=html_content,
                file_name=f"account_health_report_{summary.get('account_name', 'unknown')}_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html",
                use_container_width=True
            )

# JSON Export
with col3:
    st.markdown(f"<h3 style='color: {COLORS['secondary']};'>JSON Data</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: {COLORS['text_muted']};'>Raw data for processing</p>", unsafe_allow_html=True)

    if st.button("Generate JSON", use_container_width=True):
        export_data = {
            "summary": summary,
            "cases": cases_data.get("cases", []) if include_case_details else [],
            "export_date": datetime.now().isoformat(),
        }

        json_str = json.dumps(export_data, indent=2, default=str)

        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name=f"account_health_data_{summary.get('account_name', 'unknown')}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )

# CSV Export
with col4:
    st.markdown(f"<h3 style='color: {COLORS['secondary']};'>CSV Data</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: {COLORS['text_muted']};'>Spreadsheet format</p>", unsafe_allow_html=True)

    if st.button("Generate CSV", use_container_width=True):
        import pandas as pd

        cases = cases_data.get("cases", [])
        if cases:
            csv_data = []
            for c in cases:
                claude = c.get("claude_analysis") or {}
                deepseek = c.get("deepseek_analysis") or {}
                csv_data.append({
                    "Case Number": c.get("case_number"),
                    "Customer": c.get("customer_name"),
                    "Severity": c.get("severity"),
                    "Support Level": c.get("support_level"),
                    "Status": c.get("status"),
                    "Age (Days)": c.get("case_age_days"),
                    "Criticality Score": c.get("criticality_score"),
                    "Frustration Score": claude.get("frustration_score"),
                    "Issue Type": claude.get("issue_class"),
                    "Resolution Outlook": claude.get("resolution_outlook"),
                    "Key Phrase": claude.get("key_phrase"),
                    "Pain Points": deepseek.get("pain_points", ""),
                    "Recommended Action": deepseek.get("recommended_action", ""),
                })

            df = pd.DataFrame(csv_data)
            csv_str = df.to_csv(index=False)

            st.download_button(
                label="Download CSV",
                data=csv_str,
                file_name=f"cases_{summary.get('account_name', 'unknown')}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning("No case data to export")

st.markdown("---")

# Preview section
st.markdown(f"<h3 style='color: {COLORS['secondary']};'>Report Preview</h3>", unsafe_allow_html=True)

with st.expander("Preview HTML Report", expanded=False):
    preview_html = generate_html_report(
        summary, cases_data, {},
        include_charts=False, include_case_details=True, include_timelines=False
    )
    st.components.v1.html(preview_html, height=600, scrolling=True)

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: {COLORS['text_muted']}; padding: 1rem;">
    <p>TrueNAS Enterprise - Account Health Reports</p>
    <p style="font-size: 0.85rem;">Reports are generated with AI-powered analysis</p>
</div>
""", unsafe_allow_html=True)
