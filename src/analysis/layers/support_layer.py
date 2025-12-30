"""
Support Analysis Layer (Layer 3) for Account Solutions Success.

Analyzes support case data to assess:
- Field performance issues
- Time to resolution
- Escalation patterns
- Frustration signals
- Deployment-related issues (with deployment context)

Uses Claude 3.5 Haiku for message analysis.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Any

from ...core import get_claude_client, streaming_output
from ...data.models import SupportCase, Deployment


@dataclass
class SupportAnalysisResult:
    """Result of support case analysis."""
    # Core metrics
    frustration_score: float = 0.0  # 0-10
    criticality_score: int = 0  # 0-250 (from scoring.py formula)

    # Issue classification
    issue_class: str = "Unknown"  # Systemic, Environmental, Component, Procedural
    issue_category: str = ""  # Specific category (performance, hardware, etc.)
    resolution_outlook: str = "Unknown"  # Challenging, Manageable, Straightforward

    # Field performance
    is_hardware_failure: bool = False
    is_performance_issue: bool = False
    is_configuration_issue: bool = False
    deployment_related: Optional[bool] = None  # If linked to deployment

    # Patterns
    is_repeat_issue: bool = False
    repeat_of_case: Optional[str] = None
    escalation_detected: bool = False

    # Key findings
    key_phrase: str = ""
    pain_points: List[str] = field(default_factory=list)
    recommended_action: str = ""

    # Metadata
    analysis_model: str = "Claude 3.5 Haiku"
    analysis_successful: bool = False
    raw_response: str = ""


def _build_support_prompt(
    case: SupportCase,
    deployment_context: Optional[List[Deployment]] = None
) -> str:
    """Build the analysis prompt for a support case."""

    # Build deployment context if available
    deploy_context = ""
    if deployment_context:
        deploy_info = deployment_context[0] if deployment_context else None
        if deploy_info:
            deploy_context = f"""
DEPLOYMENT HISTORY:
- Deployment Case: {deploy_info.case_number}
- Deploy Duration: {deploy_info.case_age_days} days
- Service Deploy: {'Yes' if deploy_info.is_service_deploy else 'No (self-deploy)'}
"""

    # Combine messages (limit to reasonable size)
    messages_text = "\n\n---\n\n".join(case.messages[:15])[:10000]

    return f"""Analyze this support case to assess field performance and customer experience.

SUPPORT CASE DETAILS:
Case Number: {case.case_number}
Account: {case.account_name}
Product: {case.product_model} ({case.product_series.value}-Series)
Case Duration: {case.case_age_days} days
Status: {case.status}
Severity: {case.severity.value}
Support Level: {case.support_level.value}
Case Reason: {case.case_reason}
{deploy_context}

CASE MESSAGES:
{messages_text}

ANALYSIS TASKS:

1. FRUSTRATION_SCORE: Rate customer frustration 0-10:
   - 0: Satisfied, thankful
   - 1-3: Minor concerns, patient
   - 4-6: Visible frustration, impatience
   - 7-8: Angry, escalation threats
   - 9-10: Extreme anger, churn risk

2. ISSUE_CLASS: Classify the root cause:
   - Systemic: Product not meeting expectations overall
   - Environmental: Integration or compatibility issues
   - Component: Specific hardware/software failure
   - Procedural: Configuration or knowledge issue

3. ISSUE_CATEGORY: Specific category (e.g., Performance, Hardware Failure, Replication, Network, Upgrade)

4. RESOLUTION_OUTLOOK: How fixable is this?
   - Challenging: May not have clear solution
   - Manageable: Solvable with effort
   - Straightforward: Clear path to resolution

5. IS_HARDWARE_FAILURE: Is this a hardware problem? (Yes/No)

6. IS_PERFORMANCE_ISSUE: Is this about performance/speed? (Yes/No)

7. IS_CONFIGURATION_ISSUE: Is this a config/setup problem? (Yes/No)

{"8. DEPLOYMENT_RELATED: Is this issue related to the original deployment? (Yes/No/Unknown)" if deployment_context else ""}

