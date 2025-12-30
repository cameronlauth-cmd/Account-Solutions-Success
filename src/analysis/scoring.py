"""
Criticality scoring for TrueNAS Sentiment Analysis.
Calculates case priority scores and account health metrics.
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Tuple

from ..core import streaming_output


def calculate_criticality_scores(
    case_analysis: List[Dict],
    console_output: Any = None
) -> List[Dict]:
    """
    Calculate criticality scores for all cases using the hybrid scoring model.

    Scoring components:
    - Claude frustration (0-100 pts, logarithmic curve)
    - Technical severity (5-35 pts)
    - Issue class (5-30 pts)
    - Resolution outlook (0-15 pts)
    - Support level priority (0-10 pts)
    - Message volume (5-30 pts, inverted)
    - Case age (0-10 pts)
    - Engagement ratio (0-15 pts)

    Args:
        case_analysis: List of case dictionaries from Claude analysis
        console_output: Object with stream_message() method

    Returns:
        case_analysis list sorted by criticality score (descending)
    """
    if console_output is None:
        console_output = streaming_output

    console_output.stream_message("\nCalculating criticality scores...")

    for case in case_analysis:
        claude = case['claude_analysis']
        frustration_score = claude['frustration_score']
        frustration_metrics = claude.get('frustration_metrics', {})

        # Component 1: Claude frustration - ENHANCED formula
        # Base points from headline score (0-50 pts)
        if frustration_score >= 9:
            base_frust_pts = 50
        elif frustration_score >= 7:
            base_frust_pts = 35 + (frustration_score - 7) * 7.5
        elif frustration_score >= 5:
            base_frust_pts = 20 + (frustration_score - 5) * 7.5
        elif frustration_score >= 3:
            base_frust_pts = 10 + (frustration_score - 3) * 5
        else:
            base_frust_pts = frustration_score * 3.33

        # Peak frustration bonus (0-25 pts) - highest individual message score
        peak_score = frustration_metrics.get('peak_score', frustration_score)
        if peak_score >= 9:
            peak_bonus = 25
        elif peak_score >= 7:
            peak_bonus = 15 + (peak_score - 7) * 5
        elif peak_score >= 5:
            peak_bonus = 5 + (peak_score - 5) * 5
        else:
            peak_bonus = peak_score * 1

        # Frustrated message percentage bonus (0-25 pts)
        total_msgs = frustration_metrics.get('total_messages', 1)
        frustrated_count = frustration_metrics.get('frustrated_message_count', 0)
        frustrated_pct = (frustrated_count / max(1, total_msgs)) * 100

        if frustrated_pct >= 30:
            pct_bonus = 25
        elif frustrated_pct >= 20:
            pct_bonus = 15 + (frustrated_pct - 20) * 1
        elif frustrated_pct >= 10:
            pct_bonus = 5 + (frustrated_pct - 10) * 1
        else:
            pct_bonus = frustrated_pct * 0.5

        claude_points = base_frust_pts + peak_bonus + pct_bonus

        # Component 2: Severity (5-35 pts)
        severity = case['severity']
        if severity == "S1":
            severity_points = 35
        elif severity == "S2":
            severity_points = 25
        elif severity == "S3":
            severity_points = 15
        else:  # S4
            severity_points = 5

        # Component 3: Issue class (5-30 pts)
        issue_class = claude.get('issue_class', 'Unknown')
        if issue_class == "Systemic":
            issue_class_points = 30
        elif issue_class == "Environmental":
            issue_class_points = 15
        elif issue_class == "Component":
            issue_class_points = 10
        elif issue_class == "Procedural":
            issue_class_points = 5
        else:
            issue_class_points = 10

        # Component 4: Resolution outlook (0-15 pts)
        resolution_outlook = claude.get('resolution_outlook', 'Unknown')
        if resolution_outlook == "Challenging":
            resolution_points = 15
        elif resolution_outlook == "Manageable":
            resolution_points = 8
        elif resolution_outlook == "Straightforward":
            resolution_points = 0
        else:
            resolution_points = 5

        # Component 5: Support level priority (0-10 pts)
        support_level = case.get('support_level', 'Unknown')
        if support_level == "Gold":
            support_points = 10
        elif support_level == "Silver":
            support_points = 5
        else:
            support_points = 0

        # Component 6: Message volume - inverted (5-30 pts)
        interaction_count = case['interaction_count']
        if interaction_count <= 5:
            volume_points = 5
        elif interaction_count <= 10:
            volume_points = 10
        elif interaction_count <= 20:
            volume_points = 20
        else:
            volume_points = 30

        # Component 7: Case age (0-10 pts)
        case_age = case['case_age_days']
        if case_age >= 90:
            age_points = 10
        elif case_age >= 60:
            age_points = 7
        elif case_age >= 30:
            age_points = 5
        elif case_age >= 14:
            age_points = 3
        else:
            age_points = 0

        # Component 8: Customer engagement (0-15 pts)
        engagement_ratio = case.get('customer_engagement_ratio', 0.5)
        if engagement_ratio >= 0.7:
            engagement_points = 15
        elif engagement_ratio >= 0.5:
            engagement_points = 10
        elif engagement_ratio >= 0.3:
            engagement_points = 5
        else:
            engagement_points = 0

        # Calculate base score
        base_score = (
            claude_points +
            severity_points +
            issue_class_points +
            resolution_points +
            support_points +
            volume_points +
            age_points +
            engagement_points
        )

        # Add Sonnet quick scoring bonus if available
        quick_scoring = case.get('deepseek_quick_scoring', {})
        quick_score_bonus = 0
        frustration_rate = 0
        damage_rate = 0

        if quick_scoring and quick_scoring.get('analysis_successful'):
            frustration_rate = quick_scoring.get('frustration_frequency', 0)
            damage_rate = quick_scoring.get('damage_frequency', 0)
            priority = quick_scoring.get('priority', 'Medium')

            # Original formula: (frustration_rate * 100) + (damage_rate * 50) + priority bonus
            # Max possible: 100 + 50 + 20 = 170 points
            quick_score_bonus = (frustration_rate / 100 * 100) + (damage_rate / 100 * 50)

            if priority == 'Critical':
                quick_score_bonus += 20
            elif priority == 'High':
                quick_score_bonus += 10
            elif priority == 'Medium':
                quick_score_bonus += 5

        # Add timeline bonus if available
        timeline_bonus = 0
        timeline_analysis = case.get('deepseek_analysis', {})
        if timeline_analysis and timeline_analysis.get('analysis_successful'):
            timeline_entries = timeline_analysis.get('timeline_entries', [])
            if timeline_entries:
                # Count frustrated entries
                frustrated_count = sum(
                    1 for e in timeline_entries
                    if 'yes' in str(e.get('frustration_detected', '')).lower()
                )
                frustration_rate_timeline = frustrated_count / len(timeline_entries) * 100
                timeline_bonus = frustration_rate_timeline / 10

        final_score = base_score + quick_score_bonus + timeline_bonus

        # Store score breakdown
        case['criticality_score'] = round(final_score, 1)
        case['score_breakdown'] = {
            'claude_frustration': round(claude_points, 1),
            'claude_frustration_base': round(base_frust_pts, 1),
            'claude_frustration_peak_bonus': round(peak_bonus, 1),
            'claude_frustration_pct_bonus': round(pct_bonus, 1),
            'severity': severity_points,
            'issue_class': issue_class_points,
            'resolution_outlook': resolution_points,
            'support_level': support_points,
            'volume': volume_points,
            'age': age_points,
            'engagement': engagement_points,
            'deepseek_quick_score': round(quick_score_bonus, 1),
            'deepseek_frustration_rate': frustration_rate,
            'deepseek_damage_rate': damage_rate,
            'deepseek_timeline': round(timeline_bonus, 1),
            'base_score': round(base_score, 1),
            'final_score': round(final_score, 1),
        }

    # Sort by criticality score (highest first)
    case_analysis.sort(key=lambda x: x['criticality_score'], reverse=True)

    console_output.stream_message(f"  Scored {len(case_analysis)} cases")

    # Report top cases
    if len(case_analysis) >= 3:
        top_3 = case_analysis[:3]
        console_output.stream_message("  Top 3 critical cases:")
        for i, case in enumerate(top_3, 1):
            console_output.stream_message(
                f"    {i}. Case {case['case_number']}: "
                f"{case['criticality_score']:.0f} pts "
                f"({case['claude_analysis']['frustration_score']}/10 frustration)"
            )

    return case_analysis


def calculate_temporal_clustering_penalty(
    case_analysis: List[Dict],
    lookback_days: int = 60
) -> Tuple[float, Dict]:
    """
    Detect if multiple concerning cases are clustered in recent time.

    Returns:
        Tuple of (penalty_multiplier, clustering_info)
        - penalty_multiplier: 0.0 to 1.0 (0 = no penalty, 1 = full penalty)
        - clustering_info: dict with details for reporting
    """
    current_date = pd.Timestamp.now()
    cutoff_date = current_date - pd.Timedelta(days=lookback_days)

    # Find cases that are concerning AND recent
    scores = [c['criticality_score'] for c in case_analysis]
    if not scores:
        return 0.0, {'detected': False}

    threshold_80th = np.percentile(scores, 80)

    recent_concerning_cases = []
    for case in case_analysis:
        try:
            case_data = case.get('case_data')
            if case_data is not None and not case_data.empty:
                last_msg = case_data['Message Date'].max()
            else:
                last_msg = pd.to_datetime(case['last_modified_date'])
        except:
            continue

        is_concerning = (
            case['criticality_score'] >= 140 and
            case['criticality_score'] >= threshold_80th
        )
        is_recent = last_msg >= cutoff_date

        if is_concerning and is_recent:
            recent_concerning_cases.append({
                'case_number': case['case_number'],
                'score': case['criticality_score'],
                'last_activity': last_msg,
                'days_ago': (current_date - last_msg).days
            })

    num_recent = len(recent_concerning_cases)

    if num_recent == 0:
        return 0.0, {'detected': False}

    elif num_recent == 1:
        penalty = 0.1
        description = "1 concerning case in last 60 days"

    elif num_recent == 2:
        dates = [c['last_activity'] for c in recent_concerning_cases[:2]]
        days_between = (max(dates) - min(dates)).days

        if days_between <= 14:
            penalty = 0.4
            description = f"2 concerning cases within {days_between} days - rapid deterioration"
        elif days_between <= 30:
            penalty = 0.25
            description = f"2 concerning cases within {days_between} days - concerning trend"
        else:
            penalty = 0.15
            description = f"2 concerning cases within {days_between} days - isolated incidents"

    elif num_recent >= 3:
        dates = [c['last_activity'] for c in recent_concerning_cases[:3]]
        days_span = (max(dates) - min(dates)).days

        if days_span <= 14:
            penalty = 0.7
            description = f"{num_recent} concerning cases within {days_span} days - SEVERE deterioration"
        elif days_span <= 30:
            penalty = 0.5
            description = f"{num_recent} concerning cases within {days_span} days - major concern"
        else:
            penalty = 0.3
            description = f"{num_recent} concerning cases within {days_span} days - ongoing issues"
    else:
        penalty = 0.0
        description = "No clustering detected"

    return penalty, {
        'detected': True,
        'penalty_multiplier': penalty,
        'recent_case_count': num_recent,
        'cases': recent_concerning_cases,
        'description': description,
        'lookback_days': lookback_days
    }


def calculate_catastrophic_override_weight(case: Dict, current_date) -> float:
    """
    Calculate override weight based on recency of catastrophic case.

    Returns:
        Weight from 0.0 to 1.0
        - 1.0 = full override (0-3 months)
        - 0.5 = half override (3-6 months)
        - 0.25 = quarter override (6-12 months)
        - 0.0 = no override (>12 months)
    """
    try:
        case_data = case.get('case_data')
        if case_data is not None and not case_data.empty:
            msg_dates = case_data['Message Date'].dropna()
            if len(msg_dates) > 0:
                last_msg_date = msg_dates.max()
            else:
                last_msg_date = pd.to_datetime(case['last_modified_date'])
        else:
            last_msg_date = pd.to_datetime(case['last_modified_date'])
    except:
        last_msg_date = pd.to_datetime(case['last_modified_date'])

    days_ago = (current_date - last_msg_date).days

    if days_ago <= 90:
        return 1.0
    elif days_ago <= 180:
        return 0.5
    elif days_ago <= 365:
        return 0.25
    else:
        return 0.0


def calculate_account_health_score(
    case_analysis: List[Dict],
    claude_statistics: Dict
) -> Tuple[float, Dict]:
    """
    Calculate holistic account health score (0-100, higher = healthier).

    Components (max 100 points):
    1. Average Frustration Level (0-30 pts)
    2. High Frustration Cases (0-20 pts)
    3. Critical Case Load (0-20 pts)
    4. Systemic Issues (0-15 pts)
    5. Resolution Complexity (0-15 pts)

    Plus temporal clustering and catastrophic override penalties.

    Returns:
        Tuple of (health_score, score_breakdown_dict)
    """
    total_cases = len(case_analysis)

    if total_cases == 0:
        return 0, {
            'frustration_component': 0,
            'high_frustration_penalty': 0,
            'critical_load_component': 0,
            'systemic_issues_component': 0,
            'resolution_complexity_component': 0
        }

    # Component 1: Average Frustration (0-30 points)
    avg_frustration = claude_statistics['avg_frustration_score']
    frustration_score = max(0, 30 - (avg_frustration * 3))

    # Component 2: High Frustration Cases (0-20 points)
    high_frustration_count = claude_statistics['high_frustration']
    high_frustration_ratio = high_frustration_count / total_cases

    # Check for catastrophic cases (>=200)
    catastrophic_cases = [c for c in case_analysis if c['criticality_score'] >= 200]
    current_date = pd.Timestamp.now()

    if len(catastrophic_cases) > 0:
        override_weights = [
            calculate_catastrophic_override_weight(c, current_date)
            for c in catastrophic_cases
        ]
        max_override = max(override_weights)
        normal_score = max(0, 20 - (high_frustration_ratio * 100))
        high_frustration_score = normal_score * (1 - max_override)
    else:
        high_frustration_score = max(0, 20 - (high_frustration_ratio * 100))
        max_override = 0.0

    # Component 3: Critical Case Load (0-20 points)
    critical_count = len([c for c in case_analysis if c['criticality_score'] >= 180])
    critical_ratio = critical_count / total_cases

    if max_override > 0:
        normal_score = max(0, 20 - (critical_ratio * 100))
        critical_score = normal_score * (1 - max_override)
    else:
        critical_score = max(0, 20 - (critical_ratio * 100))

    # Component 4: Systemic Issues (0-15 points)
    systemic_count = len([
        c for c in case_analysis
        if c['claude_analysis'].get('issue_class') == 'Systemic'
    ])
    systemic_ratio = systemic_count / total_cases
    systemic_score = max(0, 15 - (systemic_ratio * 75))

    # Component 5: Challenging Resolutions (0-15 points)
    challenging_count = len([
        c for c in case_analysis
        if c['claude_analysis'].get('resolution_outlook') == 'Challenging'
    ])
    challenging_ratio = challenging_count / total_cases
    challenging_score = max(0, 15 - (challenging_ratio * 75))

    # Base health score
    base_health_score = (
        frustration_score +
        high_frustration_score +
        critical_score +
        systemic_score +
        challenging_score
    )
    base_health_score = max(0, min(100, base_health_score))

    # Apply temporal clustering penalty
    temporal_penalty, temporal_info = calculate_temporal_clustering_penalty(
        case_analysis, lookback_days=60
    )

    if temporal_penalty > 0:
        health_score = base_health_score * (1 - temporal_penalty)
        health_score = round(max(0, min(100, health_score)), 1)
    else:
        health_score = round(base_health_score, 1)

    return health_score, {
        'frustration_component': round(frustration_score, 1),
        'high_frustration_penalty': round(high_frustration_score, 1),
        'critical_load_component': round(critical_score, 1),
        'systemic_issues_component': round(systemic_score, 1),
        'resolution_complexity_component': round(challenging_score, 1),
        'catastrophic_override_applied': max_override > 0,
        'catastrophic_override_weight': round(max_override, 2),
        'catastrophic_case_count': len(catastrophic_cases),
        'base_health_score': round(base_health_score, 1),
        'temporal_clustering_penalty': round(temporal_penalty, 2),
        'temporal_clustering_info': temporal_info
    }
