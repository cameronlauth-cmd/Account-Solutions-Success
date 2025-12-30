"""
Slack integration for TrueNAS Sentiment Analysis.
Posts alerts to Slack webhook when critical issues are detected.

This is a placeholder - full implementation pending.
"""

import json
from typing import Optional

import requests

from ..core import Config


def post_slack_alert(
    customer_name: str,
    health_score: float,
    critical_cases: int,
    webhook_url: Optional[str] = None,
    channel: Optional[str] = None,
) -> bool:
    """
    Post an alert to Slack if health score is critical or there are critical cases.

    Args:
        customer_name: Customer account name
        health_score: Account health score (0-100)
        critical_cases: Number of cases with criticality >= 180
        webhook_url: Slack webhook URL (default: from config)
        channel: Slack channel (default: from config)

    Returns:
        True if alert was posted successfully, False otherwise
    """
    webhook = webhook_url or Config.SLACK_WEBHOOK_URL

    if not webhook:
        # Slack not configured, skip silently
        return False

    # Determine if alert is needed
    if health_score >= Config.ALERT_HEALTH_THRESHOLD and critical_cases == 0:
        return False  # No alert needed

    # Determine alert color based on severity
    if health_score < 60:
        color = "danger"  # Red
        status = "CRITICAL"
    elif critical_cases > 0:
        color = "warning"  # Yellow
        status = "WARNING"
    else:
        color = "good"  # Green
        status = "INFO"

    # Build message
    message = {
        "channel": channel or Config.SLACK_CHANNEL,
        "username": "TrueNAS Sentiment Bot",
        "icon_emoji": ":chart_with_upwards_trend:",
        "attachments": [
            {
                "color": color,
                "title": f"{status}: Customer Health Alert",
                "fields": [
                    {
                        "title": "Customer",
                        "value": customer_name,
                        "short": True
                    },
                    {
                        "title": "Health Score",
                        "value": f"{health_score:.0f}/100",
                        "short": True
                    },
                    {
                        "title": "Critical Cases",
                        "value": str(critical_cases),
                        "short": True
                    },
                ],
                "footer": "TrueNAS Sentiment Analysis",
            }
        ]
    }

    try:
        response = requests.post(
            webhook,
            json=message,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to post Slack alert: {e}")
        return False
