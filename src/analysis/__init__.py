"""
Analysis module for TrueNAS Sentiment Analysis.
Contains data loading, Claude analysis, scoring, and asset correlation functions.
"""

from .data_loader import (
    load_and_prepare_data,
    detect_and_merge_case_relationships,
    build_tech_map_for_case,
)
from .claude_analysis import (
    run_claude_analysis,
    run_deepseek_quick_scoring,
    run_deepseek_detailed_timeline,
    DEFAULT_ANALYSIS_CONTEXT,
)
from .scoring import (
    calculate_criticality_scores,
    calculate_account_health_score,
    calculate_temporal_clustering_penalty,
)
from .asset_correlation import (
    analyze_asset_correlations,
    build_account_intelligence_brief,
)

__all__ = [
    # Data loading
    'load_and_prepare_data',
    'detect_and_merge_case_relationships',
    'build_tech_map_for_case',

    # Claude analysis
    'run_claude_analysis',
    'run_deepseek_quick_scoring',
    'run_deepseek_detailed_timeline',
    'DEFAULT_ANALYSIS_CONTEXT',

    # Scoring
    'calculate_criticality_scores',
    'calculate_account_health_score',
    'calculate_temporal_clustering_penalty',

    # Asset correlation
    'analyze_asset_correlations',
    'build_account_intelligence_brief',
]
