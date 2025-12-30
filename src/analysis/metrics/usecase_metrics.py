"""
Use Case Metrics for Account Solutions Success.

Aggregates metrics by customer use case/workload type:
- Media & Entertainment
- Backup & Archive
- Virtualization
- Database
- File Sharing
- Video Surveillance
- Scientific/HPC
- General Purpose

Provides insights into:
- Which products perform best for each use case
- Common issues by workload
- Use case-specific recommendations
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from collections import defaultdict

from ...data.models import LinkedOrder
from ...data.data_linker import LinkedDataStore


# Standard use case categories
USE_CASE_CATEGORIES = [
    "Media & Entertainment",
    "Backup & Archive",
    "Virtualization",
    "Database",
    "File Sharing",
    "Video Surveillance",
    "Scientific/HPC",
    "General Purpose",
    "Unknown",
]


@dataclass
class UseCaseMetrics:
    """Aggregated metrics for a use case category."""
    # Identity
    use_case: str = ""

    # Volume
    total_orders: int = 0
    total_revenue: float = 0.0
    unique_accounts: int = 0

    # Product distribution
    products_deployed: Dict[str, int] = field(default_factory=dict)  # product -> count
    best_performing_product: str = ""
    worst_performing_product: str = ""

    # Deployment metrics
    total_deployments: int = 0
    avg_deployment_score: float = 0.0
    deployment_success_rate: float = 0.0
    service_deploy_rate: float = 0.0

    # Support metrics
    total_support_cases: int = 0
    support_intensity: float = 0.0  # cases per deployment
    avg_frustration_score: float = 0.0
    s1_case_count: int = 0
    escalation_rate: float = 0.0

    # Common issues for this use case
    top_issues: List[str] = field(default_factory=list)
    issue_distribution: Dict[str, int] = field(default_factory=dict)

    # Performance by product for this use case
    product_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Journey health
    avg_journey_health: float = 0.0
    high_churn_risk_count: int = 0

    # Recommendations
    recommended_products: List[str] = field(default_factory=list)
    common_pain_points: List[str] = field(default_factory=list)


def _categorize_use_case(use_case_text: str) -> str:
    """Map use case text to standard category."""
    if not use_case_text:
        return "Unknown"

    text_lower = use_case_text.lower()

    if any(kw in text_lower for kw in ["media", "video edit", "broadcast", "post-production", "4k", "8k"]):
        return "Media & Entertainment"
    elif any(kw in text_lower for kw in ["backup", "archive", "dr", "disaster", "retention", "cold storage"]):
        return "Backup & Archive"
    elif any(kw in text_lower for kw in ["vm", "virtual", "vdi", "esxi", "hyper-v", "container", "docker", "kubernetes"]):
        return "Virtualization"
    elif any(kw in text_lower for kw in ["database", "sql", "oracle", "mysql", "postgres", "analytics", "olap", "oltp"]):
        return "Database"
    elif any(kw in text_lower for kw in ["file", "share", "nas", "smb", "nfs", "cifs", "collab", "home director"]):
        return "File Sharing"
    elif any(kw in text_lower for kw in ["surveil", "camera", "nvr", "security", "cctv"]):
        return "Video Surveillance"
    elif any(kw in text_lower for kw in ["hpc", "research", "scientific", "render", "simulation", "compute"]):
        return "Scientific/HPC"
    else:
        return "General Purpose"


def calculate_usecase_metrics(
    data_store: LinkedDataStore,
    use_case: str,
) -> UseCaseMetrics:
    """
    Calculate aggregated metrics for a specific use case.

    Args:
        data_store: LinkedDataStore with correlated data
        use_case: Use case category name

    Returns:
        UseCaseMetrics with aggregated data
    """
    metrics = UseCaseMetrics()
    metrics.use_case = use_case

    # Track data points
    accounts_seen = set()
    deployment_scores_by_product = defaultdict(list)
    deployment_scores = []
    frustration_scores = []
    journey_health_scores = []
    product_counts = defaultdict(int)
    issue_counts = defaultdict(int)
    pain_points = []

    # Find orders matching this use case
    for order in data_store.orders:
        # Determine use case for this order
        order_use_case = "Unknown"

        if order.opportunity:
            order_use_case = _categorize_use_case(order.opportunity.primary_use_case or "")

            # Also check extracted use case if available
            if order_use_case == "Unknown" and order.opportunity.business_need:
                order_use_case = _categorize_use_case(order.opportunity.business_need)

        if order_use_case != use_case:
            continue

        # Match found - collect metrics
        metrics.total_orders += 1
        accounts_seen.add(order.account_name)

        if order.opportunity:
            metrics.total_revenue += order.opportunity.amount
            if order.opportunity.primary_product:
                product_counts[order.opportunity.primary_product] += 1
            if order.opportunity.pain_points:
                pain_points.append(order.opportunity.pain_points)

        # Deployment metrics
        service_count = 0
        for dep in order.deployments:
            metrics.total_deployments += 1
            product_series = dep.product_series.value

            if dep.is_service_deploy:
                service_count += 1

            if dep.deployment_score is not None:
                deployment_scores.append(dep.deployment_score)
                deployment_scores_by_product[product_series].append(dep.deployment_score)

        # Support case metrics
        for case in order.support_cases:
            metrics.total_support_cases += 1

            if case.frustration_score is not None:
                frustration_scores.append(case.frustration_score)

            if case.severity.value == "S1":
                metrics.s1_case_count += 1

            if case.case_reason:
                issue_counts[case.case_reason] += 1

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

    if metrics.total_deployments > 0:
        metrics.service_deploy_rate = (service_count / metrics.total_deployments) * 100
        metrics.support_intensity = metrics.total_support_cases / metrics.total_deployments

    if frustration_scores:
        metrics.avg_frustration_score = sum(frustration_scores) / len(frustration_scores)

    if journey_health_scores:
        metrics.avg_journey_health = sum(journey_health_scores) / len(journey_health_scores)

    # Calculate escalation rate
    if metrics.total_support_cases > 0:
        escalation_count = sum(
            1 for order in data_store.orders
            for case in order.support_cases
            if case.escalation_detected
        )
        metrics.escalation_rate = (escalation_count / metrics.total_support_cases) * 100

    # Product performance for this use case
    for product, scores in deployment_scores_by_product.items():
        if scores:
            avg_score = sum(scores) / len(scores)
            success_rate = sum(1 for s in scores if s > 70) / len(scores) * 100
            metrics.product_performance[product] = {
                "avg_deployment_score": avg_score,
                "success_rate": success_rate,
                "deployment_count": len(scores),
            }

    # Determine best/worst performing products
    if metrics.product_performance:
        sorted_products = sorted(
            metrics.product_performance.items(),
            key=lambda x: x[1]["avg_deployment_score"],
            reverse=True
        )
        metrics.best_performing_product = sorted_products[0][0] if sorted_products else ""
        metrics.worst_performing_product = sorted_products[-1][0] if len(sorted_products) > 1 else ""

    # Top issues
    sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
    metrics.top_issues = [issue for issue, _ in sorted_issues[:5]]
    metrics.issue_distribution = dict(sorted_issues[:10])

    # Common pain points
    if pain_points:
        metrics.common_pain_points = list(set(pain_points))[:5]

    # Recommended products (highest success rate with enough data)
    qualified_products = [
        (prod, data) for prod, data in metrics.product_performance.items()
        if data["deployment_count"] >= 2
    ]
    if qualified_products:
        sorted_by_success = sorted(
            qualified_products,
            key=lambda x: x[1]["success_rate"],
            reverse=True
        )
        metrics.recommended_products = [p[0] for p in sorted_by_success[:3]]

    return metrics


def calculate_all_usecase_metrics(
    data_store: LinkedDataStore,
) -> Dict[str, UseCaseMetrics]:
    """
    Calculate metrics for all use case categories.

    Returns:
        Dict mapping use case name to UseCaseMetrics
    """
    results = {}

    for use_case in USE_CASE_CATEGORIES:
        metrics = calculate_usecase_metrics(data_store, use_case)
        if metrics.total_orders > 0:
            results[use_case] = metrics

    return results


def get_usecase_comparison_table(
    all_metrics: Dict[str, UseCaseMetrics],
) -> List[Dict[str, Any]]:
    """
    Generate a comparison table across all use cases.

    Returns:
        List of dicts suitable for DataFrame creation
    """
    rows = []

    for use_case, metrics in all_metrics.items():
        rows.append({
            "Use Case": use_case,
            "Orders": metrics.total_orders,
            "Revenue": f"${metrics.total_revenue:,.0f}",
            "Accounts": metrics.unique_accounts,
            "Deployments": metrics.total_deployments,
            "Deploy Success %": f"{metrics.deployment_success_rate:.1f}%",
            "Support Cases": metrics.total_support_cases,
            "Support Intensity": f"{metrics.support_intensity:.2f}",
            "Avg Frustration": f"{metrics.avg_frustration_score:.1f}",
            "Best Product": metrics.best_performing_product,
            "Journey Health": f"{metrics.avg_journey_health:.0f}",
        })

    # Sort by order count
    rows.sort(key=lambda x: x["Orders"], reverse=True)

    return rows


def get_product_usecase_matrix(
    data_store: LinkedDataStore,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Generate a matrix showing product performance by use case.

    Returns:
        Nested dict: use_case -> product -> metrics
    """
    all_metrics = calculate_all_usecase_metrics(data_store)

    matrix = {}
    for use_case, metrics in all_metrics.items():
        if metrics.product_performance:
            matrix[use_case] = metrics.product_performance

    return matrix
