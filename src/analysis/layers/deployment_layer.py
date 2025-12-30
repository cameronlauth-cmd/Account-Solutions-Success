"""
Deployment Analysis Layer (Layer 2) for Account Solutions Success.

Analyzes deployment case data to assess:
- Deployment success score (0-100)
- Service team vs self-deploy effectiveness
- Installation issues and blockers
- Expectation match vs opportunity context

Uses Claude 3.5 Haiku for analysis.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Any

from ...core import get_claude_client, streaming_output
from ...data.models import Deployment, Opportunity


@dataclass
class DeploymentAnalysisResult:
    """Result of deployment analysis."""
    # Deployment assessment
    deployment_score: int = 50  # 0-100, higher = smoother deployment
    deployment_status: str = "Unknown"  # Successful, Partial, Problematic, Failed
    is_service_deploy: bool = False

    # Issues detected
    installation_issues: List[str] = field(default_factory=list)
    blockers_encountered: List[str] = field(default_factory=list)
    time_to_deploy_days: int = 0

    # Expectation match (requires opportunity context)
    expectation_match: Optional[str] = None  # Met, Partially Met, Not Met, Unknown
    expectation_gaps: List[str] = field(default_factory=list)

    # Service team assessment
    service_quality: str = ""  # Professional, Adequate, Needs Improvement
    customer_satisfaction_signals: str = ""

    # Metadata
    analysis_model: str = "Claude 3.5 Haiku"
    analysis_successful: bool = False
    raw_response: str = ""


def _build_deployment_prompt(
    deployment: Deployment,
    opportunity: Optional[Opportunity] = None
) -> str:
    """Build the analysis prompt for a deployment."""

    # Build opportunity context if available
    opp_context = ""
    if opportunity:
        opp_context = f"""
CUSTOMER EXPECTATIONS (from Sales):
- Use Case: {opportunity.primary_use_case or 'Not specified'}
- Business Need: {opportunity.business_need or 'Not specified'}
- Pain Points: {opportunity.pain_points or 'Not specified'}
- Products Quoted: {opportunity.products_quoted}
"""

    # Combine all deployment messages
    messages_text = "\n\n---\n\n".join(deployment.messages[:20])  # Limit to 20 messages

    return f"""Analyze this deployment case to assess installation success and customer experience.

DEPLOYMENT CASE DETAILS:
Case Number: {deployment.case_number}
Account: {deployment.account_name}
Product: {deployment.product_model} ({deployment.product_series.value}-Series)
Case Duration: {deployment.case_age_days} days
Status: {deployment.status}
Severity: {deployment.severity.value}
Case Owner: {deployment.case_owner}
{opp_context}

DEPLOYMENT MESSAGES:
{messages_text}

ANALYSIS TASKS:

1. DEPLOYMENT_STATUS: Classify the deployment outcome:
   - Successful: Completed without major issues
   - Partial: Completed but with compromises or workarounds
   - Problematic: Significant issues during deployment
   - Failed: Deployment not completed or rolled back
   - In Progress: Still ongoing

2. DEPLOYMENT_SCORE: Rate 0-100 the overall deployment success:
   - 0-30: Failed or severely problematic
   - 31-50: Major issues, workarounds needed
   - 51-70: Minor issues, generally successful
   - 71-90: Smooth with minor hiccups
   - 91-100: Perfect deployment

3. IS_SERVICE_DEPLOY: Was this deployed by Professional Services team? (Yes/No)
   Look for: PS engineer, implementation specialist, service team, on-site engineer

4. INSTALLATION_ISSUES: List specific problems encountered (max 5)

5. BLOCKERS: List any showstoppers that delayed deployment (max 3)

6. SERVICE_QUALITY: If service team involved, rate their performance:
   - Professional: Excellent service, proactive communication
   - Adequate: Got the job done, no complaints
   - Needs Improvement: Delays, communication gaps, customer frustration

7. CUSTOMER_SATISFACTION: Brief assessment of customer's deployment experience

{"8. EXPECTATION_MATCH: Did deployment meet sales expectations? (Met/Partially Met/Not Met/Unknown)" if opportunity else ""}
{"9. EXPECTATION_GAPS: What expectations were not met? (max 3)" if opportunity else ""}

