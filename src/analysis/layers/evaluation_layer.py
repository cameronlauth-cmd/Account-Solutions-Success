"""
Evaluation Analysis Layer (Layer 4) for Account Solutions Success.

Cross-layer correlation analysis that ties together:
- Opportunity expectations (what was promised)
- Deployment reality (how it was installed)
- Support experience (field performance)

Uses Claude 3.5 Sonnet for deeper analysis and correlation.
Outputs:
- Expectation vs Reality assessment
- Journey health score (0-100)
- Churn risk classification
- Actionable recommendations
"""

from dataclasses import dataclass, field
from typing import Optional, List, Any

from ...core import get_claude_client, streaming_output
from ...data.models import LinkedOrder


@dataclass
class EvaluationResult:
    """Result of cross-layer evaluation."""
    # Journey assessment
    journey_health_score: int = 50  # 0-100
    churn_risk: str = "Unknown"  # Low, Medium, High, Critical

    # Expectation vs Reality
    expectation_vs_reality: str = ""  # Summary of match/mismatch
    expectations_met: List[str] = field(default_factory=list)
    expectations_not_met: List[str] = field(default_factory=list)

    # Deployment impact
    deployment_impact_on_support: str = ""  # How deployment affected support needs

    # Key insights
    root_cause_pattern: str = ""  # Underlying pattern across layers
    critical_findings: List[str] = field(default_factory=list)
    positive_signals: List[str] = field(default_factory=list)

    # Recommendations
    immediate_actions: List[str] = field(default_factory=list)
    relationship_recovery: str = ""

    # Metadata
    analysis_model: str = "Claude 3.5 Sonnet"
    analysis_successful: bool = False
    raw_response: str = ""


def _build_evaluation_prompt(order: LinkedOrder) -> str:
    """Build the cross-layer evaluation prompt."""

    # Build opportunity section
    opp_section = "NO OPPORTUNITY DATA LINKED"
    if order.opportunity:
        opp = order.opportunity
        opp_section = f"""WHAT WAS SOLD (Opportunity Layer):
- Product: {opp.primary_product}
- Amount: ${opp.amount:,.2f}
- Use Case: {opp.primary_use_case or 'Not specified'}
- Business Need: {opp.business_need or 'Not specified'}
- Pain Points: {opp.pain_points or 'Not specified'}
- Close Date: {opp.close_date.strftime('%Y-%m-%d') if opp.close_date else 'Unknown'}"""

    # Build deployment section
    deploy_section = "NO DEPLOYMENT DATA LINKED"
    if order.deployments:
        dep = order.deployments[0]
        deploy_section = f"""HOW IT WAS DEPLOYED (Deployment Layer):
- Deployment Type: {'Professional Services' if dep.is_service_deploy else 'Self-Deploy'}
- Duration: {dep.case_age_days} days
- Status: {dep.status}
- Severity: {dep.severity.value}
- Key Issues: {', '.join(dep.messages[:2]) if dep.messages else 'None recorded'}"""

    # Build support section
    support_section = "NO SUPPORT CASES LINKED"
    if order.support_cases:
        total_cases = len(order.support_cases)
        severities = [c.severity.value for c in order.support_cases]
        s1_count = severities.count("S1")
        s2_count = severities.count("S2")
        total_age = sum(c.case_age_days for c in order.support_cases)
        avg_age = total_age / total_cases if total_cases > 0 else 0

        # Get unique case reasons
        reasons = list(set(c.case_reason for c in order.support_cases if c.case_reason))[:5]

        support_section = f"""FIELD EXPERIENCE (Support Layer):
- Total Cases: {total_cases}
- S1 Critical: {s1_count}, S2 High: {s2_count}
- Average Case Duration: {avg_age:.0f} days
- Issue Categories: {', '.join(reasons) if reasons else 'Various'}"""

    return f"""Perform a cross-layer evaluation of this customer's journey from sale to support.

ORDER: {order.order_number}
ACCOUNT: {order.account_name}

{opp_section}

{deploy_section}

{support_section}

EVALUATION TASKS:

1. JOURNEY_HEALTH_SCORE: Rate 0-100 the overall customer journey health:
   - 0-30: Critical - Major gaps between expectations and reality
   - 31-50: Poor - Significant issues, relationship at risk
   - 51-70: Fair - Some problems, recoverable
   - 71-85: Good - Minor issues, generally positive
   - 86-100: Excellent - Expectations met or exceeded

2. CHURN_RISK: Classify the churn risk:
   - Critical: High likelihood of leaving, immediate intervention needed
   - High: Significant risk, proactive engagement required
   - Medium: Some concerns, monitoring recommended
   - Low: Stable relationship, standard engagement

3. EXPECTATION_VS_REALITY: 2-3 sentences summarizing how well the actual experience matched what was sold.

4. EXPECTATIONS_MET: List what went well (max 3)

5. EXPECTATIONS_NOT_MET: List where reality fell short (max 3)

6. DEPLOYMENT_IMPACT: How did the deployment approach affect support needs? (1-2 sentences)

7. ROOT_CAUSE_PATTERN: What underlying pattern do you see across all layers? (1-2 sentences)

8. CRITICAL_FINDINGS: Most important issues to address (max 3)

9. POSITIVE_SIGNALS: Positive indicators in the relationship (max 3)

10. IMMEDIATE_ACTIONS: What should be done now? (max 3 specific actions)

11. RELATIONSHIP_RECOVERY: If at risk, what recovery strategy is recommended? (1-2 sentences)

Respond in this exact format:
JOURNEY_HEALTH_SCORE: [number]
CHURN_RISK: [level]
EXPECTATION_VS_REALITY: [summary]
EXPECTATIONS_MET:
- [item 1]
- [item 2]
EXPECTATIONS_NOT_MET:
- [item 1]
- [item 2]
DEPLOYMENT_IMPACT: [summary]
ROOT_CAUSE_PATTERN: [pattern]
CRITICAL_FINDINGS:
- [finding 1]
- [finding 2]
POSITIVE_SIGNALS:
- [signal 1]
IMMEDIATE_ACTIONS:
- [action 1]
- [action 2]
RELATIONSHIP_RECOVERY: [strategy]"""


