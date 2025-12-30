"""
Chart generation for TrueNAS Sentiment Analysis.
Creates 8 visualization charts using matplotlib.

Adapted from Part 3 of the original Abacus AI workflow.
No Abacus-specific dependencies.
"""

import io
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.patches import Patch


def save_plot_to_bytes() -> bytes:
    """Save current matplotlib figure to bytes."""
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    return buf.getvalue()


def generate_all_charts(
    case_analysis: List[Dict],
    claude_statistics: Dict,
    issue_categories: Dict,
    severity_distribution: Dict,
    support_level_distribution: Dict
) -> Dict[str, bytes]:
    """
    Generate all visualization charts.

    Returns dictionary mapping chart names to PNG bytes:
    - frustration_distribution
    - issue_categories
    - score_breakdown
    - severity_distribution
    - support_level_distribution
    - top_25_critical
    - frustration_trend
    - case_volume_trend (Gantt chart)
    """
    charts = {}
    top_25_critical = case_analysis[:25]

    # Chart 1: Frustration Distribution
    plt.figure(figsize=(10, 6))
    categories = ['High\n(7-10)', 'Medium\n(4-6)', 'Low\n(1-3)', 'None\n(0)']
    values = [
        claude_statistics['high_frustration'],
        claude_statistics['medium_frustration'],
        claude_statistics['low_frustration'],
        claude_statistics['no_frustration']
    ]
    colors = ['#DC2626', '#F59E0B', '#10B981', '#6B7280']

    bars = plt.bar(categories, values, color=colors)
    plt.title('Frustration Level Distribution', fontsize=14, fontweight='bold')
    plt.xlabel('Frustration Level', fontsize=11)
    plt.ylabel('Number of Cases', fontsize=11)

    for bar, val in zip(bars, values):
        if val > 0:
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                    str(val), ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    charts['frustration_distribution'] = save_plot_to_bytes()
    plt.close()

    # Chart 2: Issue Categories
    plt.figure(figsize=(10, 6))
    if issue_categories:
        sorted_categories = sorted(issue_categories.items(), key=lambda x: x[1], reverse=True)
        cat_names = [c[0] for c in sorted_categories]
        cat_values = [c[1] for c in sorted_categories]

        category_colors = {
            'Systemic': '#DC2626',
            'Environmental': '#F59E0B',
            'Component': '#3B82F6',
            'Procedural': '#10B981',
            'Unknown': '#6B7280'
        }
        colors = [category_colors.get(name, '#6B7280') for name in cat_names]

        bars = plt.bar(cat_names, cat_values, color=colors)
        plt.title('Issue Class Distribution', fontsize=14, fontweight='bold')
        plt.xlabel('Issue Class', fontsize=11)
        plt.ylabel('Number of Cases', fontsize=11)

        for bar, val in zip(bars, cat_values):
            if val > 0:
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                        str(val), ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    charts['issue_categories'] = save_plot_to_bytes()
    plt.close()

    # Chart 3: Score Breakdown (Top 10)
    plt.figure(figsize=(14, 8))
    top_10 = case_analysis[:10]

    case_nums = [f"Case {c['case_number']}" for c in top_10]
    x = np.arange(len(case_nums))
    width = 0.15

    component_names = ['Claude', 'Severity', 'Issue Class', 'Resolution', 'Other']

    for i, case in enumerate(top_10):
        sb = case['score_breakdown']
        other = (sb.get('support_level', 0) + sb.get('volume', 0) +
                sb.get('age', 0) + sb.get('engagement', 0))

        components = [
            sb['claude_frustration'],
            sb['severity'],
            sb['issue_class'],
            sb['resolution_outlook'],
            other
        ]

        component_colors = ['#3B82F6', '#EF4444', '#F59E0B', '#8B5CF6', '#6B7280']

        bottom = 0
        for j, (comp, color) in enumerate(zip(components, component_colors)):
            plt.bar(x[i], comp, width * 4, bottom=bottom, color=color,
                   label=component_names[j] if i == 0 else "")
            bottom += comp

    plt.xlabel('Cases', fontsize=11)
    plt.ylabel('Criticality Score', fontsize=11)
    plt.title('Score Component Breakdown - Top 10 Cases', fontsize=14, fontweight='bold')
    plt.xticks(x, case_nums, rotation=45, ha='right')
    plt.legend(loc='upper right')
    plt.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()

    charts['score_breakdown'] = save_plot_to_bytes()
    plt.close()

    # Chart 4: Severity Distribution
    plt.figure(figsize=(8, 6))
    if severity_distribution:
        sorted_sev = sorted(severity_distribution.items())
        sev_names = [s[0] for s in sorted_sev]
        sev_values = [s[1] for s in sorted_sev]

        sev_colors = {
            'S1': '#DC2626',
            'S2': '#F59E0B',
            'S3': '#3B82F6',
            'S4': '#10B981'
        }
        colors = [sev_colors.get(name, '#6B7280') for name in sev_names]

        bars = plt.bar(sev_names, sev_values, color=colors)
        plt.title('Case Severity Distribution', fontsize=14, fontweight='bold')
        plt.xlabel('Severity Level', fontsize=11)
        plt.ylabel('Number of Cases', fontsize=11)

        for bar, val in zip(bars, sev_values):
            if val > 0:
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                        str(val), ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    charts['severity_distribution'] = save_plot_to_bytes()
    plt.close()

    # Chart 5: Support Level Distribution
    plt.figure(figsize=(8, 6))
    if support_level_distribution:
        sorted_support = sorted(support_level_distribution.items(),
                               key=lambda x: x[1], reverse=True)
        support_names = [s[0] for s in sorted_support]
        support_values = [s[1] for s in sorted_support]

        support_colors = {
            'Gold': '#FFD700',
            'Silver': '#C0C0C0',
            'Bronze': '#CD7F32',
            'Basic': '#6B7280',
            'Unknown': '#374151'
        }
        colors = [support_colors.get(name, '#6B7280') for name in support_names]

        bars = plt.bar(support_names, support_values, color=colors, edgecolor='black')
        plt.title('Support Level Distribution', fontsize=14, fontweight='bold')
        plt.xlabel('Support Level', fontsize=11)
        plt.ylabel('Number of Cases', fontsize=11)

        for bar, val in zip(bars, support_values):
            if val > 0:
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                        str(val), ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    charts['support_level_distribution'] = save_plot_to_bytes()
    plt.close()

    # Chart 6: Top 25 Critical Cases (Horizontal Bar)
    plt.figure(figsize=(14, 10))
    case_labels = [f"Case {c['case_number']}" for c in reversed(top_25_critical)]
    scores = [c['criticality_score'] for c in reversed(top_25_critical)]

    colors = []
    for case in reversed(top_25_critical):
        score = case['criticality_score']
        if score >= 190:
            colors.append('#DC2626')
        elif score >= 140:
            colors.append('#ea580c')
        else:
            colors.append('#16a34a')

    bars = plt.barh(case_labels, scores, color=colors)
    plt.xlabel('Criticality Score', fontsize=11)
    plt.ylabel('Case Number', fontsize=11)
    plt.title('Top 25 Critical Cases by Criticality Score', fontsize=14, fontweight='bold')
    plt.axvline(x=190, color='#DC2626', linestyle='--', alpha=0.5, label='Critical (190)')
    plt.axvline(x=140, color='#ea580c', linestyle='--', alpha=0.5, label='High (140)')
    plt.legend(loc='lower right')
    plt.grid(True, axis='x', alpha=0.3)
    plt.tight_layout()

    charts['top_25_critical'] = save_plot_to_bytes()
    plt.close()

    # Chart 7: Frustration Trend Over Time
    plt.figure(figsize=(14, 6))

    def get_first_message_date(case):
        try:
            case_data = case.get('case_data')
            if case_data is not None and not case_data.empty:
                msg_dates = case_data['Message Date'].dropna()
                if len(msg_dates) > 0:
                    return msg_dates.min()
        except:
            pass
        return pd.to_datetime(case['created_date'])

    # Prepare data for trend chart
    trend_data = []
    for case in case_analysis:
        first_date = get_first_message_date(case)
        if pd.notna(first_date):
            trend_data.append({
                'date': first_date,
                'case_number': case['case_number'],
                'frustration': case['claude_analysis']['frustration_score'],
                'criticality': case['criticality_score']
            })

    if trend_data:
        trend_df = pd.DataFrame(trend_data)
        trend_df = trend_df.sort_values('date')

        # Plot individual cases
        for _, row in trend_df.iterrows():
            frust = row['frustration']
            if frust >= 7:
                color = '#DC2626'
                marker = 'o'
            elif frust >= 4:
                color = '#F59E0B'
                marker = 's'
            else:
                color = '#10B981'
                marker = '^'

            plt.scatter(row['date'], frust, color=color, s=50, marker=marker, alpha=0.7)

            if frust >= 7:
                plt.annotate(f"{row['case_number']}", (row['date'], frust),
                           textcoords="offset points", xytext=(0, 8),
                           ha='center', fontsize=7, color='#DC2626')

        # Add trend line (rolling average)
        if len(trend_df) >= 3:
            trend_df['rolling_avg'] = trend_df['frustration'].rolling(window=3, min_periods=1).mean()
            plt.plot(trend_df['date'], trend_df['rolling_avg'],
                    color='#3B82F6', linewidth=2, linestyle='-', alpha=0.8, label='3-case moving avg')

        plt.axhline(y=7, color='#DC2626', linestyle='--', alpha=0.5, label='High frustration threshold')
        plt.xlabel('Date', fontsize=11)
        plt.ylabel('Frustration Score (0-10)', fontsize=11)
        plt.title('Frustration Score Trend Over Time', fontsize=14, fontweight='bold')
        plt.legend(loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

    charts['frustration_trend'] = save_plot_to_bytes()
    plt.close()

    # Chart 8: Case Timeline Gantt Chart
    plt.figure(figsize=(14, 10))

    def get_last_message_date(case):
        try:
            case_data = case.get('case_data')
            if case_data is not None and not case_data.empty:
                msg_dates = case_data['Message Date'].dropna()
                if len(msg_dates) > 0:
                    return msg_dates.max()
        except:
            pass
        return pd.to_datetime(case['last_modified_date'])

    # Sort cases by first message date (newest first)
    cases_sorted = sorted(case_analysis, key=get_first_message_date, reverse=True)
    display_cases = cases_sorted[:30]

    valid_cases = []
    for case in display_cases:
        try:
            start_date = get_first_message_date(case)
            end_date = get_last_message_date(case)

            if pd.notna(start_date) and pd.notna(end_date) and start_date <= end_date:
                valid_cases.append({
                    'case': case,
                    'start': start_date,
                    'end': end_date,
                    'duration_days': (end_date - start_date).days
                })
        except:
            continue

    if len(valid_cases) > 0:
        for idx, case_info in enumerate(valid_cases):
            case = case_info['case']
            start = case_info['start']
            end = case_info['end']

            criticality = case['criticality_score']
            if criticality >= 190:
                color = '#DC2626'
                alpha = 0.9
            elif criticality >= 140:
                color = '#ea580c'
                alpha = 0.8
            else:
                color = '#16a34a'
                alpha = 0.7

            start_num = mdates.date2num(start)
            end_num = mdates.date2num(end)
            width = end_num - start_num

            if width < 1:
                width = 1

            plt.barh(
                idx,
                width,
                left=start_num,
                height=0.8,
                color=color,
                alpha=alpha,
                edgecolor='black',
                linewidth=0.5
            )

            label = f"Case {case['case_number']}"
            if case['status'] not in ['Closed', 'Closed-NA', 'Closed Duplicate', 'Closed-Test']:
                label += " (Active)"

            if width > 30:
                plt.text(
                    start_num + width/2,
                    idx,
                    label,
                    va='center',
                    ha='center',
                    fontsize=7,
                    color='white',
                    fontweight='bold'
                )
            else:
                plt.text(
                    start_num - 2,
                    idx,
                    label,
                    va='center',
                    ha='right',
                    fontsize=7
                )

        ax = plt.gca()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))

        plt.xlabel('Date', fontsize=11)
        plt.ylabel('Cases (Newest to Oldest)', fontsize=11)
        plt.title('Case Timeline - Recent Activity (Top 30 Most Recent Cases)',
                 fontsize=14, fontweight='bold', pad=20)
        plt.yticks([])
        plt.grid(True, axis='x', alpha=0.3)
        plt.gcf().autofmt_xdate()

        legend_elements = [
            Patch(facecolor='#DC2626', alpha=0.9, label='Critical Priority (Score >=190)'),
            Patch(facecolor='#ea580c', alpha=0.8, label='High Priority (Score 140-189)'),
            Patch(facecolor='#16a34a', alpha=0.7, label='Lower Priority (Score <140)')
        ]
        plt.legend(handles=legend_elements, loc='upper right')

        plt.tight_layout()

    charts['case_volume_trend'] = save_plot_to_bytes()
    plt.close()

    return charts
