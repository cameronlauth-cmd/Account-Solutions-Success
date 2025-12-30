"""
Analysis Layers Package for Account Solutions Success.

4-Layer Analysis Pipeline:
- Layer 1: Opportunity Analysis - What was sold and expected
- Layer 2: Deployment Analysis - How was it deployed
- Layer 3: Support Analysis - Field performance and issues
- Layer 4: Evaluation Analysis - Cross-layer correlation
"""

from .opportunity_layer import analyze_opportunity, OpportunityAnalysisResult
from .deployment_layer import analyze_deployment, DeploymentAnalysisResult
from .support_layer import analyze_support_case, SupportAnalysisResult
from .evaluation_layer import evaluate_customer_journey, EvaluationResult

__all__ = [
    # Opportunity Layer
    "analyze_opportunity",
    "OpportunityAnalysisResult",
    # Deployment Layer
    "analyze_deployment",
    "DeploymentAnalysisResult",
    # Support Layer
    "analyze_support_case",
    "SupportAnalysisResult",
    # Evaluation Layer
    "evaluate_customer_journey",
    "EvaluationResult",
]