def _parse_evaluation_response(response_text: str) -> EvaluationResult:
    """Parse Sonnet's response into structured result."""
    result = EvaluationResult()
    result.raw_response = response_text

    lines = response_text.strip().split('\n')
    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('JOURNEY_HEALTH_SCORE:'):
            try:
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    result.journey_health_score = min(100, max(0, int(numbers[0])))
            except:
                result.journey_health_score = 50
            current_section = None
        elif line.startswith('CHURN_RISK:'):
            risk = line.replace('CHURN_RISK:', '').strip()
            for valid in ['Critical', 'High', 'Medium', 'Low']:
                if valid.lower() in risk.lower():
                    result.churn_risk = valid
                    break
            current_section = None
        elif line.startswith('EXPECTATION_VS_REALITY:'):
            result.expectation_vs_reality = line.replace('EXPECTATION_VS_REALITY:', '').strip()
            current_section = None
        elif line.startswith('EXPECTATIONS_MET:'):
            current_section = 'met'
        elif line.startswith('EXPECTATIONS_NOT_MET:'):
            current_section = 'not_met'
        elif line.startswith('DEPLOYMENT_IMPACT:'):
            result.deployment_impact_on_support = line.replace('DEPLOYMENT_IMPACT:', '').strip()
            current_section = None
        elif line.startswith('ROOT_CAUSE_PATTERN:'):
            result.root_cause_pattern = line.replace('ROOT_CAUSE_PATTERN:', '').strip()
            current_section = None
        elif line.startswith('CRITICAL_FINDINGS:'):
            current_section = 'critical'
        elif line.startswith('POSITIVE_SIGNALS:'):
            current_section = 'positive'
        elif line.startswith('IMMEDIATE_ACTIONS:'):
            current_section = 'actions'
        elif line.startswith('RELATIONSHIP_RECOVERY:'):
            result.relationship_recovery = line.replace('RELATIONSHIP_RECOVERY:', '').strip()
            current_section = None
        elif line.startswith('-'):
            item = line.lstrip('-').strip()
            if current_section == 'met':
                result.expectations_met.append(item)
            elif current_section == 'not_met':
                result.expectations_not_met.append(item)
            elif current_section == 'critical':
                result.critical_findings.append(item)
            elif current_section == 'positive':
                result.positive_signals.append(item)
            elif current_section == 'actions':
                result.immediate_actions.append(item)

    # Trim lists to max items
    result.expectations_met = result.expectations_met[:3]
    result.expectations_not_met = result.expectations_not_met[:3]
    result.critical_findings = result.critical_findings[:3]
    result.positive_signals = result.positive_signals[:3]
    result.immediate_actions = result.immediate_actions[:3]

    result.analysis_successful = True
    return result


