"""
Data models for Account Solutions Success.

Dataclass definitions for:
- Opportunity: Salesforce opportunity/deal data
- Deployment: Deployment case data (Professional Services)
- SupportCase: Support case messages
- LinkedOrder: Order-linked bundle of all three sources
- LinkSummary: Statistics about data correlation
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class Severity(Enum):
    """Case severity levels."""
    S1 = "S1"  # Critical - system down
    S2 = "S2"  # High - major impact
    S3 = "S3"  # Medium - moderate impact
    S4 = "S4"  # Low - minor impact


class SupportLevel(Enum):
    """Customer support tier."""
    GOLD = "Gold"
    SILVER = "Silver"
    BRONZE = "Bronze"
    UNKNOWN = "Unknown"


class ProductSeries(Enum):
    """TrueNAS product series."""
    F_SERIES = "F"  # Flash-based
    M_SERIES = "M"  # Midrange
    H_SERIES = "H"  # Hybrid
    R_SERIES = "R"  # Rack-mount
    UNKNOWN = "Unknown"


@dataclass
class Opportunity:
    """
    Salesforce Opportunity record.

    Represents a sales deal/order with customer expectations.
    """
    # Identifiers
    order_number: str
    opportunity_name: str
    account_name: str

    # Sales info
    opportunity_owner: str = ""
    owner_role: str = ""
    fiscal_period: str = ""
    lead_source: str = ""
    deal_type: str = ""

    # Financials
    amount: float = 0.0

    # Dates
    close_date: Optional[datetime] = None
    created_date: Optional[datetime] = None

    # Products
    products_quoted: str = ""
    primary_product: str = ""
    system_model: str = ""

    # Customer context (key fields for analysis)
    business_need: str = ""
    primary_use_case: str = ""
    pain_points: str = ""
    next_step: str = ""

    # Derived fields (populated during analysis)
    product_series: ProductSeries = ProductSeries.UNKNOWN

    def __post_init__(self):
        """Derive product series from primary product."""
        if self.primary_product:
            product_upper = str(self.primary_product).upper()
            if product_upper.startswith("F"):
                self.product_series = ProductSeries.F_SERIES
            elif product_upper.startswith("M"):
                self.product_series = ProductSeries.M_SERIES
            elif product_upper.startswith("H"):
                self.product_series = ProductSeries.H_SERIES
            elif product_upper.startswith("R"):
                self.product_series = ProductSeries.R_SERIES


@dataclass
class Deployment:
    """
    Deployment case record.

    Represents a Professional Services deployment case,
    tracking the installation/setup of a system.
    """
    # Identifiers
    case_number: str
    order_number: str
    account_name: str
    serial_number: str = ""

    # Assignment
    case_owner: str = ""

    # Timing
    case_age_days: int = 0
    message_date: Optional[datetime] = None

    # Classification
    severity: Severity = Severity.S4
    case_reason: str = ""
    status: str = ""

    # Product info
    product_series: ProductSeries = ProductSeries.UNKNOWN
    product_model: str = ""

    # Support tier
    support_level: SupportLevel = SupportLevel.UNKNOWN

    # Content (deployment notes/communication)
    messages: List[str] = field(default_factory=list)
    from_addresses: List[str] = field(default_factory=list)

    # Deployment-specific flags (derived during analysis)
    is_service_deploy: bool = False  # vs self-deploy
    deployment_score: int = 0  # 0-100


@dataclass
class SupportCase:
    """
    Support case record.

    Represents a customer support case with message history.
    """
    # Identifiers
    case_number: str
    order_number: str
    account_name: str
    serial_number: str = ""

    # Assignment
    case_owner: str = ""

    # Timing
    case_age_days: int = 0
    message_date: Optional[datetime] = None
    created_date: Optional[datetime] = None

    # Classification
    severity: Severity = Severity.S4
    case_reason: str = ""
    status: str = ""

    # Product info
    product_series: ProductSeries = ProductSeries.UNKNOWN
    product_model: str = ""

    # Support tier
    support_level: SupportLevel = SupportLevel.UNKNOWN

    # Content
    messages: List[str] = field(default_factory=list)
    from_addresses: List[str] = field(default_factory=list)

    # Analysis results (populated later by analysis layers)
    is_repeat_issue: bool = False
    repeat_of_case: Optional[str] = None
    criticality_score: int = 0
    frustration_score: float = 0.0

    # Issue classification (populated by support_layer)
    is_hardware_failure: bool = False
    is_performance_issue: bool = False
    is_configuration_issue: bool = False
    escalation_detected: bool = False
    deployment_related: Optional[bool] = None  # If linked to deployment issues


@dataclass
class LinkedOrder:
    """
    Order-linked bundle of Opportunity, Deployments, and Support Cases.

    Represents the full customer journey for a single order:
    Sale -> Deployment -> Support
    """
    order_number: str
    account_name: str

    # Linked records (may be None if not found)
    opportunity: Optional[Opportunity] = None
    deployments: List[Deployment] = field(default_factory=list)
    support_cases: List[SupportCase] = field(default_factory=list)

    # Cross-layer analysis results (populated by evaluation layer)
    journey_health_score: int = 0  # 0-100
    expectation_match: Optional[str] = None  # How well deployment matched expectations
    churn_risk: str = "Unknown"  # Low/Medium/High/Critical

    # Insights from evaluation layer
    critical_findings: List[str] = field(default_factory=list)
    positive_signals: List[str] = field(default_factory=list)
    immediate_actions: List[str] = field(default_factory=list)

    @property
    def has_opportunity(self) -> bool:
        return self.opportunity is not None

    @property
    def has_deployments(self) -> bool:
        return len(self.deployments) > 0

    @property
    def has_support_cases(self) -> bool:
        return len(self.support_cases) > 0

    @property
    def is_fully_linked(self) -> bool:
        """Returns True if order has data from all three sources."""
        return self.has_opportunity and self.has_deployments and self.has_support_cases

    @property
    def total_support_cases(self) -> int:
        return len(self.support_cases)

    @property
    def total_deployments(self) -> int:
        return len(self.deployments)


@dataclass
class LinkSummary:
    """
    Summary statistics about data linking results.
    """
    # Counts
    total_orders: int = 0
    orders_with_opportunity: int = 0
    orders_with_deployment: int = 0
    orders_with_support: int = 0
    fully_linked_orders: int = 0

    # Orphan counts (records with no order number match)
    orphan_opportunities: int = 0
    orphan_deployments: int = 0
    orphan_cases: int = 0

    # Source totals
    total_opportunities: int = 0
    total_deployments: int = 0
    total_cases: int = 0

    def summary(self) -> str:
        """Generate human-readable summary report."""
        lines = [
            "=" * 50,
            "DATA LINKING SUMMARY",
            "=" * 50,
            "",
            "Orders:",
            f"  Total Orders: {self.total_orders}",
            f"  With Opportunity: {self.orders_with_opportunity} ({self._pct(self.orders_with_opportunity, self.total_orders)})",
            f"  With Deployment: {self.orders_with_deployment} ({self._pct(self.orders_with_deployment, self.total_orders)})",
            f"  With Support Cases: {self.orders_with_support} ({self._pct(self.orders_with_support, self.total_orders)})",
            f"  Fully Linked (all 3): {self.fully_linked_orders} ({self._pct(self.fully_linked_orders, self.total_orders)})",
            "",
            "Source Records:",
            f"  Opportunities: {self.total_opportunities} (orphans: {self.orphan_opportunities})",
            f"  Deployments: {self.total_deployments} (orphans: {self.orphan_deployments})",
            f"  Support Cases: {self.total_cases} (orphans: {self.orphan_cases})",
            "=" * 50,
        ]
        return "\n".join(lines)

    def _pct(self, num: int, denom: int) -> str:
        if denom == 0:
            return "0%"
        return f"{(num / denom * 100):.0f}%"
