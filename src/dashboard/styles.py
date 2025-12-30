"""
TrueNAS Enterprise Dashboard Styles

Dark mode CSS for Streamlit with TrueNAS brand colors.
"""

from .branding import COLORS, FONTS


def get_global_css() -> str:
    """Generate global CSS for the entire dashboard."""
    return f"""
    <style>
        /* Import Inter font from Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

        /* Global dark theme */
        .stApp {{
            background-color: {COLORS["background"]};
            font-family: {FONTS["family"]};
            font-size: 16px;
        }}

        /* Main content area */
        .main .block-container {{
            background-color: {COLORS["background"]};
            padding-top: 2rem;
            font-size: 1.1rem;
        }}

        /* Headers - Increased sizes */
        h1, h2, h3, h4, h5, h6 {{
            color: {COLORS["white"]} !important;
            font-family: {FONTS["family"]} !important;
        }}

        h1 {{
            font-weight: {FONTS["headline"]} !important;
            color: {COLORS["primary"]} !important;
            font-size: 2.2rem !important;
        }}

        h2 {{
            font-weight: {FONTS["subhead"]} !important;
            border-bottom: 2px solid {COLORS["primary"]};
            padding-bottom: 0.5rem;
            font-size: 1.8rem !important;
        }}

        h3 {{
            font-weight: {FONTS["subhead"]} !important;
            color: {COLORS["secondary"]} !important;
            font-size: 1.4rem !important;
        }}

        h4 {{
            font-size: 1.2rem !important;
        }}

        /* Body text - Larger */
        p, span, div, label {{
            color: {COLORS["text"]} !important;
        }}

        p {{
            font-size: 1.1rem !important;
            line-height: 1.6 !important;
        }}

        /* Markdown text */
        .stMarkdown {{
            font-size: 1.1rem !important;
        }}

        .stMarkdown p {{
            font-size: 1.1rem !important;
            line-height: 1.6 !important;
        }}

        /* Sidebar styling */
        [data-testid="stSidebar"] {{
            background-color: {COLORS["surface"]};
            border-right: 1px solid {COLORS["border"]};
        }}

        [data-testid="stSidebar"] .stMarkdown {{
            color: {COLORS["text"]};
        }}

        /* Metrics styling - Larger text */
        [data-testid="stMetric"] {{
            background-color: {COLORS["surface"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 8px;
            padding: 1.25rem;
            border-left: 3px solid {COLORS["primary"]};
        }}

        [data-testid="stMetricLabel"] {{
            color: {COLORS["text_muted"]} !important;
            font-weight: {FONTS["body"]};
            font-size: 1rem !important;
        }}

        [data-testid="stMetricValue"] {{
            color: {COLORS["white"]} !important;
            font-weight: {FONTS["headline"]};
            font-size: 2rem !important;
        }}

        [data-testid="stMetricDelta"] {{
            color: {COLORS["secondary"]} !important;
            font-size: 1rem !important;
        }}

        /* DataFrames / Tables - Larger text */
        .stDataFrame {{
            background-color: {COLORS["surface"]};
            border-radius: 8px;
            overflow: hidden;
            font-size: 1rem !important;
        }}

        .stDataFrame thead tr {{
            background-color: {COLORS["primary"]} !important;
        }}

        .stDataFrame thead th {{
            color: {COLORS["white"]} !important;
            font-weight: {FONTS["subhead"]} !important;
            padding: 14px !important;
            font-size: 1rem !important;
        }}

        .stDataFrame tbody tr {{
            background-color: {COLORS["surface"]} !important;
            border-bottom: 1px solid {COLORS["border"]} !important;
        }}

        .stDataFrame tbody tr:hover {{
            background-color: {COLORS["surface_light"]} !important;
        }}

        .stDataFrame tbody td {{
            color: {COLORS["text"]} !important;
            padding: 12px !important;
            font-size: 1rem !important;
        }}

        /* Expanders */
        .streamlit-expanderHeader {{
            background-color: {COLORS["surface"]} !important;
            border: 1px solid {COLORS["border"]} !important;
            border-radius: 8px !important;
            color: {COLORS["white"]} !important;
        }}

        .streamlit-expanderHeader:hover {{
            background-color: {COLORS["surface_light"]} !important;
            border-color: {COLORS["primary"]} !important;
        }}

        .streamlit-expanderContent {{
            background-color: {COLORS["surface"]} !important;
            border: 1px solid {COLORS["border"]} !important;
            border-top: none !important;
            border-radius: 0 0 8px 8px !important;
        }}

        /* Buttons */
        .stButton > button {{
            background-color: {COLORS["primary"]} !important;
            color: {COLORS["white"]} !important;
            border: none !important;
            border-radius: 6px !important;
            font-weight: {FONTS["subhead"]} !important;
            padding: 0.5rem 1rem !important;
            transition: all 0.2s ease !important;
        }}

        .stButton > button:hover {{
            background-color: {COLORS["secondary"]} !important;
            transform: translateY(-1px);
        }}

        /* Download button - accent green for CTAs */
        .stDownloadButton > button {{
            background-color: {COLORS["accent"]} !important;
            color: {COLORS["white"]} !important;
        }}

        .stDownloadButton > button:hover {{
            background-color: #5fa038 !important;
        }}

        /* Select boxes */
        .stSelectbox > div > div {{
            background-color: {COLORS["surface"]} !important;
            border: 1px solid {COLORS["border"]} !important;
            color: {COLORS["text"]} !important;
        }}

        /* Multiselect */
        .stMultiSelect > div > div {{
            background-color: {COLORS["surface"]} !important;
            border: 1px solid {COLORS["border"]} !important;
        }}

        /* Sliders */
        .stSlider > div > div {{
            background-color: {COLORS["primary"]} !important;
        }}

        /* Info/Warning/Error/Success boxes */
        .stAlert {{
            border-radius: 8px !important;
        }}

        /* Dividers */
        hr {{
            border-color: {COLORS["border"]} !important;
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            background-color: {COLORS["surface"]};
            border-radius: 8px;
            padding: 4px;
        }}

        .stTabs [data-baseweb="tab"] {{
            color: {COLORS["text_muted"]} !important;
            border-radius: 6px !important;
        }}

        .stTabs [aria-selected="true"] {{
            background-color: {COLORS["primary"]} !important;
            color: {COLORS["white"]} !important;
        }}

        /* Progress bars */
        .stProgress > div > div {{
            background-color: {COLORS["primary"]} !important;
        }}

        /* Caption text */
        .stCaption {{
            color: {COLORS["text_muted"]} !important;
        }}

        /* Code blocks */
        .stCodeBlock {{
            background-color: {COLORS["surface"]} !important;
            border: 1px solid {COLORS["border"]} !important;
        }}
    </style>
    """


