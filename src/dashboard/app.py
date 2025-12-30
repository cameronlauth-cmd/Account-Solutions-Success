"""
TrueNAS Enterprise Account Health Dashboard
Main Streamlit application entry point with file upload capability.
"""

import json
import re
import subprocess
import sys
import streamlit as st
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core import Config
from src.dashboard.branding import COLORS, get_health_color, get_health_status
from src.dashboard.styles import get_global_css


def get_available_analyses():
    """Get list of available analysis folders (both single and full analysis)."""
    outputs_dir = Config.OUTPUT_DIR
    if not outputs_dir.exists():
        return []

    analyses = []
    for folder in sorted(outputs_dir.iterdir(), reverse=True):
        if not folder.is_dir():
            continue

        # Handle traditional single-source analysis
        if folder.name.startswith("analysis_"):
            summary_file = folder / "json" / "summary_statistics.json"
            if summary_file.exists():
                try:
                    with open(summary_file) as f:
                        data = json.load(f)
                    analyses.append({
                        "folder": folder,
                        "name": folder.name,
                        "account": data.get("account_name", "Unknown"),
                        "date": data.get("analysis_date", "Unknown"),
                        "health_score": data.get("account_health_score", 0),
                        "total_cases": data.get("total_cases", 0),
                        "analysis_type": "single",
                    })
                except Exception:
                    pass

        # Handle full multi-source analysis
        elif folder.name.startswith("full_analysis_"):
            link_summary_file = folder / "json" / "link_summary.json"
            account_metrics_file = folder / "json" / "account_metrics.json"
            if link_summary_file.exists():
                try:
                    with open(link_summary_file) as f:
                        link_data = json.load(f)

                    # Try to get account name from account metrics
                    account_name = "Multi-Account"
                    if account_metrics_file.exists():
                        with open(account_metrics_file) as f:
                            acct_data = json.load(f)
                            accounts = acct_data.get("accounts", {})
                            if accounts:
                                # Get first account name
                                if isinstance(accounts, dict):
                                    account_name = list(accounts.keys())[0]
                                elif isinstance(accounts, list) and accounts:
                                    account_name = accounts[0].get("account_name", "Multi-Account")

                    # Extract timestamp from folder name
                    timestamp = folder.name.replace("full_analysis_", "")
                    date_str = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"

                    analyses.append({
                        "folder": folder,
                        "name": folder.name,
                        "account": account_name,
                        "date": date_str,
                        "health_score": 0,  # Will show linked orders instead
                        "total_cases": link_data.get("total_cases", 0),
                        "total_orders": link_data.get("total_orders", 0),
                        "fully_linked": link_data.get("fully_linked_orders", 0),
                        "analysis_type": "full",
                    })
                except Exception:
                    pass

    return analyses


def load_analysis_data(folder: Path):
    """Load all analysis data from a folder (single or full analysis)."""
    data = {}

    # Determine analysis type
    is_full = folder.name.startswith("full_analysis_")
    data["analysis_type"] = "full" if is_full else "single"

    json_dir = folder / "json"

    if is_full:
        # Load full analysis data
        files_to_load = {
            "link_summary": "link_summary.json",
            "opportunities": "opportunities.json",
            "deployments": "deployments.json",
            "support_cases": "support_cases.json",
            "cross_layer_insights": "cross_layer_insights.json",
            "product_metrics": "product_metrics.json",
            "account_metrics": "account_metrics.json",
            "usecase_metrics": "usecase_metrics.json",
            "service_metrics": "service_metrics.json",
        }

        for key, filename in files_to_load.items():
            filepath = json_dir / filename
            if filepath.exists():
                with open(filepath) as f:
                    data[key] = json.load(f)

        # Create a summary-like object for compatibility with existing pages
        if "link_summary" in data:
            ls = data["link_summary"]
            data["summary"] = {
                "total_cases": ls.get("total_cases", 0),
                "total_orders": ls.get("total_orders", 0),
                "fully_linked_orders": ls.get("fully_linked_orders", 0),
                "total_opportunities": ls.get("total_opportunities", 0),
                "total_deployments": ls.get("total_deployments", 0),
            }
            # Try to get account name
            if "account_metrics" in data:
                accounts = data["account_metrics"].get("accounts", {})
                if isinstance(accounts, dict) and accounts:
                    data["summary"]["account_name"] = list(accounts.keys())[0]
                elif isinstance(accounts, list) and accounts:
                    data["summary"]["account_name"] = accounts[0].get("account_name", "Multi-Account")

    else:
        # Load traditional single-source analysis data
        summary_file = json_dir / "summary_statistics.json"
        if summary_file.exists():
            with open(summary_file) as f:
                data["summary"] = json.load(f)

        cases_file = json_dir / "top_25_critical_cases.json"
        if cases_file.exists():
            with open(cases_file) as f:
                data["cases"] = json.load(f)

        all_cases_file = json_dir / "all_cases.json"
        if all_cases_file.exists():
            with open(all_cases_file) as f:
                data["all_cases"] = json.load(f)

    # Get chart paths (both types may have charts)
    charts_dir = folder / "charts"
    if charts_dir.exists():
        data["charts"] = {
            f.stem: str(f) for f in charts_dir.glob("*.png")
        }

    return data


