"""
Integrations module for TrueNAS Sentiment Analysis.
Contains Slack and other external service integrations.
"""

from .slack import post_slack_alert

__all__ = ['post_slack_alert']