def get_header_html(title: str, subtitle: str = "") -> str:
    """Generate branded header HTML."""
    from .branding import get_logo_html

    logo_html = get_logo_html(height=36)
    subtitle_html = f'<p style="color: {COLORS["text_muted"]}; margin: 5px 0 0 0; font-size: 0.9em;">{subtitle}</p>' if subtitle else ""

    return f"""
    <div style="background: linear-gradient(135deg, {COLORS["surface"]} 0%, {COLORS["background"]} 100%);
                padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;
                border: 1px solid {COLORS["border"]}; border-left: 4px solid {COLORS["primary"]};">
        <div style="display: flex; align-items: center; gap: 1rem;">
            {logo_html}
            <div>
                <h1 style="color: {COLORS["white"]}; margin: 0; font-family: {FONTS["family"]};
                           font-weight: {FONTS["headline"]}; font-size: 1.8rem;">{title}</h1>
                {subtitle_html}
            </div>
        </div>
    </div>
    """


def get_metric_card_html(label: str, value: str, color: str = None, icon: str = "") -> str:
    """Generate a branded metric card."""
    border_color = color or COLORS["primary"]
    icon_html = f'<span style="font-size: 1.5em; margin-right: 8px;">{icon}</span>' if icon else ""

    return f"""
    <div style="background-color: {COLORS["surface"]}; border: 1px solid {COLORS["border"]};
                border-left: 4px solid {border_color}; border-radius: 8px; padding: 1rem;
                margin: 0.5rem 0;">
        <div style="color: {COLORS["text_muted"]}; font-size: 0.85rem; margin-bottom: 0.5rem;">
            {label}
        </div>
        <div style="color: {COLORS["white"]}; font-size: 1.5rem; font-weight: {FONTS["headline"]};">
            {icon_html}{value}
        </div>
    </div>
    """


