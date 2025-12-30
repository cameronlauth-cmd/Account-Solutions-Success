"""
Core utilities for Account Solutions Success.

Exports:
- Console output functions (print_*, streaming_output)
- Claude client (get_claude_client)
- Configuration (Config)
"""

from .console import (
    console,
    print_header,
    print_stage,
    print_progress,
    print_success,
    print_warning,
    print_error,
    print_metric,
    print_divider,
    print_case_progress,
    create_progress_bar,
    print_summary_table,
    print_health_score,
    StreamingOutput,
    streaming_output,
    StreamlitStreamingOutput,
)

from .claude_client import get_claude_client

from .config import Config

__all__ = [
    # Console
    "console",
    "print_header",
    "print_stage",
    "print_progress",
    "print_success",
    "print_warning",
    "print_error",
    "print_metric",
    "print_divider",
    "print_case_progress",
    "create_progress_bar",
    "print_summary_table",
    "print_health_score",
    "StreamingOutput",
    "streaming_output",
    "StreamlitStreamingOutput",
    # Claude
    "get_claude_client",
    # Config
    "Config",
]