Respond in this exact format:
DEPLOYMENT_STATUS: [status]
DEPLOYMENT_SCORE: [number]
IS_SERVICE_DEPLOY: [Yes/No]
INSTALLATION_ISSUES:
- [issue 1]
- [issue 2]
BLOCKERS:
- [blocker 1]
SERVICE_QUALITY: [rating]
CUSTOMER_SATISFACTION: [brief assessment]
{"EXPECTATION_MATCH: [rating]" if opportunity else ""}
{"EXPECTATION_GAPS:" if opportunity else ""}
{"- [gap 1]" if opportunity else ""}"""


def _parse_deployment_response(
    response_text: str,
    has_opportunity: bool
) -> DeploymentAnalysisResult:
    """Parse Claude's response into structured result."""
    result = DeploymentAnalysisResult()
    result.raw_response = response_text

    lines = response_text.strip().split('\n')
    current_section = None
    issues = []
    blockers = []
    gaps = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('DEPLOYMENT_STATUS:'):
            status = line.replace('DEPLOYMENT_STATUS:', '').strip()
            for valid in ['Successful', 'Partial', 'Problematic', 'Failed', 'In Progress']:
                if valid.lower() in status.lower():
                    result.deployment_status = valid
                    break
            current_section = None
        elif line.startswith('DEPLOYMENT_SCORE:'):
            try:
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    result.deployment_score = min(100, max(0, int(numbers[0])))
            except:
                result.deployment_score = 50
            current_section = None
        elif line.startswith('IS_SERVICE_DEPLOY:'):
            result.is_service_deploy = 'yes' in line.lower()
            current_section = None
        elif line.startswith('INSTALLATION_ISSUES:'):
            current_section = 'issues'
        elif line.startswith('BLOCKERS:'):
            current_section = 'blockers'
        elif line.startswith('SERVICE_QUALITY:'):
            quality = line.replace('SERVICE_QUALITY:', '').strip()
            for valid in ['Professional', 'Adequate', 'Needs Improvement']:
                if valid.lower() in quality.lower():
                    result.service_quality = valid
                    break
            current_section = None
        elif line.startswith('CUSTOMER_SATISFACTION:'):
            result.customer_satisfaction_signals = line.replace('CUSTOMER_SATISFACTION:', '').strip()
            current_section = None
        elif line.startswith('EXPECTATION_MATCH:'):
            match = line.replace('EXPECTATION_MATCH:', '').strip()
            for valid in ['Met', 'Partially Met', 'Not Met', 'Unknown']:
                if valid.lower() in match.lower():
                    result.expectation_match = valid
                    break
            current_section = None
        elif line.startswith('EXPECTATION_GAPS:'):
            current_section = 'gaps'
        elif line.startswith('-') and current_section:
            item = line.lstrip('-').strip()
            if current_section == 'issues':
                issues.append(item)
            elif current_section == 'blockers':
                blockers.append(item)
            elif current_section == 'gaps':
                gaps.append(item)

    result.installation_issues = issues[:5]
    result.blockers_encountered = blockers[:3]
    result.expectation_gaps = gaps[:3]
    result.analysis_successful = True

    return result


def analyze_deployment(
    deployment: Deployment,
    opportunity_context: Optional[Opportunity] = None,
    console_output: Any = None,
    skip_ai: bool = False,
) -> DeploymentAnalysisResult:
    """
    Analyze a deployment case to assess installation success.

    Args:
        deployment: Deployment dataclass to analyze
        opportunity_context: Optional linked Opportunity for expectation matching
        console_output: Optional output handler
        skip_ai: If True, return basic analysis without AI

    Returns:
        DeploymentAnalysisResult with assessment and scoring
    """
    if console_output is None:
        console_output = streaming_output

    # Basic analysis without AI
    if skip_ai:
        result = DeploymentAnalysisResult()
        result.is_service_deploy = deployment.is_service_deploy
        result.time_to_deploy_days = deployment.case_age_days

        # Basic scoring based on status and duration
        status_lower = deployment.status.lower()
        if 'closed' in status_lower or 'resolved' in status_lower:
            base_score = 70
        elif 'open' in status_lower or 'progress' in status_lower:
            base_score = 50
            result.deployment_status = "In Progress"
        else:
            base_score = 60

        # Adjust for duration
        if deployment.case_age_days <= 7:
            base_score += 15
        elif deployment.case_age_days <= 14:
            base_score += 10
        elif deployment.case_age_days <= 30:
            base_score += 5
        elif deployment.case_age_days > 60:
            base_score -= 10

        # Adjust for severity
        if deployment.severity.value == "S1":
            base_score -= 15
        elif deployment.severity.value == "S2":
            base_score -= 10

        result.deployment_score = min(100, max(0, base_score))

        # Determine status from score
        if result.deployment_status == "Unknown":
            if result.deployment_score >= 70:
                result.deployment_status = "Successful"
            elif result.deployment_score >= 50:
                result.deployment_status = "Partial"
            else:
                result.deployment_status = "Problematic"

        result.analysis_model = "Basic Scoring (No AI)"
        result.analysis_successful = True

        return result

    # AI-powered analysis
    try:
        client = get_claude_client()

        prompt = _build_deployment_prompt(deployment, opportunity_context)

        response = client.evaluate_prompt(
            prompt=prompt,
            system_message="You are analyzing deployment case data to assess installation success. "
                          "Focus on identifying issues, assessing service quality, and evaluating "
                          "whether customer expectations were met. Be concise and factual.",
            llm_name="CLAUDE_V3_5_HAIKU",
        )

        result = _parse_deployment_response(
            response.content,
            has_opportunity=opportunity_context is not None
        )
        result.analysis_model = "Claude 3.5 Haiku"
        result.is_service_deploy = deployment.is_service_deploy or result.is_service_deploy
        result.time_to_deploy_days = deployment.case_age_days

        return result

    except Exception as e:
        console_output.stream_message(f"  Warning: AI analysis failed for deployment {deployment.case_number}: {e}")
        return analyze_deployment(deployment, opportunity_context, console_output, skip_ai=True)


def analyze_deployments_batch(
    deployments: List[Deployment],
    opportunities_map: dict = None,
    console_output: Any = None,
    skip_ai: bool = False,
) -> List[DeploymentAnalysisResult]:
    """
    Analyze multiple deployments.

    Args:
        deployments: List of Deployment objects to analyze
        opportunities_map: Optional dict of order_number -> Opportunity
        console_output: Optional output handler
        skip_ai: If True, skip AI analysis

    Returns:
        List of DeploymentAnalysisResult objects
    """
    if console_output is None:
        console_output = streaming_output

    if opportunities_map is None:
        opportunities_map = {}

    results = []

    for idx, dep in enumerate(deployments, 1):
        if idx % 10 == 0 or idx == 1:
            console_output.stream_message(f"  Analyzing deployment {idx}/{len(deployments)}...")

        # Get linked opportunity if available
        opp = opportunities_map.get(dep.order_number)

        result = analyze_deployment(dep, opp, console_output, skip_ai)
        results.append(result)

    return results