def evaluate_customer_journey(
    order: LinkedOrder,
    console_output: Any = None,
    skip_ai: bool = False,
) -> EvaluationResult:
    """
    Perform cross-layer evaluation of a customer journey.

    Requires a LinkedOrder with data from multiple sources for meaningful analysis.

    Args:
        order: LinkedOrder with opportunity, deployment, and/or support data
        console_output: Optional output handler
        skip_ai: If True, return basic evaluation without AI

    Returns:
        EvaluationResult with cross-layer insights
    """
    if console_output is None:
        console_output = streaming_output

    # Basic evaluation without AI
    if skip_ai:
        result = EvaluationResult()

        # Calculate basic health score
        base_score = 70

        # Adjust based on what data we have
        if order.has_opportunity:
            base_score += 5  # Good to have context

        if order.has_deployments:
            dep = order.deployments[0]
            if dep.case_age_days > 30:
                base_score -= 10
            if dep.severity.value in ["S1", "S2"]:
                base_score -= 10

        if order.has_support_cases:
            case_count = len(order.support_cases)
            if case_count > 5:
                base_score -= 15
            elif case_count > 2:
                base_score -= 5

            # Check for S1 cases
            s1_count = sum(1 for c in order.support_cases if c.severity.value == "S1")
            base_score -= s1_count * 10

        result.journey_health_score = min(100, max(0, base_score))

        # Determine churn risk from score
        if result.journey_health_score < 30:
            result.churn_risk = "Critical"
        elif result.journey_health_score < 50:
            result.churn_risk = "High"
        elif result.journey_health_score < 70:
            result.churn_risk = "Medium"
        else:
            result.churn_risk = "Low"

        result.expectation_vs_reality = "Basic evaluation - AI analysis required for detailed assessment."
        result.analysis_model = "Basic Scoring (No AI)"
        result.analysis_successful = True

        return result

    # AI-powered evaluation
    try:
        client = get_claude_client()

        prompt = _build_evaluation_prompt(order)

        response = client.evaluate_prompt(
            prompt=prompt,
            system_message="You are performing cross-layer analysis of customer journeys from sale to support. "
                          "Focus on correlating expectations with reality, identifying patterns, and providing "
                          "actionable insights for relationship management. Be concise but thorough.",
            llm_name="CLAUDE_V3_5_SONNET",
        )

        result = _parse_evaluation_response(response.content)
        result.analysis_model = "Claude 3.5 Sonnet"

        return result

    except Exception as e:
        console_output.stream_message(f"  Warning: AI evaluation failed for order {order.order_number}: {e}")
        return evaluate_customer_journey(order, console_output, skip_ai=True)


def evaluate_orders_batch(
    orders: List[LinkedOrder],
    console_output: Any = None,
    skip_ai: bool = False,
    only_fully_linked: bool = False,
) -> List[EvaluationResult]:
    """
    Evaluate multiple customer journeys.

    Args:
        orders: List of LinkedOrder objects to evaluate
        console_output: Optional output handler
        skip_ai: If True, skip AI analysis
        only_fully_linked: If True, only evaluate orders with all 3 data sources

    Returns:
        List of EvaluationResult objects
    """
    if console_output is None:
        console_output = streaming_output

    # Filter if requested
    if only_fully_linked:
        orders = [o for o in orders if o.is_fully_linked]
        console_output.stream_message(f"  Evaluating {len(orders)} fully-linked orders")

    results = []

    for idx, order in enumerate(orders, 1):
        if idx % 5 == 0 or idx == 1:
            console_output.stream_message(f"  Evaluating order {idx}/{len(orders)} ({order.order_number})...")

        result = evaluate_customer_journey(order, console_output, skip_ai)
        results.append(result)

    return results