9. ESCALATION_DETECTED: Are there escalation signals? (Yes/No)
   Look for: executive mentions, manager requests, contract threats

10. KEY_PHRASE: Most concerning customer statement (quote if possible)

11. PAIN_POINTS: Customer's main frustrations (max 3)

12. RECOMMENDED_ACTION: What should support do next?

Respond in this exact format:
FRUSTRATION_SCORE: [number]
ISSUE_CLASS: [class]
ISSUE_CATEGORY: [category]
RESOLUTION_OUTLOOK: [outlook]
IS_HARDWARE_FAILURE: [Yes/No]
IS_PERFORMANCE_ISSUE: [Yes/No]
IS_CONFIGURATION_ISSUE: [Yes/No]
{"DEPLOYMENT_RELATED: [Yes/No/Unknown]" if deployment_context else ""}
ESCALATION_DETECTED: [Yes/No]
KEY_PHRASE: [phrase]
PAIN_POINTS:
- [point 1]
- [point 2]
RECOMMENDED_ACTION: [action]"""


def _parse_support_response(
    response_text: str,
    has_deployment: bool
) -> SupportAnalysisResult:
    """Parse Claude's response into structured result."""
    result = SupportAnalysisResult()
    result.raw_response = response_text

    lines = response_text.strip().split('\n')
    current_section = None
    pain_points = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('FRUSTRATION_SCORE:'):
            try:
                import re
                numbers = re.findall(r'[\d.]+', line)
                if numbers:
                    result.frustration_score = min(10.0, max(0.0, float(numbers[0])))
            except:
                result.frustration_score = 5.0
            current_section = None
        elif line.startswith('ISSUE_CLASS:'):
            issue_class = line.replace('ISSUE_CLASS:', '').strip()
            for valid in ['Systemic', 'Environmental', 'Component', 'Procedural']:
                if valid.lower() in issue_class.lower():
                    result.issue_class = valid
                    break
            current_section = None
        elif line.startswith('ISSUE_CATEGORY:'):
            result.issue_category = line.replace('ISSUE_CATEGORY:', '').strip()
            current_section = None
        elif line.startswith('RESOLUTION_OUTLOOK:'):
            outlook = line.replace('RESOLUTION_OUTLOOK:', '').strip()
            for valid in ['Challenging', 'Manageable', 'Straightforward']:
                if valid.lower() in outlook.lower():
                    result.resolution_outlook = valid
                    break
            current_section = None
        elif line.startswith('IS_HARDWARE_FAILURE:'):
            result.is_hardware_failure = 'yes' in line.lower()
            current_section = None
        elif line.startswith('IS_PERFORMANCE_ISSUE:'):
            result.is_performance_issue = 'yes' in line.lower()
            current_section = None
        elif line.startswith('IS_CONFIGURATION_ISSUE:'):
            result.is_configuration_issue = 'yes' in line.lower()
            current_section = None
        elif line.startswith('DEPLOYMENT_RELATED:'):
            related = line.replace('DEPLOYMENT_RELATED:', '').strip().lower()
            if 'yes' in related:
                result.deployment_related = True
            elif 'no' in related:
                result.deployment_related = False
            else:
                result.deployment_related = None
            current_section = None
        elif line.startswith('ESCALATION_DETECTED:'):
            result.escalation_detected = 'yes' in line.lower()
            current_section = None
        elif line.startswith('KEY_PHRASE:'):
            result.key_phrase = line.replace('KEY_PHRASE:', '').strip().strip('"\'')
            current_section = None
        elif line.startswith('PAIN_POINTS:'):
            current_section = 'pain_points'
        elif line.startswith('RECOMMENDED_ACTION:'):
            result.recommended_action = line.replace('RECOMMENDED_ACTION:', '').strip()
            current_section = None
        elif line.startswith('-') and current_section == 'pain_points':
            pain_points.append(line.lstrip('-').strip())

    result.pain_points = pain_points[:3]
    result.analysis_successful = True

    return result


