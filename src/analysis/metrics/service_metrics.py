"""
Service Team Metrics for Account Solutions Success.

Measures effectiveness of Professional Services team deployments vs self-deployments:
- Deployment success rates
- Time to deploy
- Post-deployment support needs
- Customer satisfaction signals

Key metric: Service Value-Add = Service Team Delta vs Self-Deploy
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from collections import defaultdict

from ...data.models import LinkedOrder
from ...data.data_linker import LinkedDataStore


@dataclass
class ServiceMetrics:
    """Metrics for service team or self-deploy category."""
    # Identity
    category: str = ""  # "Service Deploy" or "Self Deploy"

    # Volume
    total_deployments: int = 0
    unique_accounts: int = 0
    total_revenue: float = 0.0  # Deal value for these deployments

    # Deployment quality
    avg_deployment_score: float = 0.0
    deployment_success_rate: float = 0.0  # % scoring >70
    avg_deployment_days: float = 0.0

    # Post-deployment support
    total_support_cases: int = 0
    support_cases_per_deployment: float = 0.0
    avg_time_to_first_case_days: float = 0.0
    s1_cases: int = 0
    s2_cases: int = 0

    # Customer experience
    avg_frustration_score: float = 0.0
    escalation_count: int = 0
    deployment_related_issues: int = 0

    # Journey outcomes
    avg_journey_health: float = 0.0
    high_churn_risk_count: int = 0

    # Product distribution
    products_deployed: Dict[str, int] = field(default_factory=dict)


@dataclass
class ServiceComparison:
    """Comparison between Service Deploy and Self Deploy."""
    # Individual metrics
    service_metrics: ServiceMetrics = field(default_factory=ServiceMetrics)
    self_metrics: ServiceMetrics = field(default_factory=ServiceMetrics)

    # Deltas (positive = service is better)
    deployment_score_delta: float = 0.0
    success_rate_delta: float = 0.0
    support_intensity_delta: float = 0.0  # Negative = service has fewer cases
    frustration_delta: float = 0.0  # Negative = service has lower frustration
    journey_health_delta: float = 0.0

    # Summary
    service_value_add_score: float = 0.0  # 0-100, higher = service adds more value
    recommendation: str = ""


def calculate_service_metrics(
    data_store: LinkedDataStore,
    is_service_deploy: bool,
) -> ServiceMetrics:
    """
    Calculate metrics for service or self deployments.

    Args:
        data_store: LinkedDataStore with correlated data
        is_service_deploy: True for service deploys, False for self-deploys

    Returns:
        ServiceMetrics for the specified category
    """
    metrics = ServiceMetrics()
    metrics.category = "Service Deploy" if is_service_deploy else "Self Deploy"

    # Track data points
    accounts_seen = set()
    deployment_scores = []
    deployment_days = []
    frustration_scores = []
    journey_health_scores = []
    product_counts = defaultdict(int)
    time_to_first_case = []

    for order in data_store.orders:
        # Find deployments matching our category
        matching_deploys = [
            d for d in order.deployments
            if d.is_service_deploy == is_service_deploy
        ]

        if not matching_deploys:
            continue

        # Count this order
        accounts_seen.add(order.account_name)

        if order.opportunity:
            metrics.total_revenue += order.opportunity.amount

        # Process each matching deployment
        for dep in matching_deploys:
            metrics.total_deployments += 1
            deployment_days.append(dep.case_age_days)

            if dep.deployment_score is not None:
                deployment_scores.append(dep.deployment_score)

            product_counts[dep.product_series.value] += 1

        # Support cases for orders with matching deployments
        for case in order.support_cases:
            metrics.total_support_cases += 1

            if case.frustration_score is not None:
                frustration_scores.append(case.frustration_score)

            if case.severity.value == "S1":
                metrics.s1_cases += 1
            elif case.severity.value == "S2":
                metrics.s2_cases += 1

            if case.escalation_detected:
                metrics.escalation_count += 1

            if case.deployment_related:
                metrics.deployment_related_issues += 1

        # Journey health
        if order.is_fully_linked and order.journey_health_score is not None:
            journey_health_scores.append(order.journey_health_score)
            if order.churn_risk in ["Critical", "High"]:
                metrics.high_churn_risk_count += 1

    # Calculate aggregates
    metrics.unique_accounts = len(accounts_seen)
    metrics.products_deployed = dict(product_counts)

    if deployment_scores:
        metrics.avg_deployment_score = sum(deployment_scores) / len(deployment_scores)
        metrics.deployment_success_rate = (
            sum(1 for s in deployment_scores if s > 70) / len(deployment_scores) * 100
        )

    if deployment_days:
        metrics.avg_deployment_days = sum(deployment_days) / len(deployment_days)

    if metrics.total_deployments > 0:
        metrics.support_cases_per_deployment = (
            metrics.total_support_cases / metrics.total_deployments
        )

    if frustration_scores:
        metrics.avg_frustration_score = sum(frustration_scores) / len(frustration_scores)

    if journey_health_scores:
        metrics.avg_journey_health = sum(journey_health_scores) / len(journey_health_scores)

    return metrics


def compare_service_vs_self_deploy(
    data_store: LinkedDataStore,
) -> ServiceComparison:
    """
    Compare Service Deploy vs Self Deploy effectiveness.

    Returns:
        ServiceComparison with both metrics and deltas
    """
    comparison = ServiceComparison()

    # Calculate both sets of metrics
    comparison.service_metrics = calculate_service_metrics(data_store, is_service_deploy=True)
    comparison.self_metrics = calculate_service_metrics(data_store, is_service_deploy=False)

    service = comparison.service_metrics
    self_deploy = comparison.self_metrics

    # Calculate deltas (positive = service is better)
    comparison.deployment_score_delta = (
        service.avg_deployment_score - self_deploy.avg_deployment_score
    )

    comparison.success_rate_delta = (
        service.deployment_success_rate - self_deploy.deployment_success_rate
    )

    # For support intensity and frustration, lower is better
    # So we flip the sign: positive delta = service is better (fewer cases/lower frustration)
    comparison.support_intensity_delta = (
        self_deploy.support_cases_per_deployment - service.support_cases_per_deployment
    )

    comparison.frustration_delta = (
        self_deploy.avg_frustration_score - service.avg_frustration_score
    )

    comparison.journey_health_delta = (
        service.avg_journey_health - self_deploy.avg_journey_health
    )

    # Calculate Service Value-Add Score (0-100)
    # Weighted combination of deltas
    value_score = 50  # Start neutral

    # Deployment success (weight: 30)
    if comparison.success_rate_delta > 20:
        value_score += 15
    elif comparison.success_rate_delta > 10:
        value_score += 10
    elif comparison.success_rate_delta > 0:
        value_score += 5
    elif comparison.success_rate_delta < -10:
        value_score -= 10
    elif comparison.success_rate_delta < 0:
        value_score -= 5

    # Support intensity (weight: 25)
    if comparison.support_intensity_delta > 1.0:
        value_score += 12
    elif comparison.support_intensity_delta > 0.5:
        value_score += 8
    elif comparison.support_intensity_delta > 0:
        value_score += 4
    elif comparison.support_intensity_delta < -0.5:
        value_score -= 8
    elif comparison.support_intensity_delta < 0:
        value_score -= 4

    # Frustration (weight: 20)
    if comparison.frustration_delta > 2:
        value_score += 10
    elif comparison.frustration_delta > 1:
        value_score += 6
    elif comparison.frustration_delta > 0:
        value_score += 3
    elif comparison.frustration_delta < -1:
        value_score -= 6
    elif comparison.frustration_delta < 0:
        value_score -= 3

    # Journey health (weight: 25)
    if comparison.journey_health_delta > 15:
        value_score += 12
    elif comparison.journey_health_delta > 5:
        value_score += 8
    elif comparison.journey_health_delta > 0:
        value_score += 4
    elif comparison.journey_health_delta < -5:
        value_score -= 8
    elif comparison.journey_health_delta < 0:
        value_score -= 4

    comparison.service_value_add_score = max(0, min(100, value_score))

    # Generate recommendation
    if comparison.service_value_add_score >= 70:
        comparison.recommendation = (
            "Strong recommendation for Professional Services deployment. "
            "Service deploys show significantly better outcomes across metrics."
        )
    elif comparison.service_value_add_score >= 55:
        comparison.recommendation = (
            "Moderate preference for Professional Services. "
            "Service deploys show measurably better results, especially for complex deployments."
        )
    elif comparison.service_value_add_score >= 45:
        comparison.recommendation = (
            "Mixed results between Service and Self deploy. "
            "Consider customer technical capability when recommending."
        )
    elif comparison.service_value_add_score >= 30:
        comparison.recommendation = (
            "Self-deploy showing comparable or better results. "
            "May indicate strong customer base or opportunity for service improvement."
        )
    else:
        comparison.recommendation = (
            "Self-deploy significantly outperforming service deploys. "
            "Review service delivery processes for improvement opportunities."
        )

    return comparison


def get_service_comparison_table(
    comparison: ServiceComparison,
) -> List[Dict[str, Any]]:
    """
    Generate a comparison table for Service vs Self Deploy.

    Returns:
        List of dicts suitable for DataFrame creation
    """
    service = comparison.service_metrics
    self_deploy = comparison.self_metrics

    rows = [
        {
            "Metric": "Total Deployments",
            "Service Deploy": service.total_deployments,
            "Self Deploy": self_deploy.total_deployments,
            "Delta": service.total_deployments - self_deploy.total_deployments,
        },
        {
            "Metric": "Unique Accounts",
            "Service Deploy": service.unique_accounts,
            "Self Deploy": self_deploy.unique_accounts,
            "Delta": service.unique_accounts - self_deploy.unique_accounts,
        },
        {
            "Metric": "Total Revenue",
            "Service Deploy": f"${service.total_revenue:,.0f}",
            "Self Deploy": f"${self_deploy.total_revenue:,.0f}",
            "Delta": f"${service.total_revenue - self_deploy.total_revenue:,.0f}",
        },
        {
            "Metric": "Avg Deployment Score",
            "Service Deploy": f"{service.avg_deployment_score:.1f}",
            "Self Deploy": f"{self_deploy.avg_deployment_score:.1f}",
            "Delta": f"{comparison.deployment_score_delta:+.1f}",
        },
        {
            "Metric": "Deployment Success Rate",
            "Service Deploy": f"{service.deployment_success_rate:.1f}%",
            "Self Deploy": f"{self_deploy.deployment_success_rate:.1f}%",
            "Delta": f"{comparison.success_rate_delta:+.1f}%",
        },
        {
            "Metric": "Avg Deployment Days",
            "Service Deploy": f"{service.avg_deployment_days:.1f}",
            "Self Deploy": f"{self_deploy.avg_deployment_days:.1f}",
            "Delta": f"{service.avg_deployment_days - self_deploy.avg_deployment_days:+.1f}",
        },
        {
            "Metric": "Support Cases per Deploy",
            "Service Deploy": f"{service.support_cases_per_deployment:.2f}",
            "Self Deploy": f"{self_deploy.support_cases_per_deployment:.2f}",
            "Delta": f"{comparison.support_intensity_delta:+.2f}",
        },
        {
            "Metric": "Avg Frustration Score",
            "Service Deploy": f"{service.avg_frustration_score:.1f}",
            "Self Deploy": f"{self_deploy.avg_frustration_score:.1f}",
            "Delta": f"{comparison.frustration_delta:+.1f}",
        },
        {
            "Metric": "S1 Cases",
            "Service Deploy": service.s1_cases,
            "Self Deploy": self_deploy.s1_cases,
            "Delta": service.s1_cases - self_deploy.s1_cases,
        },
        {
            "Metric": "Escalations",
            "Service Deploy": service.escalation_count,
            "Self Deploy": self_deploy.escalation_count,
            "Delta": service.escalation_count - self_deploy.escalation_count,
        },
        {
            "Metric": "Avg Journey Health",
            "Service Deploy": f"{service.avg_journey_health:.0f}",
            "Self Deploy": f"{self_deploy.avg_journey_health:.0f}",
            "Delta": f"{comparison.journey_health_delta:+.1f}",
        },
        {
            "Metric": "High Churn Risk Count",
            "Service Deploy": service.high_churn_risk_count,
            "Self Deploy": self_deploy.high_churn_risk_count,
            "Delta": service.high_churn_risk_count - self_deploy.high_churn_risk_count,
        },
    ]

    return rows


def get_service_summary(comparison: ServiceComparison) -> Dict[str, Any]:
    """
    Generate a summary of service effectiveness.

    Returns:
        Dict with summary statistics and recommendation
    """
    return {
        "service_value_add_score": comparison.service_value_add_score,
        "recommendation": comparison.recommendation,
        "key_findings": {
            "deployment_success_delta": f"{comparison.success_rate_delta:+.1f}%",
            "support_intensity_delta": f"{comparison.support_intensity_delta:+.2f} cases/deploy",
            "frustration_delta": f"{comparison.frustration_delta:+.1f} points",
            "journey_health_delta": f"{comparison.journey_health_delta:+.1f} points",
        },
        "service_deploy_count": comparison.service_metrics.total_deployments,
        "self_deploy_count": comparison.self_metrics.total_deployments,
        "service_accounts": comparison.service_metrics.unique_accounts,
        "self_accounts": comparison.self_metrics.unique_accounts,
    }