def save_uploaded_file(uploaded_file) -> Path:
    """Save uploaded file to input directory."""
    Config.ensure_directories()
    dest = Config.INPUT_DIR / uploaded_file.name
    with open(dest, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return dest


def run_analysis_with_progress(file_path: Path, skip_sonnet: bool) -> tuple:
    """
    Run analysis as subprocess and capture output for progress display.
    Returns (success: bool, output_dir: str or None, error: str or None)
    """
    cmd = [sys.executable, "-m", "src.cli", "analyze", str(file_path)]
    if skip_sonnet:
        cmd.append("--skip-sonnet")

    # Create placeholders for progress display
    st.markdown(f"""
    <div style="background: {COLORS['surface']}; padding: 1.5rem; border-radius: 8px;
                border-left: 4px solid {COLORS['primary']}; margin-bottom: 1rem;">
        <h3 style="color: {COLORS['white']}; margin: 0 0 0.5rem 0;">Analysis in Progress</h3>
        <p style="color: {COLORS['text_muted']}; margin: 0;">
            File: {file_path.name}<br>
            Mode: {"Quick (Haiku only)" if skip_sonnet else "Full (Haiku + Sonnet)"}
        </p>
    </div>
    """, unsafe_allow_html=True)

    progress_bar = st.progress(0, text="Starting analysis...")
    status_container = st.empty()
    log_expander = st.expander("View Analysis Log", expanded=True)
    log_area = log_expander.empty()

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=str(PROJECT_ROOT)
    )

    log_lines = []
    stage = 0
    total_stages = 7 if skip_sonnet else 9
    output_dir = None

    for line in process.stdout:
        line = line.strip()
        if not line:
            continue

        log_lines.append(line)

        # Parse stage progress
        if "STAGE" in line:
            match = re.search(r'STAGE (\d+)', line)
            if match:
                stage = int(match.group(1))
                progress = min(stage / total_stages, 0.95)
                progress_bar.progress(progress, text=f"Stage {stage}/{total_stages}")

        # Parse output directory
        if "Output saved to:" in line or "output_dir" in line.lower():
            match = re.search(r'outputs[/\\]analysis_\d{8}_\d{6}', line)
            if match:
                output_dir = match.group(0)

        # Update status with current activity
        if "[" in line and "/" in line and "]" in line:
            status_container.markdown(f"""
            <div style="color: {COLORS['text_muted']}; font-size: 0.9rem; padding: 0.5rem 0;">
                {line[:100]}...
            </div>
            """, unsafe_allow_html=True)

        # Update log display
        log_area.code("\n".join(log_lines[-20:]), language=None)

    return_code = process.wait()
    success = return_code == 0

    if success:
        progress_bar.progress(1.0, text="Analysis complete!")
        status_container.success("Analysis completed successfully!")
    else:
        progress_bar.progress(1.0, text="Analysis failed")
        status_container.error("Analysis failed. Check the log for details.")

    return success, output_dir, None if success else "Analysis process failed"


