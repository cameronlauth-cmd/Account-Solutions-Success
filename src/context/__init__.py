"""
Context loading module for TrueNAS Sentiment Analysis.
Handles loading and composing context from PDFs and configuration files.
"""

from .loader import (
    ContextLoader,
    load_context_for_case,
    load_global_context,
    get_product_line_from_serial,
    get_product_line_from_series,
    get_product_line_from_model,
)

__all__ = [
    'ContextLoader',
    'load_context_for_case',
    'load_global_context',
    'get_product_line_from_serial',
    'get_product_line_from_series',
    'get_product_line_from_model',
]
