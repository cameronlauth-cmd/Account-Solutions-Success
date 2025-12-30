"""
Account Metrics for Account Solutions Success.

Aggregates metrics for a specific customer account across all their:
- Opportunities (purchases)
- Deployments
- Support cases

Provides account-level view of:
- Total spend and purchase history
- Deployment success
- Support health
- Journey health score
- Churn risk assessment
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

from ...data.models import LinkedOrder
from ...data.data_linker import LinkedDataStore


@dataclass
class AccountMetrics:
    """Aggregated metrics for a customer account."""
    # Identity
    account_name: str = ""

    # Purchase metrics (from Opportunities)
    total_orders: int = 0
    total_spend: float = 0.0
    avg_order_size: float = 0.0
    products_purchased: List[str] = field(default_factory=list)
    first_purchase_date: Optional[datetime] = None
    last_purchase_date: Optional[datetime] = None
    customer_tenure_days: int = 0

    # Deployment metrics
    total_deployments: int = 0
    successful_deployments: int = 0  # score > 70
    deployment_success_rate: float = 0.0
    avg_deployment_score: float = 0.0
    service_deploys: int = 0
    self_deploys: int = 0
    avg_deployment_days: float = 0.0

    # Support metrics
    total_support_cases: int = 0
    open_cases: int = 0
    s1_cases: int = 0
    s2_cases: int = 0
    avg_case_age_days: float = 0.0
    avg_frustration_score: float = 0.0
    max_frustration_score: float = 0.0
    escalation_count: int = 0
    repeat_issues: int = 0

    # Issue breakdown
    hardware_failures: int = 0
    performance_issues: int = 0
    configuration_issues: int = 0
    issue_categories: Dict[str, int] = field(default_factory=dict)

    # Health scores
    account_health_score: float = 0.0  # 0-100, higher = healthier
    journey_health_avg: float = 0.0  # Avg across orders
    churn_risk: str = "Unknown"  # Low, Medium, High, Critical
    high_risk_order_count: int = 0

    # Cross-layer insights
    fully_linked_orders: int = 0
    expectations_met_rate: float = 0.0
    deployment_related_issues: int = 0

    # Key indicators
    critical_findings: List[str] = field(default_factory=list)
    positive_signals: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)


def calculate_account_metrics(
    data_store: LinkedDataStore,
    account_name: str,
) -> AccountMetrics:
    """
    Calculate aggregated metrics for a specific account.

    Args:
        data_store: LinkedDataStore with correlated data
        account_name: Name of the account to analyze

    Returns:
        AccountMetrics with aggregated data
    """
    metrics = AccountMetrics()
    metrics.account_name = account_name

    # Get all orders for this account
    orders = data_store.get_orders_by_account(account_name)

    if not orders:
        return metrics

    # Collect data points
    deployment_scores = []
    deployment_days = []
    case_ages = []
    frustration_scores = []
    journey_health_scores = []
    products_seen = set()
    purchase_dates = []

    for order in orders:
        metrics.total_orders += 1

        # Opportunity metrics
        if order.opportunity:
            metrics.total_spend += order.opportunity.amount
            if order.opportunity.primary_product:
                products_seen.add(order.opportunity.primary_product)
            if order.opportunity.close_date:
                purchase_dates.append(order.opportunity.close_date)

        # Deployment metrics
        for dep in order.deployments:
            metrics.total_deployments += 1
            deployment_days.append(dep.case_age_days)

            if dep.is_service_deploy:
                metrics.service_deploys += 1
            else:
                metrics.self_deploys += 1

            if dep.deployment_score is not None:
                deployment_scores.append(dep.deployment_score)
                if dep.deployment_score > 70:
                    metrics.successful_deployments += 1

        # Support case metrics
        for case in order.support_cases:
            metrics.total_support_cases += 1
            case_ages.append(case.case_age_days)

            if case.status and "open" in case.status.lower():
                metrics.open_cases += 1

            if case.severity.value == "S1":
                metrics.s1_cases += 1
            elif case.severity.value == "S2":
                metrics.s2_cases += 1

            if case.frustration_score is not None:
                frustration_scores.append(case.frustration_score)

            if case.escalation_detected:
                metrics.escalation_count += 1
            if case.is_repeat_issue:
                metrics.repeat_issues += 1
            if case.is_hardware_failure:
                metrics.hardware_failures += 1
            if case.is_performance_issue:
                metrics.performance_issues += 1
            if case.is_configuration_issue:
                metrics.configuration_issues += 1
            if case.deployment_related:
                metrics.deployment_related_issues += 1

            # Issue categories
            reason = case.case_reason or "Unknown"
            metrics.issue_categories[reason] = metrics.issue_categories.get(reason, 0) + 1

        # Journey health from fully linked orders
        if order.is_fully_linked:
            metrics.fully_linked_orders += 1
            if order.journey_health_score is not None:
                journey_health_scores.append(order.journey_health_score)
            if order.churn_risk in ["Critical", "High"]:
                metrics.high_risk_order_count += 1

            # Collect insights
            if order.critical_findings:
                metrics.critical_findings.extend(order.critical_findings[:2])
            if order.positive_signals:
                metrics.positive_signals.extend(order.positive_signals[:2])
            if order.immediate_actions:
                metrics.recommended_actions.extend(order.immediate_actions[:2])

    # Calculate averages and rates
    if metrics.total_orders > 0:
        metrics.avg_order_size = metrics.total_spend / metrics.total_orders

    if deployment_scores:
        metrics.avg_deployment_score = sum(deployment_scores) / len(deployment_scores)
        metrics.deployment_success_rate = (
            metrics.successful_deployments / len(deployment_scores) * 100
        )

    if deployment_days:
        metrics.avg_deployment_days = sum(deployment_days) / len(deployment_days)

    if case_ages:
        metrics.avg_case_age_days = sum(case_ages) / len(case_ages)

    if frustration_scores:
        metrics.avg_frustration_score = sum(frustration_scores) / len(frustration_scores)
        metrics.max_frustration_score = max(frustration_scores)

    if journey_health_scores:
        metrics.journey_health_avg = sum(journey_health_scores) / len(journey_health_scores)

    # Products and dates
    metrics.products_purchased = sorted(products_seen)

    if purchase_dates:
        metrics.first_purchase_date = min(purchase_dates)
        metrics.last_purchase_date = max(purchase_dates)
        metrics.customer_tenure_days = (
            datetime.now() - metrics.first_purchase_date
        ).days

    # Calculate account health score (0-100, higher = healthier)
    metrics.account_health_score = _calculate_health_score(metrics)

    # Determine churn risk
    metrics.churn_risk = _determine_churn_risk(metrics)

    # Trim lists
    metrics.critical_findings = list(set(metrics.critical_findings))[:5]
    metrics.positive_signals = list(set(metrics.positive_signals))[:5]
    metrics.recommended_actions = list(set(metrics.recommended_actions))[:5]

    return metrics


def _calculate_health_score(metrics: AccountMetrics) -> float:
    """
    Calculate account health score (0-100).

    Components:
    - Deployment success: 25 pts max
    - Support intensity: 25 pts max (inverted - fewer is better)
    - Frustration level: 25 pts max (inverted)
    - Issue severity: 25 pts max (inverted)
    """
    score = 0.0

    # Deployment success (25 pts)
    if metrics.total_deployments > 0:
        deploy_pts = (metrics.deployment_success_rate / 100) * 25
        score += deploy_pts
    else:
        score += 15  # Neutral if no deployments

    # Support intensity (25 pts, inverted)
    if metrics.total_deployments > 0:
        intensity = metrics.total_support_cases / metrics.total_deployments
        if intensity <= 0.5:
            support_pts = 25
        elif intensity <= 1.0:
            support_pts = 20
        elif intensity <= 2.0:
            support_pts = 15
        elif intensity <= 3.0:
            support_pts = 10
        else:
            support_pts = 5
        score += support_pts
    else:
        score += 15  # Neutral

    # Frustration level (25 pts, inverted)
    if metrics.avg_frustration_score <= 3:
        frust_pts = 25
    elif metrics.avg_frustration_score <= 5:
        frust_pts = 20
    elif metrics.avg_frustration_score <= 6:
        frust_pts = 15
    elif metrics.avg_frustration_score <= 7:
        frust_pts = 10
    elif metrics.avg_frustration_score <= 8:
        frust_pts = 5
    else:
        frust_pts = 0
    score += frust_pts

    # Issue severity (25 pts, inverted)
    severe_cases = metrics.s1_cases + metrics.s2_cases
    total = max(1, metrics.total_support_cases)
    severe_ratio = severe_cases / total

    if severe_ratio <= 0.1:
        severity_pts = 25
    elif severe_ratio <= 0.2:
        severity_pts = 20
    elif severe_ratio <= 0.3:
        severity_pts = 15
    elif severe_ratio <= 0.5:
        severity_pts = 10
    else:
        severity_pts = 5
    score += severity_pts

    # Bonus/penalty for escalations
    if metrics.escalation_count > 3:
        score -= 10
    elif metrics.escalation_count > 1:
        score -= 5

    # Bonus for journey health
    if metrics.journey_health_avg > 70:
        score += 5
    elif metrics.journey_health_avg < 40:
        score -= 5

    return max(0, min(100, score))


def _determine_churn_risk(metrics: AccountMetrics) -> str:
    """Determine churn risk level based on metrics."""
    risk_score = 0

    # High frustration
    if metrics.avg_frustration_score >= 8:
        risk_score += 3
    elif metrics.avg_frustration_score >= 6:
        risk_score += 2
    elif metrics.avg_frustration_score >= 5:
        risk_score += 1

    # Multiple S1 cases
    if metrics.s1_cases >= 3:
        risk_score += 3
    elif metrics.s1_cases >= 1:
        risk_score += 1

    # Escalations
    if metrics.escalation_count >= 3:
        risk_score += 2
    elif metrics.escalation_count >= 1:
        risk_score += 1

    # Failed deployments
    if metrics.deployment_success_rate < 50 and metrics.total_deployments > 0:
        risk_score += 2

    # High support intensity
    if metrics.total_deployments > 0:
        intensity = metrics.total_support_cases / metrics.total_deployments
        if intensity > 3:
            risk_score += 2
        elif intensity > 2:
            risk_score += 1

    # Low health score
    if metrics.account_health_score < 30:
        risk_score += 2
    elif metrics.account_health_score < 50:
        risk_score += 1

    # Existing high-risk orders
    if metrics.high_risk_order_count >= 2:
        risk_score += 2
    elif metrics.high_risk_order_count >= 1:
        risk_score += 1

    # Determine risk level
    if risk_score >= 8:
        return "Critical"
    elif risk_score >= 5:
        return "High"
    elif risk_score >= 2:
        return "Medium"
    else:
        return "Low"


def calculate_all_account_metrics(
    data_store: LinkedDataStore,
) -> Dict[str, AccountMetrics]:
    """
    Calculate metrics for all accounts in the data store.

    Returns:
        Dict mapping account name to AccountMetrics
    """
    results = {}

    # Get unique accounts
    accounts = set()
    for order in data_store.orders:
        accounts.add(order.account_name)

    for account in accounts:
        metrics = calculate_account_metrics(data_store, account)
        results[account] = metrics

    return results


def get_account_comparison_table(
    all_metrics: Dict[str, AccountMetrics],
    sort_by: str = "churn_risk",
) -> List[Dict[str, Any]]:
    """
    Generate a comparison table across all accounts.

    Args:
        all_metrics: Dict of account name to AccountMetrics
        sort_by: Field to sort by (health_score, churn_risk, total_spend)

    Returns:
        List of dicts suitable for DataFrame creation
    """
    rows = []

    for account_name, metrics in all_metrics.items():
        rows.append({
            "Account": account_name,
            "Total Spend": f"${metrics.total_spend:,.0f}",
            "Orders": metrics.total_orders,
            "Deployments": metrics.total_deployments,
            "Deploy Success %": f"{metrics.deployment_success_rate:.1f}%",
            "Support Cases": metrics.total_support_cases,
            "Open Cases": metrics.open_cases,
            "Avg Frustration": f"{metrics.avg_frustration_score:.1f}",
            "S1 Cases": metrics.s1_cases,
            "Escalations": metrics.escalation_count,
            "Health Score": f"{metrics.account_health_score:.0f}",
            "Churn Risk": metrics.churn_risk,
        })

    # Sort
    risk_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Unknown": 4}

    if sort_by == "churn_risk":
        rows.sort(key=lambda x: risk_order.get(x["Churn Risk"], 4))
    elif sort_by == "health_score":
        rows.sort(key=lambda x: float(x["Health Score"]))
    elif sort_by == "total_spend":
        rows.sort(
            key=lambda x: float(x["Total Spend"].replace("$", "").replace(",", "")),
            reverse=True
        )

    return rows


def get_at_risk_accounts(
    all_metrics: Dict[str, AccountMetrics],
    min_risk: str = "High",
) -> List[AccountMetrics]:
    """
    Get accounts at or above a certain risk level.

    Args:
        all_metrics: Dict of account metrics
        min_risk: Minimum risk level ("Medium", "High", "Critical")

    Returns:
        List of AccountMetrics for at-risk accounts
    """
    risk_levels = {
        "Critical": ["Critical"],
        "High": ["Critical", "High"],
        "Medium": ["Critical", "High", "Medium"],
    }

    target_risks = risk_levels.get(min_risk, ["Critical", "High"])

    return [
        metrics for metrics in all_metrics.values()
        if metrics.churn_risk in target_risks
    ]
