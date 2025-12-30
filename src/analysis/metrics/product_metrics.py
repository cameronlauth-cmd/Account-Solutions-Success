"""
Product Metrics for Account Solutions Success.

Aggregates metrics across all customers for a specific product series:
- F-Series, M-Series, H-Series, R-Series

Provides product-level view of:
- Sales volume and revenue
- Deployment success rates
- Support intensity (cases per unit)
- Field failure rates
- Common issues by product
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from collections import defaultdict

from ...data.models import ProductSeries, LinkedOrder
from ...data.data_linker import LinkedDataStore


@dataclass
class ProductMetrics:
    """Aggregated metrics for a product series."""
    # Identity
    product_series: str = ""  # F-Series, M-Series, etc.

    # Sales metrics (from Opportunities)
    units_sold: int = 0
    total_revenue: float = 0.0
    avg_deal_size: float = 0.0

    # Deployment metrics
    units_deployed: int = 0
    deployment_success_rate: float = 0.0  # % scoring >70
    avg_deployment_score: float = 0.0
    avg_deployment_days: float = 0.0
    service_deploy_count: int = 0
    self_deploy_count: int = 0

    # Support metrics
    total_support_cases: int = 0
    support_intensity: float = 0.0  # cases per deployed unit
    avg_case_age_days: float = 0.0
    avg_frustration_score: float = 0.0
    s1_case_count: int = 0
    s2_case_count: int = 0
    escalation_count: int = 0
    repeat_issue_rate: float = 0.0  # % that are repeats

    # Field performance
    hardware_failure_count: int = 0
    hardware_failure_rate: float = 0.0  # failures per unit
    performance_issue_count: int = 0
    configuration_issue_count: int = 0

    # Issue distribution
    issue_categories: Dict[str, int] = field(default_factory=dict)
    top_issues: List[str] = field(default_factory=list)

    # Journey health (from fully linked orders)
    fully_linked_orders: int = 0
    avg_journey_health: float = 0.0
    high_churn_risk_count: int = 0  # Critical or High risk

    # Account distribution
    unique_accounts: int = 0
    accounts: List[str] = field(default_factory=list)


def calculate_product_metrics(
    data_store: LinkedDataStore,
    product_series: str,
    include_analysis: bool = True,
) -> ProductMetrics:
    """
    Calculate aggregated metrics for a specific product series.

    Args:
        data_store: LinkedDataStore with correlated data
        product_series: Product series name (e.g., "F-Series", "M")
        include_analysis: If True, include AI analysis results

    Returns:
        ProductMetrics with aggregated data
    """
    metrics = ProductMetrics()

    # Normalize product series name
    series_normalized = product_series.upper().replace("-SERIES", "").replace("SERIES", "").strip()
    metrics.product_series = f"{series_normalized}-Series"

    # Track unique accounts
    accounts_seen = set()

    # Collect orders for this product
    matching_orders = []

    for order in data_store.orders:
        # Check if any linked data matches this product series
        matches = False

        # Check opportunity
        if order.opportunity:
            opp_product = (order.opportunity.primary_product or "").upper()
            if series_normalized in opp_product:
                matches = True

        # Check deployments
        for dep in order.deployments:
            if dep.product_series.value.upper() == series_normalized:
                matches = True
                break

        # Check support cases
        for case in order.support_cases:
            if case.product_series.value.upper() == series_normalized:
                matches = True
                break

        if matches:
            matching_orders.append(order)
            accounts_seen.add(order.account_name)

    # Calculate metrics from matching orders
    deployment_scores = []
    deployment_days = []
    case_ages = []
    frustration_scores = []
    journey_health_scores = []

    for order in matching_orders:
        # Opportunity metrics
        if order.opportunity:
            metrics.units_sold += 1
            metrics.total_revenue += order.opportunity.amount

        # Deployment metrics
        for dep in order.deployments:
            if dep.product_series.value.upper() == series_normalized:
                metrics.units_deployed += 1
                deployment_days.append(dep.case_age_days)

                if dep.is_service_deploy:
                    metrics.service_deploy_count += 1
                else:
                    metrics.self_deploy_count += 1

                if dep.deployment_score is not None:
                    deployment_scores.append(dep.deployment_score)

        # Support case metrics
        for case in order.support_cases:
            if case.product_series.value.upper() == series_normalized:
                metrics.total_support_cases += 1
                case_ages.append(case.case_age_days)

                if case.frustration_score is not None:
                    frustration_scores.append(case.frustration_score)

                # Severity counts
                if case.severity.value == "S1":
                    metrics.s1_case_count += 1
                elif case.severity.value == "S2":
                    metrics.s2_case_count += 1

                # Issue detection
                if case.is_hardware_failure:
                    metrics.hardware_failure_count += 1
                if case.is_performance_issue:
                    metrics.performance_issue_count += 1
                if case.is_configuration_issue:
                    metrics.configuration_issue_count += 1
                if case.is_repeat_issue:
                    metrics.repeat_issue_rate += 1  # Will convert to rate later
                if case.escalation_detected:
                    metrics.escalation_count += 1

                # Issue categories
                reason = case.case_reason or "Unknown"
                metrics.issue_categories[reason] = metrics.issue_categories.get(reason, 0) + 1

        # Journey health from fully linked orders
        if order.is_fully_linked:
            metrics.fully_linked_orders += 1
            if order.journey_health_score is not None:
                journey_health_scores.append(order.journey_health_score)
            if order.churn_risk in ["Critical", "High"]:
                metrics.high_churn_risk_count += 1

    # Calculate averages and rates
    if metrics.units_sold > 0:
        metrics.avg_deal_size = metrics.total_revenue / metrics.units_sold

    if deployment_scores:
        metrics.avg_deployment_score = sum(deployment_scores) / len(deployment_scores)
        metrics.deployment_success_rate = (
            sum(1 for s in deployment_scores if s > 70) / len(deployment_scores) * 100
        )

    if deployment_days:
        metrics.avg_deployment_days = sum(deployment_days) / len(deployment_days)

    if case_ages:
        metrics.avg_case_age_days = sum(case_ages) / len(case_ages)

    if frustration_scores:
        metrics.avg_frustration_score = sum(frustration_scores) / len(frustration_scores)

    if metrics.units_deployed > 0:
        metrics.support_intensity = metrics.total_support_cases / metrics.units_deployed
        metrics.hardware_failure_rate = metrics.hardware_failure_count / metrics.units_deployed

    if metrics.total_support_cases > 0:
        # Convert repeat count to rate
        metrics.repeat_issue_rate = (metrics.repeat_issue_rate / metrics.total_support_cases) * 100

    if journey_health_scores:
        metrics.avg_journey_health = sum(journey_health_scores) / len(journey_health_scores)

    # Top issues
    sorted_issues = sorted(
        metrics.issue_categories.items(),
        key=lambda x: x[1],
        reverse=True
    )
    metrics.top_issues = [issue for issue, _ in sorted_issues[:5]]

    # Account info
    metrics.unique_accounts = len(accounts_seen)
    metrics.accounts = sorted(accounts_seen)[:20]  # Top 20

    return metrics


def calculate_all_product_metrics(
    data_store: LinkedDataStore,
    include_analysis: bool = True,
) -> Dict[str, ProductMetrics]:
    """
    Calculate metrics for all product series.

    Args:
        data_store: LinkedDataStore with correlated data
        include_analysis: If True, include AI analysis results

    Returns:
        Dict mapping product series name to ProductMetrics
    """
    series_list = ["F", "M", "H", "R"]

    results = {}
    for series in series_list:
        metrics = calculate_product_metrics(data_store, series, include_analysis)
        if metrics.units_sold > 0 or metrics.units_deployed > 0 or metrics.total_support_cases > 0:
            results[metrics.product_series] = metrics

    return results


def get_product_comparison_table(
    all_metrics: Dict[str, ProductMetrics]
) -> List[Dict[str, Any]]:
    """
    Generate a comparison table across all products.

    Returns:
        List of dicts suitable for DataFrame creation
    """
    rows = []

    for series_name, metrics in all_metrics.items():
        rows.append({
            "Product": series_name,
            "Units Sold": metrics.units_sold,
            "Revenue": f"${metrics.total_revenue:,.0f}",
            "Units Deployed": metrics.units_deployed,
            "Deploy Success %": f"{metrics.deployment_success_rate:.1f}%",
            "Support Cases": metrics.total_support_cases,
            "Support Intensity": f"{metrics.support_intensity:.2f}",
            "Avg Frustration": f"{metrics.avg_frustration_score:.1f}",
            "Hardware Failures": metrics.hardware_failure_count,
            "S1 Cases": metrics.s1_case_count,
            "Repeat Rate %": f"{metrics.repeat_issue_rate:.1f}%",
            "Journey Health": f"{metrics.avg_journey_health:.0f}",
            "High Risk Orders": metrics.high_churn_risk_count,
        })

    return rows
