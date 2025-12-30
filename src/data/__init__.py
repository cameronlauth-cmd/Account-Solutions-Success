"""
Data loading and linking package for Account Solutions Success.

This package handles:
- Loading data from Excel exports (Opportunities, Deployments, Support Cases)
- Data models (dataclasses) for each entity type
- Linking data across sources via Order Number
"""

from .models import (
    Opportunity,
    Deployment,
    SupportCase,
    LinkedOrder,
    LinkSummary,
    Severity,
    SupportLevel,
    ProductSeries,
)
from .opportunity_loader import load_opportunities
from .deployment_loader import load_deployments
from .case_loader import load_support_cases
from .data_linker import link_data_sources, LinkedDataStore, load_and_link_all_sources

__all__ = [
    # Models
    "Opportunity",
    "Deployment",
    "SupportCase",
    "LinkedOrder",
    "LinkSummary",
    "Severity",
    "SupportLevel",
    "ProductSeries",
    # Loaders
    "load_opportunities",
    "load_deployments",
    "load_support_cases",
    # Linker
    "link_data_sources",
    "LinkedDataStore",
    "load_and_link_all_sources",
]
