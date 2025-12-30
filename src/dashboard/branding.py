"""
TrueNAS Enterprise Brand Configuration

Based on TrueNAS Brand Guide July 2025.
"""

from pathlib import Path
from typing import Optional
import base64

# TrueNAS Brand Colors
COLORS = {
    # Primary Brand Colors
    "primary": "#0095D5",       # TrueNAS Blue - main brand color
    "secondary": "#31BEEC",     # Light Blue - accents, highlights
    "gray": "#AEADAE",          # Cool Gray - borders, secondary text
    "accent": "#71BF44",        # Green - CTAs and action buttons ONLY

    # Base Colors
    "white": "#FFFFFF",
    "black": "#000000",

    # Dark Mode Theme Colors
    "background": "#0d1117",    # Dark background (GitHub-style dark)
    "surface": "#161b22",       # Card/surface backgrounds
    "surface_light": "#21262d", # Lighter surface for hover states
    "border": "#30363d",        # Border color

    # Text Colors
    "text": "#FFFFFF",          # Primary text on dark
    "text_muted": "#8b949e",    # Secondary/muted text
    "text_dark": "#000000",     # Text on light backgrounds

    # Status Colors (for health indicators)
    "critical": "#dc3545",      # Red - critical issues
    "warning": "#ffc107",       # Yellow - warnings
    "success": "#28a745",       # Green - positive
    "info": "#0095D5",          # Blue - informational (use primary)
}

# Typography Configuration
FONTS = {
    "family": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    "headline": "800",      # ExtraBold for headlines
    "subhead": "600",       # SemiBold for subheadings
    "body": "400",          # Regular for body text
    "footer": "300",        # Light for footers
}

# Health Score Thresholds and Colors
HEALTH_THRESHOLDS = {
    "critical": 40,     # Below this is critical
    "warning": 60,      # Below this is warning
    "healthy": 80,      # Below this is moderate, above is healthy
}


def get_health_color(score: float) -> str:
    """Get color based on health score."""
    if score < HEALTH_THRESHOLDS["critical"]:
        return COLORS["critical"]
    elif score < HEALTH_THRESHOLDS["warning"]:
        return COLORS["warning"]
    elif score < HEALTH_THRESHOLDS["healthy"]:
        return COLORS["secondary"]
    else:
        return COLORS["success"]


def get_health_status(score: float) -> str:
    """Get status text based on health score."""
    if score < HEALTH_THRESHOLDS["critical"]:
        return "Critical"
    elif score < HEALTH_THRESHOLDS["warning"]:
        return "At Risk"
    elif score < HEALTH_THRESHOLDS["healthy"]:
        return "Moderate"
    else:
        return "Healthy"


def get_frustration_color(score: int) -> str:
    """Get color based on frustration score (0-10)."""
    if score >= 7:
        return COLORS["critical"]
    elif score >= 4:
        return COLORS["warning"]
    else:
        return COLORS["success"]


# Cache the logo at module load time using absolute path from this file's location
_LOGO_BASE64_CACHE: Optional[str] = None

def _find_logo_path() -> Optional[Path]:
    """Find the logo file using absolute path from this file's location."""
    # Use absolute path from this file - this is reliable regardless of cwd
    this_file = Path(__file__).resolve()
    project_root = this_file.parent.parent.parent  # src/dashboard/branding.py -> project root

    possible_paths = [
        project_root / "assets" / "truenas_logo.png",
        project_root / "assets" / "truenas-enterprise-logo.png",
        project_root / "context" / "branding" / "truenas-enterprise-logo.png",
    ]

    for path in possible_paths:
        if path.exists():
            return path
    return None

def load_logo_base64(logo_path: Optional[str] = None) -> Optional[str]:
    """Load logo as base64 for embedding in HTML."""
    global _LOGO_BASE64_CACHE

    # Return cached version if available
    if _LOGO_BASE64_CACHE is not None:
        return _LOGO_BASE64_CACHE

    if logo_path is None:
        found_path = _find_logo_path()
        if found_path:
            logo_path = str(found_path)

    if logo_path and Path(logo_path).exists():
        with open(logo_path, "rb") as f:
            _LOGO_BASE64_CACHE = base64.b64encode(f.read()).decode()
            return _LOGO_BASE64_CACHE
    return None

# Pre-load the logo at module import time
_LOGO_BASE64_CACHE = load_logo_base64()


def get_logo_html(height: int = 40) -> str:
    """Get HTML for logo display, with fallback to text."""
    logo_b64 = load_logo_base64()
    if logo_b64:
        return f'<img src="data:image/png;base64,{logo_b64}" height="{height}" alt="TrueNAS Enterprise">'
    else:
        # Text fallback with brand styling
        return f'''
        <span style="font-family: {FONTS["family"]}; font-weight: {FONTS["headline"]};
                     font-size: {height * 0.6}px; color: {COLORS["primary"]};">
            TrueNAS<span style="color: {COLORS["white"]};">Enterprise</span>
        </span>
        '''
