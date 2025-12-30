"""
Configuration management for TrueNAS Sentiment Analysis.
Loads settings from environment variables and .env file.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


# Load .env file from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    """Application configuration loaded from environment variables."""

    # Required
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Paths
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", PROJECT_ROOT / "outputs"))
    ASSETS_DIR: Path = PROJECT_ROOT / "assets"
    INPUT_DIR: Path = PROJECT_ROOT / "input"

    # Logo
    LOGO_PATH: Optional[Path] = ASSETS_DIR / "truenas_logo.png"

    # Claude model identifiers
    CLAUDE_HAIKU_MODEL: str = "claude-3-5-haiku-20241022"
    CLAUDE_SONNET_MODEL: str = "claude-sonnet-4-20250514"

    # API settings
    MAX_TOKENS_HAIKU: int = 4096
    MAX_TOKENS_SONNET: int = 8192

    # Analysis settings
    SONNET_SCORE_ALL_CASES: bool = True  # Score all cases with Sonnet, not just top N
    TOP_N_QUICK_SCORING: int = 25  # Fallback if not scoring all cases

    # Timeline generation - score threshold based
    TIMELINE_SCORE_THRESHOLD: int = 125  # Generate timeline for cases scoring >= this
    MAX_TIMELINE_CASES: int = 25  # Safety cap on timeline generation

    # Slack (placeholder for future)
    SLACK_WEBHOOK_URL: Optional[str] = os.getenv("SLACK_WEBHOOK_URL")
    SLACK_CHANNEL: Optional[str] = os.getenv("SLACK_CHANNEL", "#customer-escalations")
    ALERT_HEALTH_THRESHOLD: int = 60  # Alert if health score below this

    @classmethod
    def validate(cls) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is not set. Add it to .env file.")

        return errors

    @classmethod
    def ensure_directories(cls) -> None:
        """Create required directories if they don't exist."""
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        cls.INPUT_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_logo_path(cls) -> Optional[Path]:
        """Return logo path if file exists, None otherwise."""
        if cls.LOGO_PATH and cls.LOGO_PATH.exists():
            return cls.LOGO_PATH
        return None


# Version information
PART1_VERSION = "1.5.1"
PART1_MODIFIED = "2024-12-16"
PART2_VERSION = "1.10.0"
PART2_MODIFIED = "2024-12-16"
PART3_VERSION = "1.3.6"
PART3_MODIFIED = "2024-12-16"
PART4_VERSION = "1.8.0"
PART4_MODIFIED = "2024-12-16"
PART5_VERSION = "1.6.1"
PART5_MODIFIED = "2024-12-16"

# Local adaptation version
LOCAL_VERSION = "2.0.0"
LOCAL_MODIFIED = "2024-12-19"