def render_analysis_card(analysis: dict, index: int):
    """Render a card for an existing analysis."""
    is_full = analysis.get("analysis_type") == "full"

    if is_full:
        # Full analysis card - show linked orders instead of health score
        total_orders = analysis.get('total_orders', 0)
        fully_linked = analysis.get('fully_linked', 0)
        link_pct = (fully_linked / total_orders * 100) if total_orders > 0 else 0

        # Color based on link percentage
        if link_pct >= 50:
            card_color = COLORS['success']
        elif link_pct >= 25:
            card_color = COLORS['warning']
        else:
            card_color = COLORS['primary']

        st.markdown(f"""
        <div style="background: {COLORS['surface']}; padding: 1rem; border-radius: 8px;
                    border-left: 3px solid {card_color}; margin-bottom: 0.75rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div style="color: {COLORS['white']}; font-weight: 600; font-size: 1.1rem;">
                        {analysis['account']}
                        <span style="background: {COLORS['primary']}; color: white; padding: 2px 8px;
                                     border-radius: 4px; font-size: 0.7rem; margin-left: 8px;">FULL</span>
                    </div>
                    <div style="color: {COLORS['text_muted']}; font-size: 0.85rem; margin-top: 0.25rem;">
                        {analysis['date']} &bull; {analysis['total_cases']} cases &bull; {total_orders} orders
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="color: {card_color}; font-size: 1.2rem; font-weight: 700;">
                        {fully_linked}/{total_orders}
                    </div>
                    <div style="color: {COLORS['text_muted']}; font-size: 0.75rem;">
                        linked orders
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("View Full Dashboard", key=f"view_{index}", use_container_width=True):
            st.session_state["analysis_folder"] = analysis["folder"]
            st.session_state["analysis_data"] = load_analysis_data(analysis["folder"])
            st.switch_page("pages/6_Opportunities.py")
    else:
        # Traditional single-source analysis card
        health = analysis['health_score']
        health_color = get_health_color(health)
        health_status = get_health_status(health)

        st.markdown(f"""
        <div style="background: {COLORS['surface']}; padding: 1rem; border-radius: 8px;
                    border-left: 3px solid {health_color}; margin-bottom: 0.75rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div style="color: {COLORS['white']}; font-weight: 600; font-size: 1.1rem;">
                        {analysis['account']}
                    </div>
                    <div style="color: {COLORS['text_muted']}; font-size: 0.85rem; margin-top: 0.25rem;">
                        {analysis['date']} &bull; {analysis['total_cases']} cases
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="color: {health_color}; font-size: 1.5rem; font-weight: 700;">
                        {health:.0f}
                    </div>
                    <div style="color: {health_color}; font-size: 0.75rem;">
                        {health_status}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("View Dashboard", key=f"view_{index}", use_container_width=True):
            st.session_state["analysis_folder"] = analysis["folder"]
            st.session_state["analysis_data"] = load_analysis_data(analysis["folder"])
            st.switch_page("pages/1_Overview.py")


# Page configuration
st.set_page_config(
    page_title="TrueNAS Enterprise - Account Health",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Apply global TrueNAS branded dark theme
st.markdown(get_global_css(), unsafe_allow_html=True)

# Initialize session state
if "analysis_running" not in st.session_state:
    st.session_state["analysis_running"] = False

# Header
st.markdown(f"""
<div style="text-align: center; padding: 2rem 0 1rem 0;">
    <span style="font-size: 2rem; font-weight: 800; color: {COLORS['primary']};">TrueNAS</span>
    <span style="font-size: 2rem; font-weight: 800; color: {COLORS['white']};">Enterprise</span>
    <div style="color: {COLORS['text_muted']}; font-size: 1.1rem; margin-top: 0.5rem;">
        Account Health Dashboard
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Check if analysis is running
if st.session_state.get("analysis_running"):
    # Show analysis in progress
    uploaded_file = st.session_state.get("uploaded_file")
    skip_sonnet = st.session_state.get("skip_sonnet", False)

    if uploaded_file:
        file_path = save_uploaded_file(uploaded_file)
        success, output_dir, error = run_analysis_with_progress(file_path, skip_sonnet)

        st.session_state["analysis_running"] = False
        st.session_state["uploaded_file"] = None

        if success:
            st.balloons()
            st.markdown(f"""
            <div style="background: {COLORS['surface']}; padding: 1.5rem; border-radius: 8px;
                        border-left: 4px solid {COLORS['success']}; margin: 1rem 0;">
                <h3 style="color: {COLORS['success']}; margin: 0 0 0.5rem 0;">Analysis Complete!</h3>
                <p style="color: {COLORS['text_muted']}; margin: 0;">
                    Results saved to: {output_dir}
                </p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("View Results", type="primary", use_container_width=True):
                st.rerun()
        else:
            st.error(f"Analysis failed: {error}")
            if st.button("Try Again"):
                st.rerun()
else:
    # Two-column layout: Upload on left, Existing analyses on right
    col_upload, col_existing = st.columns([1, 1], gap="large")

    with col_upload:
        st.markdown(f"""
        <h2 style="color: {COLORS['white']}; font-size: 1.4rem; margin-bottom: 1rem;
                   border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
            New Analysis
        </h2>
        """, unsafe_allow_html=True)

        # File upload zone
        uploaded_file = st.file_uploader(
            "Upload Excel File",
            type=["xlsx", "xls"],
            help="Upload an Excel file with support case data for analysis",
            label_visibility="collapsed"
        )

        if uploaded_file:
            st.success(f"File ready: {uploaded_file.name}")

            # Analysis mode selection
            st.markdown(f"""
            <div style="color: {COLORS['text_muted']}; font-size: 0.9rem; margin: 1rem 0 0.5rem 0;">
                Analysis Mode
            </div>
            """, unsafe_allow_html=True)

            mode = st.radio(
                "Analysis Mode",
                options=["full", "quick"],
                format_func=lambda x: "Full Analysis (~40 min)" if x == "full" else "Quick Analysis (~15 min)",
                captions=[
                    "Claude Haiku + Sonnet with detailed timelines",
                    "Claude Haiku only - faster, lower cost"
                ],
                label_visibility="collapsed",
                horizontal=False
            )

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("Start Analysis", type="primary", use_container_width=True):
                st.session_state["analysis_running"] = True
                st.session_state["uploaded_file"] = uploaded_file
                st.session_state["skip_sonnet"] = (mode == "quick")
                st.rerun()
        else:
            st.markdown(f"""
            <div style="background: {COLORS['surface']}; padding: 2rem; border-radius: 8px;
                        border: 2px dashed {COLORS['border']}; text-align: center; margin: 1rem 0;">
                <div style="color: {COLORS['text_muted']}; font-size: 1rem;">
                    Drag and drop an Excel file here<br>
                    <span style="font-size: 0.85rem;">or click to browse</span>
                </div>
                <div style="color: {COLORS['text_muted']}; font-size: 0.8rem; margin-top: 1rem;">
                    Supported formats: .xlsx, .xls
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_existing:
        st.markdown(f"""
        <h2 style="color: {COLORS['white']}; font-size: 1.4rem; margin-bottom: 1rem;
                   border-bottom: 2px solid {COLORS['primary']}; padding-bottom: 0.5rem;">
            Existing Analyses
        </h2>
        """, unsafe_allow_html=True)

        analyses = get_available_analyses()

        if not analyses:
            st.markdown(f"""
            <div style="background: {COLORS['surface']}; padding: 2rem; border-radius: 8px;
                        text-align: center; color: {COLORS['text_muted']};">
                <div style="font-size: 1rem; margin-bottom: 0.5rem;">No analyses found</div>
                <div style="font-size: 0.85rem;">Upload a file to run your first analysis</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Create a scrollable container for analysis cards
            for idx, analysis in enumerate(analyses):
                render_analysis_card(analysis, idx)
