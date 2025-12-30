"""
Opportunity Analysis Layer (Layer 1) for Account Solutions Success.

Analyzes Salesforce Opportunity data to extract:
- Customer use case and workload type
- Business need and requirements
- Pain points and challenges
- Customer expectations
- Opportunity score (0-100)

Uses Claude 3.5 Haiku for fast analysis of opportunity context.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Any

from ...core import get_claude_client, streaming_output
from ...data.models import Opportunity


@dataclass
class OpportunityAnalysisResult:
    """Result of opportunity analysis."""
    # Extracted context
    use_case_extracted: str = ""
    use_case_category: str = ""  # Media, Backup, Virtualization, etc.
    business_need_extracted: str = ""
    pain_points_extracted: List[str] = field(default_factory=list)
    customer_expectations: List[str] = field(default_factory=list)

    # Scoring
    opportunity_score: int = 50  # 0-100, higher = clearer requirements

    # Metadata
    analysis_model: str = "Claude 3.5 Haiku"
    analysis_successful: bool = False
    raw_response: str = ""


# Use case categories for classification
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


def _build_opportunity_prompt(opp: Opportunity) -> str:
    """Build the analysis prompt for an opportunity."""
    return f"""Analyze this sales opportunity to extract customer context and expectations.

OPPORTUNITY DETAILS:
Account: {opp.account_name}
Opportunity Name: {opp.opportunity_name}
Amount: ${opp.amount:,.2f}
Close Date: {opp.close_date.strftime('%Y-%m-%d') if opp.close_date else 'Unknown'}
Primary Product: {opp.primary_product}
Products Quoted: {opp.products_quoted}
System Model: {opp.system_model}

CUSTOMER-PROVIDED CONTEXT:
Business Need: {opp.business_need or 'Not provided'}
Primary Use Case: {opp.primary_use_case or 'Not provided'}
Pain Points: {opp.pain_points or 'Not provided'}

ANALYSIS TASKS:

1. USE_CASE_SUMMARY: Summarize in 1-2 sentences what the customer wants to accomplish with this system.

2. USE_CASE_CATEGORY: Classify into ONE of these categories:
   - Media & Entertainment (video editing, post-production, broadcast)
   - Backup & Archive (data protection, long-term storage, DR)
   - Virtualization (VM storage, VDI, containers)
   - Database (SQL, NoSQL, analytics)
   - File Sharing (NAS, collaboration, home directories)
   - Video Surveillance (security cameras, NVR)
   - Scientific/HPC (research, simulations, rendering)
   - General Purpose (mixed workloads, unclear)
   - Unknown (insufficient information)

3. BUSINESS_NEED_SUMMARY: What business problem are they solving? (1-2 sentences)

4. PAIN_POINTS: List specific challenges or problems mentioned (bullet points, max 5)

5. EXPECTATIONS: What does the customer expect from this purchase? (bullet points, max 5)

6. CLARITY_SCORE: Rate 0-100 how clearly the customer's requirements are documented:
   - 0-30: Vague, missing critical details
   - 31-60: Some context but gaps exist
   - 61-80: Good documentation, minor gaps
   - 81-100: Excellent, comprehensive requirements

Respond in this exact format:
USE_CASE_SUMMARY: [your summary]
USE_CASE_CATEGORY: [category name]
BUSINESS_NEED_SUMMARY: [your summary]
PAIN_POINTS:
- [point 1]
- [point 2]
EXPECTATIONS:
- [expectation 1]
- [expectation 2]
CLARITY_SCORE: [number]"""


def _parse_opportunity_response(response_text: str) -> OpportunityAnalysisResult:
    """Parse Claude's response into structured result."""
    result = OpportunityAnalysisResult()
    result.raw_response = response_text

    lines = response_text.strip().split('\n')
    current_section = None
    pain_points = []
    expectations = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('USE_CASE_SUMMARY:'):
            result.use_case_extracted = line.replace('USE_CASE_SUMMARY:', '').strip()
            current_section = None
        elif line.startswith('USE_CASE_CATEGORY:'):
            category = line.replace('USE_CASE_CATEGORY:', '').strip()
            # Match to known categories
            for known_cat in USE_CASE_CATEGORIES:
                if known_cat.lower() in category.lower():
                    result.use_case_category = known_cat
                    break
            if not result.use_case_category:
                result.use_case_category = "Unknown"
            current_section = None
        elif line.startswith('BUSINESS_NEED_SUMMARY:'):
            result.business_need_extracted = line.replace('BUSINESS_NEED_SUMMARY:', '').strip()
            current_section = None
        elif line.startswith('PAIN_POINTS:'):
            current_section = 'pain_points'
        elif line.startswith('EXPECTATIONS:'):
            current_section = 'expectations'
        elif line.startswith('CLARITY_SCORE:'):
            try:
                score_text = line.replace('CLARITY_SCORE:', '').strip()
                # Extract first number found
                import re
                numbers = re.findall(r'\d+', score_text)
                if numbers:
                    result.opportunity_score = min(100, max(0, int(numbers[0])))
            except:
                result.opportunity_score = 50
            current_section = None
        elif line.startswith('-') and current_section:
            point = line.lstrip('-').strip()
            if current_section == 'pain_points':
                pain_points.append(point)
            elif current_section == 'expectations':
                expectations.append(point)

    result.pain_points_extracted = pain_points[:5]
    result.customer_expectations = expectations[:5]
    result.analysis_successful = True

    return result