def analyze_support_case(
    case: SupportCase,
    deployment_context: Optional[List[Deployment]] = None,
    console_output: Any = None,
    skip_ai: bool = False,
) -> SupportAnalysisResult:
    """
    Analyze a support case to assess field performance.

    Args:
        case: SupportCase dataclass to analyze
        deployment_context: Optional linked deployments for context
        console_output: Optional output handler
        skip_ai: If True, return basic analysis without AI

    Returns:
        SupportAnalysisResult with assessment
    """
    if console_output is None:
        console_output = streaming_output

    # Basic analysis without AI
    if skip_ai:
        result = SupportAnalysisResult()

        # Copy existing flags
        result.is_repeat_issue = case.is_repeat_issue
        result.repeat_of_case = case.repeat_of_case

        # Basic scoring based on severity and duration
        base_frustration = 3.0
        if case.severity.value == "S1":
            base_frustration = 7.0
        elif case.severity.value == "S2":
            base_frustration = 5.0
        elif case.severity.value == "S3":
            base_frustration = 4.0

        # Adjust for duration
        if case.case_age_days > 30:
            base_frustration += 1.5
        elif case.case_age_days > 14:
            base_frustration += 0.5

        result.frustration_score = min(10.0, base_frustration)

        # Basic issue classification from case reason
        reason_lower = (case.case_reason or "").lower()
        if any(kw in reason_lower for kw in ["hardware", "disk", "drive", "controller"]):
            result.is_hardware_failure = True
            result.issue_class = "Component"
        elif any(kw in reason_lower for kw in ["performance", "slow", "latency", "iops"]):
            result.is_performance_issue = True
            result.issue_class = "Systemic"
        elif any(kw in reason_lower for kw in ["config", "setup", "install"]):
            result.is_configuration_issue = True
            result.issue_class = "Procedural"
        else:
            result.issue_class = "Environmental"

        result.issue_category = case.case_reason or "General Support"
        result.resolution_outlook = "Manageable"

        result.analysis_model = "Basic Scoring (No AI)"
        result.analysis_successful = True

        return result

    # AI-powered analysis
    try:
        client = get_claude_client()

        prompt = _build_support_prompt(case, deployment_context)

        response = client.evaluate_prompt(
            prompt=prompt,
            system_message="You are analyzing customer support cases for field performance issues. "
                          "Focus on identifying root causes, frustration levels, and actionable insights. "
                          "Be concise and factual.",
            llm_name="CLAUDE_V3_5_HAIKU",
        )

        result = _parse_support_response(
            response.content,
            has_deployment=deployment_context is not None
        )
        result.analysis_model = "Claude 3.5 Haiku"

        # Copy case flags
        result.is_repeat_issue = case.is_repeat_issue
        result.repeat_of_case = case.repeat_of_case

        return result

    except Exception as e:
        console_output.stream_message(f"  Warning: AI analysis failed for case {case.case_number}: {e}")
        return analyze_support_case(case, deployment_context, console_output, skip_ai=True)


def analyze_support_cases_batch(
    cases: List[SupportCase],
    deployments_map: dict = None,
    console_output: Any = None,
    skip_ai: bool = False,
) -> List[SupportAnalysisResult]:
    """
    Analyze multiple support cases.

    Args:
        cases: List of SupportCase objects to analyze
        deployments_map: Optional dict of order_number -> List[Deployment]
        console_output: Optional output handler
        skip_ai: If True, skip AI analysis

    Returns:
        List of SupportAnalysisResult objects
    """
    if console_output is None:
        console_output = streaming_output

    if deployments_map is None:
        deployments_map = {}

    results = []

    for idx, case in enumerate(cases, 1):
        if idx % 10 == 0 or idx == 1:
            console_output.stream_message(f"  Analyzing support case {idx}/{len(cases)}...")

        # Get linked deployments if available
        deploys = deployments_map.get(case.order_number, [])

        result = analyze_support_case(case, deploys if deploys else None, console_output, skip_ai)
        results.append(result)

    return results
