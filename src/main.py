"""
Main orchestration for TrueNAS Sentiment Analysis.
Local deployment version - adapted from Abacus AI workflow.

This module coordinates the full analysis pipeline:
1. Load and prepare data from Excel
2. Run Claude 3.5 Haiku analysis on all cases
3. Calculate criticality scores
4. Run Claude 3.5 Sonnet quick scoring and detailed timelines
5. Generate visualizations
6. Save outputs (charts, JSON, PDF report)
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import numpy as np

from .core import (
    Config,
    console,
    print_header,
    print_stage,
    print_success,
    print_error,
    print_health_score,
    streaming_output,
)
from .analysis import (
    load_and_prepare_data,
    detect_and_merge_case_relationships,
    run_claude_analysis,
    run_deepseek_quick_scoring,
    run_deepseek_detailed_timeline,
    calculate_criticality_scores,
    calculate_account_health_score,
    analyze_asset_correlations,
    build_account_intelligence_brief,
    DEFAULT_ANALYSIS_CONTEXT,
)
from .visualization import generate_all_charts
from .context import (
    load_context_for_case,
    get_product_line_from_serial,
    get_product_line_from_series,
    get_product_line_from_model,
)


def build_enhanced_context(df, client=None) -> tuple:
    """
    Build enhanced analysis context from loaded data.

    Detects product line from Product Series or Product Model columns and loads:
    - Global context (SLA, always-load docs)
    - Product-specific documentation

    Args:
        df: DataFrame with case data containing Product Series or Product Model columns
        client: Optional streaming output client for progress messages

    Returns:
        Tuple of (enhanced_context_string, detected_product_line)
    """
    if client is None:
        client = streaming_output

    detected_products = set()

    # Primary method: Use Product Series column (e.g., 'F', 'M', 'H', 'R')
    if "Product Series" in df.columns:
        series_values = df["Product Series"].dropna().unique().tolist()
        for series in series_values:
            product = get_product_line_from_series(str(series))
            if product:
                detected_products.add(product)

    # Fallback: Use Product Model column (e.g., 'F100-HA', 'M50')
    if not detected_products and "Product Model" in df.columns:
        model_values = df["Product Model"].dropna().unique().tolist()
        for model in model_values:
            product = get_product_line_from_model(str(model))
            if product:
                detected_products.add(product)

    # Last resort: Use Asset Serial column
    if not detected_products and "Asset Serial" in df.columns:
        serial_values = df["Asset Serial"].dropna().unique().tolist()
        for serial in serial_values:
            product = get_product_line_from_serial(str(serial))
            if product:
                detected_products.add(product)

    # Use first detected product (most common case: single product per account)
    primary_product = list(detected_products)[0] if detected_products else None

    if primary_product:
        client.stream_message(f"  Detected product line: {primary_product}")
        if len(detected_products) > 1:
            client.stream_message(f"  Note: Multiple products detected: {', '.join(detected_products)}")

    # Load context (SLA + product-specific docs)
    loaded_context, product_line = load_context_for_case(
        product_line=primary_product
    )

    # Combine with default analysis context
    if loaded_context:
        enhanced_context = DEFAULT_ANALYSIS_CONTEXT + "\n\n" + loaded_context
        client.stream_message(f"  Loaded {len(loaded_context):,} chars of product documentation")
    else:
        enhanced_context = DEFAULT_ANALYSIS_CONTEXT
        client.stream_message("  Using default context (no product docs loaded)")

    return enhanced_context, product_line


def run_analysis(
    input_file: str,
    output_dir: Optional[str] = None,
    analysis_context: Optional[str] = None,
    skip_sonnet: bool = False,
) -> Dict[str, Any]:
    """
    Run the complete sentiment analysis pipeline.

    Args:
        input_file: Path to Excel file with case data
        output_dir: Output directory (default: outputs/)
        analysis_context: Custom analysis context (default: TrueNAS context)
        skip_sonnet: If True, skip Sonnet analysis (faster, cheaper)

    Returns:
        Dictionary with analysis results and paths to output files
    """
    # Validate configuration
    errors = Config.validate()
    if errors:
        for error in errors:
            print_error(error)
        raise ValueError("Configuration validation failed")

    # Setup directories
    Config.ensure_directories()

    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = Config.OUTPUT_DIR

    # Note: analysis_context is now built after data loading if not provided,
    # using build_enhanced_context() which loads SLA + product-specific docs

    # Create timestamped output folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_output_dir = output_path / f"analysis_{timestamp}"
    run_output_dir.mkdir(parents=True, exist_ok=True)

    charts_dir = run_output_dir / "charts"
    json_dir = run_output_dir / "json"
    reports_dir = run_output_dir / "reports"

    charts_dir.mkdir(exist_ok=True)
    json_dir.mkdir(exist_ok=True)
    reports_dir.mkdir(exist_ok=True)

    print_header(
        "TrueNAS Customer Sentiment Analysis",
        f"Input: {input_file}"
    )

    start_time = time.time()
    client = streaming_output

    try:
        # STAGE 1: Load and prepare data
        print_stage(1, "DATA LOADING", "Loading Excel file and preparing data")
        df, current_date = load_and_prepare_data(input_file, client)

        # STAGE 1.5: Detect and merge duplicates
        df = detect_and_merge_case_relationships(df, client)

        # STAGE 1.6: Load context documentation
        if analysis_context is None:
            print_stage(2, "CONTEXT LOADING", "Loading SLA and product documentation")
            analysis_context, detected_product = build_enhanced_context(df, client)
        else:
            detected_product = None
            client.stream_message("  Using custom analysis context provided")

        # STAGE 2: Claude Haiku analysis
        print_stage(3, "CLAUDE 3.5 HAIKU ANALYSIS", "Analyzing all cases for frustration patterns")
        (case_analysis, claude_statistics, issue_categories,
         support_level_distribution, claude_time) = run_claude_analysis(
            df, analysis_context, client
        )

        # STAGE 4: Criticality scoring
        print_stage(4, "CRITICALITY SCORING", "Calculating priority scores")
        case_analysis = calculate_criticality_scores(case_analysis, client)

        # Initialize Sonnet statistics
        deepseek_statistics = {
            "total_scored": 0,
            "total_analyzed": 0,
            "api_errors": 0,
            "quick_scoring_time": 0,
            "detailed_timeline_time": 0,
            "analysis_time_seconds": 0,
        }
        deepseek_time = 0

        if not skip_sonnet:
            # Build account brief for quick scoring
            account_brief_light = build_account_intelligence_brief(
                case_analysis, asset_correlations=None, mode='light'
            )

            # STAGE 5: Claude Sonnet quick scoring
            print_stage(5, "CLAUDE 3.5 SONNET - QUICK SCORING", "Pattern analysis on top cases")
            quick_stats, quick_time = run_deepseek_quick_scoring(
                case_analysis, analysis_context, client, account_brief_light
            )
            deepseek_statistics.update(quick_stats)
            deepseek_statistics["quick_scoring_time"] = quick_time

            # Recalculate scores with Sonnet data
            case_analysis = calculate_criticality_scores(case_analysis, client)

            # STAGE 6: Asset correlation
            print_stage(6, "ASSET CORRELATION", "Analyzing hardware patterns")
            asset_correlations = analyze_asset_correlations(case_analysis, client)

            # Build full account brief
            account_brief_full = build_account_intelligence_brief(
                case_analysis, asset_correlations, mode='full'
            )

            # STAGE 7: Claude Sonnet detailed timelines
            print_stage(7, "CLAUDE 3.5 SONNET - DETAILED TIMELINES", "Building interaction timelines")
            timeline_stats, timeline_time = run_deepseek_detailed_timeline(
                case_analysis, analysis_context, client, account_brief_full, asset_correlations
            )
            deepseek_statistics["total_analyzed"] = timeline_stats["total_analyzed"]
            deepseek_statistics["api_errors"] += timeline_stats["api_errors"]
            deepseek_statistics["detailed_timeline_time"] = timeline_time
            deepseek_statistics["analysis_time_seconds"] = quick_time + timeline_time
            deepseek_time = quick_time + timeline_time
        else:
            asset_correlations = analyze_asset_correlations(case_analysis, client)

        # STAGE 8: Generate visualizations
        print_stage(8 if not skip_sonnet else 6, "VISUALIZATION", "Generating charts")

        severity_distribution = {}
        for case in case_analysis:
            sev = case["severity"]
            severity_distribution[sev] = severity_distribution.get(sev, 0) + 1

        charts = generate_all_charts(
            case_analysis,
            claude_statistics,
            issue_categories,
            severity_distribution,
            support_level_distribution
        )

        # Save charts
        for chart_name, chart_bytes in charts.items():
            chart_path = charts_dir / f"{chart_name}.png"
            with open(chart_path, 'wb') as f:
                f.write(chart_bytes)
            client.stream_message(f"  Saved: {chart_path.name}")

        # STAGE 6: Calculate account health
        customer_name = case_analysis[0]['customer_name'] if case_analysis else "Unknown"
        health_score, score_breakdown = calculate_account_health_score(
            case_analysis, claude_statistics
        )

        total_time = time.time() - start_time

        # Print summary
        print_health_score(health_score, customer_name)

        # STAGE 9: Save JSON outputs
        print_stage(9 if not skip_sonnet else 7, "SAVING OUTPUTS", "Writing JSON and preparing report")

        def clean_for_json(case_list):
            """Remove non-serializable data from cases."""
            cleaned = []
            for case in case_list:
                case_copy = case.copy()
                case_copy.pop('case_data', None)
                case_copy.pop('messages_full', None)
                cleaned.append(case_copy)
            return cleaned

        # Summary statistics
        summary_stats = {
            "analysis_date": current_date.strftime("%Y-%m-%d"),
            "account_name": customer_name,
            "account_health_score": round(health_score, 1),
            "total_cases": len(case_analysis),
            "analysis_time_seconds": round(total_time, 1),
            "claude_haiku_time": round(claude_time, 1),
            "claude_sonnet_time": round(deepseek_time, 1),
            "severity_distribution": severity_distribution,
            "support_level_distribution": support_level_distribution,
            "claude_statistics": claude_statistics,
            "deepseek_statistics": deepseek_statistics,
            "score_breakdown": score_breakdown,
        }

        with open(json_dir / "summary_statistics.json", 'w') as f:
            json.dump(summary_stats, f, indent=2, default=str)

        # Top 25 cases
        top_25 = case_analysis[:25]
        top_25_data = {
            "analysis_date": current_date.strftime("%Y-%m-%d"),
            "account_name": customer_name,
            "methodology": "Hybrid: Claude 3.5 Haiku + Claude 3.5 Sonnet",
            "cases": clean_for_json(top_25),
        }

        with open(json_dir / "top_25_critical_cases.json", 'w') as f:
            json.dump(top_25_data, f, indent=2, default=str)

        # All cases (condensed)
        all_cases_data = {
            "analysis_date": current_date.strftime("%Y-%m-%d"),
            "account_name": customer_name,
            "total_cases": len(case_analysis),
            "cases": [
                {
                    "case_number": c["case_number"],
                    "criticality_score": c["criticality_score"],
                    "frustration_score": c["claude_analysis"]["frustration_score"],
                    "severity": c["severity"],
                    "status": c["status"],
                    "age_days": c["case_age_days"],
                }
                for c in case_analysis
            ]
        }

        with open(json_dir / "all_cases.json", 'w') as f:
            json.dump(all_cases_data, f, indent=2, default=str)

        client.stream_message(f"  Saved: summary_statistics.json")
        client.stream_message(f"  Saved: top_25_critical_cases.json")
        client.stream_message(f"  Saved: all_cases.json")

        # Final summary
        console.print()
        console.print(f"[bold green]Analysis complete![/bold green]")
        console.print(f"  Total time: {total_time:.1f}s")
        console.print(f"  Output directory: {run_output_dir}")
        console.print()

        return {
            "success": True,
            "output_dir": str(run_output_dir),
            "customer_name": customer_name,
            "health_score": health_score,
            "total_cases": len(case_analysis),
            "critical_cases": len([c for c in case_analysis if c['criticality_score'] >= 180]),
            "analysis_time": total_time,
            "charts": charts,
            "case_analysis": case_analysis,
            "statistics": {
                "claude": claude_statistics,
                "sonnet": deepseek_statistics,
            },
            "asset_correlations": asset_correlations,
        }

    except Exception as e:
        print_error(f"Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            "success": False,
            "error": str(e),
        }


def run_full_analysis(
    opportunities_path: Optional[str] = None,
    deployments_path: Optional[str] = None,
    support_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    skip_ai: bool = False,
    skip_sonnet: bool = False,
) -> Dict[str, Any]:
    """
    Run the full 4-layer analysis pipeline across all data sources.

    This is the Phase 4 pipeline that orchestrates:
    - Data loading from all 3 sources (opportunities, deployments, support)
    - Order Number linking across sources
    - 4-layer AI analysis (opportunity, deployment, support, evaluation)
    - Multi-dimensional metrics calculation
    - JSON output generation

    Args:
        opportunities_path: Path to opportunities Excel file (glob pattern allowed)
        deployments_path: Path to deployments Excel file (glob pattern allowed)
        support_path: Path to support cases Excel file (glob pattern allowed)
        output_dir: Output directory (default: outputs/)
        skip_ai: If True, skip all AI analysis (fastest, for testing)
        skip_sonnet: If True, skip only Sonnet analysis (faster, cheaper)

    Returns:
        Dictionary with analysis results and paths to output files
    """
    from dataclasses import asdict
    from glob import glob

    # Import data layer
    from .data import (
        load_opportunities,
        load_deployments,
        load_support_cases,
        link_data_sources,
        LinkedDataStore,
    )

    # Import analysis layers
    from .analysis.layers import (
        analyze_opportunity,
        analyze_deployment,
        analyze_support_case,
        evaluate_customer_journey,
    )

    # Import metrics
    from .analysis.metrics import (
        calculate_all_product_metrics,
        calculate_all_account_metrics,
        calculate_all_usecase_metrics,
        compare_service_vs_self_deploy,
    )

    # Validate configuration
    errors = Config.validate()
    if errors:
        for error in errors:
            print_error(error)
        raise ValueError("Configuration validation failed")

    # Setup directories
    Config.ensure_directories()

    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = Config.OUTPUT_DIR

    # Create timestamped output folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_output_dir = output_path / f"full_analysis_{timestamp}"
    run_output_dir.mkdir(parents=True, exist_ok=True)

    json_dir = run_output_dir / "json"
    json_dir.mkdir(exist_ok=True)

    print_header(
        "Account Solutions Full Analysis",
        "4-Layer Pipeline: Opportunity > Deployment > Support > Evaluation"
    )

    start_time = time.time()
    client = streaming_output

    try:
        # Resolve glob patterns to actual files
        def resolve_path(pattern: Optional[str]) -> Optional[str]:
            if not pattern:
                return None
            matches = glob(pattern)
            if matches:
                return matches[0]  # Use first match
            if Path(pattern).exists():
                return pattern
            return None

        opp_file = resolve_path(opportunities_path)
        deploy_file = resolve_path(deployments_path)
        support_file = resolve_path(support_path)

        # =====================================================
        # STAGE 1: DATA LOADING
        # =====================================================
        print_stage(1, "DATA LOADING", "Loading all data sources")

        opportunities = []
        deployments = []
        support_cases = []

        if opp_file:
            client.stream_message(f"  Loading opportunities: {opp_file}")
            opportunities = load_opportunities(opp_file, client)
            client.stream_message(f"    Loaded {len(opportunities)} opportunities")
        else:
            client.stream_message("  No opportunities file provided")

        if deploy_file:
            client.stream_message(f"  Loading deployments: {deploy_file}")
            deployments = load_deployments(deploy_file, client)
            client.stream_message(f"    Loaded {len(deployments)} deployments")
        else:
            client.stream_message("  No deployments file provided")

        if support_file:
            client.stream_message(f"  Loading support cases: {support_file}")
            support_cases = load_support_cases(support_file, console_output=client)
            client.stream_message(f"    Loaded {len(support_cases)} support cases")
        else:
            client.stream_message("  No support cases file provided")

        # =====================================================
        # STAGE 2: DATA LINKING
        # =====================================================
        print_stage(2, "DATA LINKING", "Correlating via Order Number")

        linked_data = link_data_sources(
            opportunities=opportunities,
            deployments=deployments,
            support_cases=support_cases,
            console_output=client,
        )

        client.stream_message(linked_data.summary.summary())

        # =====================================================
        # STAGE 3: LAYER 1 - OPPORTUNITY ANALYSIS
        # =====================================================
        print_stage(3, "OPPORTUNITY ANALYSIS", "Extracting customer expectations (Layer 1)")

        opportunity_results = {}
        for order in linked_data.orders:
            if order.opportunity:
                result = analyze_opportunity(
                    order.opportunity,
                    console_output=client,
                    skip_ai=skip_ai,
                )
                opportunity_results[order.order_number] = result

        client.stream_message(f"  Analyzed {len(opportunity_results)} opportunities")

        # =====================================================
        # STAGE 4: LAYER 2 - DEPLOYMENT ANALYSIS
        # =====================================================
        print_stage(4, "DEPLOYMENT ANALYSIS", "Assessing installation quality (Layer 2)")

        deployment_results = {}
        for order in linked_data.orders:
            for deploy in order.deployments:
                result = analyze_deployment(
                    deploy,
                    opportunity_context=order.opportunity,
                    console_output=client,
                    skip_ai=skip_ai,
                )
                deployment_results[deploy.case_number] = result

        client.stream_message(f"  Analyzed {len(deployment_results)} deployments")

        # =====================================================
        # STAGE 5: LAYER 3 - SUPPORT ANALYSIS
        # =====================================================
        print_stage(5, "SUPPORT ANALYSIS", "Analyzing field performance (Layer 3)")

        support_results = {}
        for order in linked_data.orders:
            for case in order.support_cases:
                result = analyze_support_case(
                    case,
                    deployment_context=order.deployments,
                    console_output=client,
                    skip_ai=skip_ai,
                )
                support_results[case.case_number] = result

        client.stream_message(f"  Analyzed {len(support_results)} support cases")

        # =====================================================
        # STAGE 6: LAYER 4 - CROSS-LAYER EVALUATION
        # =====================================================
        print_stage(6, "CROSS-LAYER EVALUATION", "Correlating journey insights (Layer 4)")

        evaluation_results = {}
        fully_linked_count = 0

        # Only run Sonnet evaluation if not skipping
        skip_evaluation_ai = skip_ai or skip_sonnet

        for order in linked_data.orders:
            # Evaluate all orders, but prioritize fully linked ones
            if order.has_opportunity or order.has_deployments or order.has_support_cases:
                if order.is_fully_linked:
                    fully_linked_count += 1

                result = evaluate_customer_journey(
                    order,
                    console_output=client,
                    skip_ai=skip_evaluation_ai,
                )
                evaluation_results[order.order_number] = result

                # Update the order with evaluation results
                order.journey_health_score = result.journey_health_score
                order.churn_risk = result.churn_risk
                order.critical_findings = result.critical_findings
                order.positive_signals = result.positive_signals
                order.immediate_actions = result.immediate_actions

        client.stream_message(f"  Evaluated {len(evaluation_results)} orders ({fully_linked_count} fully linked)")

        # =====================================================
        # STAGE 7: METRICS CALCULATION
        # =====================================================
        print_stage(7, "METRICS CALCULATION", "Computing multi-dimensional metrics")

        product_metrics = calculate_all_product_metrics(linked_data)
        client.stream_message(f"  Product metrics: {len(product_metrics)} product lines")

        account_metrics = calculate_all_account_metrics(linked_data)
        client.stream_message(f"  Account metrics: {len(account_metrics)} accounts")

        usecase_metrics = calculate_all_usecase_metrics(linked_data)
        client.stream_message(f"  Use case metrics: {len(usecase_metrics)} use cases")

        service_comparison = compare_service_vs_self_deploy(linked_data)
        client.stream_message(f"  Service comparison calculated (value-add score: {service_comparison.service_value_add_score:.0f})")

        # =====================================================
        # STAGE 8: JSON OUTPUT GENERATION
        # =====================================================
        print_stage(8, "OUTPUT GENERATION", "Saving JSON results")

        def safe_asdict(obj):
            """Convert dataclass to dict, handling non-dataclass objects."""
            if hasattr(obj, '__dataclass_fields__'):
                return asdict(obj)
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            return str(obj)

        # Opportunities JSON
        opp_output = {
            "total": len(opportunities),
            "analyzed": len(opportunity_results),
            "opportunities": [
                {
                    "order_number": opp.order_number,
                    "account_name": opp.account_name,
                    "opportunity_name": opp.opportunity_name,
                    "amount": opp.amount,
                    "primary_product": opp.primary_product,
                    "analysis": safe_asdict(opportunity_results.get(opp.order_number)) if opp.order_number in opportunity_results else None,
                }
                for opp in opportunities
            ]
        }
        with open(json_dir / "opportunities.json", 'w') as f:
            json.dump(opp_output, f, indent=2, default=str)
        client.stream_message(f"  Saved: opportunities.json")

        # Deployments JSON
        deploy_output = {
            "total": len(deployments),
            "analyzed": len(deployment_results),
            "deployments": [
                {
                    "case_number": dep.case_number,
                    "order_number": dep.order_number,
                    "account_name": dep.account_name,
                    "product_model": dep.product_model,
                    "status": dep.status,
                    "analysis": safe_asdict(deployment_results.get(dep.case_number)) if dep.case_number in deployment_results else None,
                }
                for dep in deployments
            ]
        }
        with open(json_dir / "deployments.json", 'w') as f:
            json.dump(deploy_output, f, indent=2, default=str)
        client.stream_message(f"  Saved: deployments.json")

        # Support Cases JSON
        support_output = {
            "total": len(support_cases),
            "analyzed": len(support_results),
            "support_cases": [
                {
                    "case_number": case.case_number,
                    "order_number": case.order_number,
                    "account_name": case.account_name,
                    "severity": case.severity.value,
                    "status": case.status,
                    "analysis": safe_asdict(support_results.get(case.case_number)) if case.case_number in support_results else None,
                }
                for case in support_cases
            ]
        }
        with open(json_dir / "support_cases.json", 'w') as f:
            json.dump(support_output, f, indent=2, default=str)
        client.stream_message(f"  Saved: support_cases.json")

        # Cross-Layer Insights JSON
        insights_output = {
            "total_orders": len(linked_data.orders),
            "fully_linked": fully_linked_count,
            "evaluations": [
                {
                    "order_number": order.order_number,
                    "account_name": order.account_name,
                    "has_opportunity": order.has_opportunity,
                    "has_deployments": order.has_deployments,
                    "has_support_cases": order.has_support_cases,
                    "is_fully_linked": order.is_fully_linked,
                    "evaluation": safe_asdict(evaluation_results.get(order.order_number)) if order.order_number in evaluation_results else None,
                }
                for order in linked_data.orders
            ]
        }
        with open(json_dir / "cross_layer_insights.json", 'w') as f:
            json.dump(insights_output, f, indent=2, default=str)
        client.stream_message(f"  Saved: cross_layer_insights.json")

        # Product Metrics JSON
        product_output = {
            "products": [safe_asdict(pm) for pm in product_metrics]
        }
        with open(json_dir / "product_metrics.json", 'w') as f:
            json.dump(product_output, f, indent=2, default=str)
        client.stream_message(f"  Saved: product_metrics.json")

        # Account Metrics JSON
        account_output = {
            "accounts": [safe_asdict(am) for am in account_metrics]
        }
        with open(json_dir / "account_metrics.json", 'w') as f:
            json.dump(account_output, f, indent=2, default=str)
        client.stream_message(f"  Saved: account_metrics.json")

        # Use Case Metrics JSON
        usecase_output = {
            "use_cases": {name: safe_asdict(um) for name, um in usecase_metrics.items()}
        }
        with open(json_dir / "usecase_metrics.json", 'w') as f:
            json.dump(usecase_output, f, indent=2, default=str)
        client.stream_message(f"  Saved: usecase_metrics.json")

        # Service Comparison JSON
        service_output = {
            "service_deploy": safe_asdict(service_comparison.service_metrics),
            "self_deploy": safe_asdict(service_comparison.self_metrics),
            "comparison": {
                "deployment_score_delta": service_comparison.deployment_score_delta,
                "success_rate_delta": service_comparison.success_rate_delta,
                "support_intensity_delta": service_comparison.support_intensity_delta,
                "frustration_delta": service_comparison.frustration_delta,
                "journey_health_delta": service_comparison.journey_health_delta,
                "service_value_add_score": service_comparison.service_value_add_score,
                "recommendation": service_comparison.recommendation,
            }
        }
        with open(json_dir / "service_metrics.json", 'w') as f:
            json.dump(service_output, f, indent=2, default=str)
        client.stream_message(f"  Saved: service_metrics.json")

        # Link Summary JSON
        with open(json_dir / "link_summary.json", 'w') as f:
            json.dump(safe_asdict(linked_data.summary), f, indent=2, default=str)
        client.stream_message(f"  Saved: link_summary.json")

        total_time = time.time() - start_time

        # Print summary
        console.print()
        console.print(f"[bold green]Full Analysis Complete![/bold green]")
        console.print(f"  Total time: {total_time:.1f}s")
        console.print(f"  Opportunities analyzed: {len(opportunity_results)}")
        console.print(f"  Deployments analyzed: {len(deployment_results)}")
        console.print(f"  Support cases analyzed: {len(support_results)}")
        console.print(f"  Orders linked: {len(linked_data.orders)}")
        console.print(f"  Fully linked: {fully_linked_count}")
        console.print(f"  Output directory: {run_output_dir}")
        console.print()

        return {
            "success": True,
            "output_dir": run_output_dir,
            "opportunities_analyzed": len(opportunity_results),
            "deployments_analyzed": len(deployment_results),
            "cases_analyzed": len(support_results),
            "linked_orders": len(linked_data.orders),
            "fully_linked_orders": fully_linked_count,
            "analysis_time": total_time,
            "linked_data": linked_data,
            "opportunity_results": opportunity_results,
            "deployment_results": deployment_results,
            "support_results": support_results,
            "evaluation_results": evaluation_results,
            "product_metrics": product_metrics,
            "account_metrics": account_metrics,
            "usecase_metrics": usecase_metrics,
            "service_comparison": service_comparison,
        }

    except Exception as e:
        print_error(f"Full analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            "success": False,
            "error": str(e),
        }