def analyze_opportunity(
    opportunity: Opportunity,
    console_output: Any = None,
    skip_ai: bool = False,
) -> OpportunityAnalysisResult:
    """
    Analyze an opportunity to extract customer context and expectations.

    Args:
        opportunity: Opportunity dataclass to analyze
        console_output: Optional output handler
        skip_ai: If True, return basic extraction without AI analysis

    Returns:
        OpportunityAnalysisResult with extracted context and scoring
    """
    if console_output is None:
        console_output = streaming_output

    # Basic extraction without AI
    if skip_ai:
        result = OpportunityAnalysisResult()
        result.use_case_extracted = opportunity.primary_use_case or ""
        result.business_need_extracted = opportunity.business_need or ""

        # Basic category detection
        use_case_lower = (opportunity.primary_use_case or "").lower()
        if any(kw in use_case_lower for kw in ["media", "video", "broadcast", "post"]):
            result.use_case_category = "Media & Entertainment"
        elif any(kw in use_case_lower for kw in ["backup", "archive", "dr", "disaster"]):
            result.use_case_category = "Backup & Archive"
        elif any(kw in use_case_lower for kw in ["vm", "virtual", "vdi", "container"]):
            result.use_case_category = "Virtualization"
        elif any(kw in use_case_lower for kw in ["database", "sql", "analytics"]):
            result.use_case_category = "Database"
        elif any(kw in use_case_lower for kw in ["file", "share", "nas", "collab"]):
            result.use_case_category = "File Sharing"
        elif any(kw in use_case_lower for kw in ["surveil", "camera", "nvr", "security"]):
            result.use_case_category = "Video Surveillance"
        elif any(kw in use_case_lower for kw in ["hpc", "research", "scientific", "render"]):
            result.use_case_category = "Scientific/HPC"
        else:
            result.use_case_category = "General Purpose" if use_case_lower else "Unknown"

        # Parse pain points if provided
        if opportunity.pain_points:
            result.pain_points_extracted = [
                p.strip() for p in opportunity.pain_points.split(',')
            ][:5]

        # Calculate basic score based on field completeness
        score = 30  # Base
        if opportunity.primary_use_case:
            score += 20
        if opportunity.business_need:
            score += 20
        if opportunity.pain_points:
            score += 15
        if opportunity.amount > 0:
            score += 15

        result.opportunity_score = min(100, score)
        result.analysis_model = "Basic Extraction (No AI)"
        result.analysis_successful = True

        return result

    # AI-powered analysis
    try:
        client = get_claude_client()

        prompt = _build_opportunity_prompt(opportunity)

        response = client.evaluate_prompt(
            prompt=prompt,
            system_message="You are analyzing sales opportunity data to extract customer context. "
                          "Focus on understanding what the customer needs and expects from this purchase. "
                          "Be concise and factual.",
            llm_name="CLAUDE_V3_5_HAIKU",
        )

        result = _parse_opportunity_response(response.content)
        result.analysis_model = "Claude 3.5 Haiku"

        return result

    except Exception as e:
        # Fallback to basic extraction on error
        console_output.stream_message(f"  Warning: AI analysis failed for opportunity {opportunity.order_number}: {e}")
        return analyze_opportunity(opportunity, console_output, skip_ai=True)


def analyze_opportunities_batch(
    opportunities: List[Opportunity],
    console_output: Any = None,
    skip_ai: bool = False,
) -> List[OpportunityAnalysisResult]:
    """
    Analyze multiple opportunities.

    Args:
        opportunities: List of Opportunity objects to analyze
        console_output: Optional output handler
        skip_ai: If True, skip AI analysis

    Returns:
        List of OpportunityAnalysisResult objects
    """
    if console_output is None:
        console_output = streaming_output

    results = []

    for idx, opp in enumerate(opportunities, 1):
        if idx % 10 == 0 or idx == 1:
            console_output.stream_message(f"  Analyzing opportunity {idx}/{len(opportunities)}...")

        result = analyze_opportunity(opp, console_output, skip_ai)
        results.append(result)

    return results