def get_health_gauge_html(score: float, label: str = "Account Health Score") -> str:
    """Generate a visual health score gauge."""
    from .branding import get_health_color, get_health_status

    color = get_health_color(score)
    status = get_health_status(score)

    # Calculate gauge fill percentage
    fill_pct = min(max(score, 0), 100)

    return f"""
    <div style="background-color: {COLORS["surface"]}; border-radius: 12px; padding: 1.5rem;
                border: 1px solid {COLORS["border"]}; text-align: center;">
        <div style="color: {COLORS["text_muted"]}; font-size: 0.9rem; margin-bottom: 0.5rem;">
            {label}
        </div>
        <div style="font-size: 3rem; font-weight: {FONTS["headline"]}; color: {color};">
            {score:.1f}
        </div>
        <div style="color: {color}; font-size: 1.1rem; font-weight: {FONTS["subhead"]};">
            {status}
        </div>
        <div style="background-color: {COLORS["border"]}; border-radius: 4px; height: 8px;
                    margin-top: 1rem; overflow: hidden;">
            <div style="background-color: {color}; height: 100%; width: {fill_pct}%;
                        border-radius: 4px; transition: width 0.5s ease;"></div>
        </div>
    </div>
    """


def get_callout_html(content: str, callout_type: str = "info", title: str = "") -> str:
    """Generate a branded callout box."""
    colors_map = {
        "info": (COLORS["primary"], COLORS["surface"]),
        "warning": (COLORS["warning"], "#2d2315"),
        "error": (COLORS["critical"], "#2d1515"),
        "success": (COLORS["success"], "#152d15"),
    }

    border_color, bg_color = colors_map.get(callout_type, colors_map["info"])
    title_html = f'<strong style="color: {border_color};">{title}</strong><br/>' if title else ""

    return f"""
    <div style="background-color: {bg_color}; border-left: 4px solid {border_color};
                padding: 1rem; margin: 0.75rem 0; border-radius: 0 8px 8px 0;">
        {title_html}
        <span style="color: {COLORS["text"]};">{content}</span>
    </div>
    """


def get_section_header_html(title: str, icon: str = "") -> str:
    """Generate a styled section header."""
    icon_html = f'<span style="margin-right: 8px;">{icon}</span>' if icon else ""

    return f"""
    <div style="border-bottom: 2px solid {COLORS["primary"]}; padding-bottom: 0.5rem;
                margin: 1.5rem 0 1rem 0;">
        <h2 style="color: {COLORS["white"]}; margin: 0; font-weight: {FONTS["subhead"]};
                   font-family: {FONTS["family"]};">
            {icon_html}{title}
        </h2>
    </div>
    """


def get_quote_html(quote: str, source: str = "Customer") -> str:
    """Generate a styled quote block."""
    return f"""
    <div style="background-color: {COLORS["surface"]}; border-left: 4px solid {COLORS["warning"]};
                padding: 1rem 1.5rem; margin: 1rem 0; border-radius: 0 8px 8px 0;
                font-style: italic;">
        <span style="color: {COLORS["text"]}; font-size: 1.1rem;">"{quote}"</span>
        <div style="color: {COLORS["text_muted"]}; font-size: 0.85rem; margin-top: 0.5rem;">
            — {source}
        </div>
    </div>
    """


def get_status_badge_html(status: str, color: str = None) -> str:
    """Generate a status badge."""
    if color is None:
        status_colors = {
            "critical": COLORS["critical"],
            "warning": COLORS["warning"],
            "healthy": COLORS["success"],
            "open": COLORS["warning"],
            "closed": COLORS["text_muted"],
            "pending": COLORS["secondary"],
        }
        color = status_colors.get(status.lower(), COLORS["primary"])

    return f"""
    <span style="background-color: {color}; color: {COLORS["white"]}; padding: 4px 12px;
                 border-radius: 12px; font-size: 0.8rem; font-weight: {FONTS["subhead"]};
                 display: inline-block;">{status}</span>
    """
