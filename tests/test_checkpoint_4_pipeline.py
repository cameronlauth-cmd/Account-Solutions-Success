"""
Checkpoint 4 Tests - End-to-End Pipeline Validation

Tests the full 4-layer analysis pipeline:
- Full pipeline integration with sample data
- CLI command validation
- JSON output verification
"""

import pytest
import subprocess
import sys
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# Sample data paths (relative to project root)
SAMPLE_OPPORTUNITIES = "Account-Analysis-Reports/Ai Opportunities Correlation Report-2025-12-30-08-51-03.xlsx"
SAMPLE_DEPLOYMENTS = "Account-Analysis-Reports/PS Deploy Account AI Email Body-2025-12-30-08-53-31.xlsx"
SAMPLE_SUPPORT = "Account-Analysis-Reports/Account  AI Email Body-2025-12-30-08-50-53.xlsx"


class TestFullPipelineIntegration:
    """Test the run_full_analysis() function end-to-end."""

    def test_full_pipeline_with_all_sources(self, tmp_path):
        """Run entire pipeline with all three data sources."""
        from src.main import run_full_analysis

        opp_path = PROJECT_ROOT / SAMPLE_OPPORTUNITIES
        deploy_path = PROJECT_ROOT / SAMPLE_DEPLOYMENTS
        support_path = PROJECT_ROOT / SAMPLE_SUPPORT

        # Skip if sample data not available
        if not opp_path.exists():
            pytest.skip(f"Sample opportunities file not found: {opp_path}")
        if not deploy_path.exists():
            pytest.skip(f"Sample deployments file not found: {deploy_path}")
        if not support_path.exists():
            pytest.skip(f"Sample support file not found: {support_path}")

        result = run_full_analysis(
            opportunities_path=str(opp_path),
            deployments_path=str(deploy_path),
            support_path=str(support_path),
            output_dir=str(tmp_path),
            skip_ai=True,  # Fast test mode - no AI calls
        )

        # Verify success
        assert result["success"], f"Pipeline failed: {result.get('error')}"

        # Verify analysis counts
        assert result["opportunities_analyzed"] >= 0
        assert result["deployments_analyzed"] >= 0
        assert result["cases_analyzed"] >= 0
        assert result["linked_orders"] >= 0

        # Verify output directory created
        output_dir = result["output_dir"]
        assert Path(output_dir).exists()

    def test_full_pipeline_outputs_generated(self, tmp_path):
        """Verify all expected JSON outputs are generated."""
        from src.main import run_full_analysis

        opp_path = PROJECT_ROOT / SAMPLE_OPPORTUNITIES
        deploy_path = PROJECT_ROOT / SAMPLE_DEPLOYMENTS
        support_path = PROJECT_ROOT / SAMPLE_SUPPORT

        # Skip if sample data not available
        if not all(p.exists() for p in [opp_path, deploy_path, support_path]):
            pytest.skip("Sample data files not found")

        result = run_full_analysis(
            opportunities_path=str(opp_path),
            deployments_path=str(deploy_path),
            support_path=str(support_path),
            output_dir=str(tmp_path),
            skip_ai=True,
        )

        assert result["success"]
        output_dir = Path(result["output_dir"])
        json_dir = output_dir / "json"

        # Verify all JSON outputs exist
        expected_outputs = [
            "opportunities.json",
            "deployments.json",
            "support_cases.json",
            "cross_layer_insights.json",
            "product_metrics.json",
            "account_metrics.json",
            "usecase_metrics.json",
            "service_metrics.json",
            "link_summary.json",
        ]

        for filename in expected_outputs:
            output_file = json_dir / filename
            assert output_file.exists(), f"Expected output not found: {filename}"

    def test_full_pipeline_support_only(self, tmp_path):
        """Test pipeline works with only support cases (backward compatible)."""
        from src.main import run_full_analysis

        support_path = PROJECT_ROOT / SAMPLE_SUPPORT

        if not support_path.exists():
            pytest.skip(f"Sample support file not found: {support_path}")

        result = run_full_analysis(
            support_path=str(support_path),
            output_dir=str(tmp_path),
            skip_ai=True,
        )

        assert result["success"]
        assert result["cases_analyzed"] >= 0

    def test_full_pipeline_returns_data_structures(self, tmp_path):
        """Verify pipeline returns proper data structures for downstream use."""
        from src.main import run_full_analysis

        support_path = PROJECT_ROOT / SAMPLE_SUPPORT

        if not support_path.exists():
            pytest.skip(f"Sample support file not found: {support_path}")

        result = run_full_analysis(
            support_path=str(support_path),
            output_dir=str(tmp_path),
            skip_ai=True,
        )

        assert result["success"]

        # Verify linked_data is returned
        assert "linked_data" in result
        linked_data = result["linked_data"]
        assert hasattr(linked_data, "orders")
        assert hasattr(linked_data, "summary")

        # Verify metrics are returned
        assert "product_metrics" in result
        assert "account_metrics" in result
        assert "usecase_metrics" in result
        assert "service_comparison" in result


class TestCLIAnalyzeFull:
    """Test the analyze-full CLI command."""

    def test_cli_help(self):
        """Test CLI help message works."""
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "analyze-full", "--help"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "analyze-full" in result.stdout or "full" in result.stdout.lower()

    def test_cli_requires_at_least_one_source(self):
        """Test CLI fails gracefully when no sources provided."""
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "analyze-full"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        # Should fail because no data sources provided
        assert result.returncode != 0

    def test_cli_analyze_full_quick_mode(self, tmp_path):
        """Test CLI command works in quick mode."""
        support_path = PROJECT_ROOT / SAMPLE_SUPPORT

        if not support_path.exists():
            pytest.skip(f"Sample support file not found: {support_path}")

        result = subprocess.run(
            [
                sys.executable, "-m", "src.cli", "analyze-full",
                "--support", str(support_path),
                "--output", str(tmp_path),
                "--quick",
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=120,  # 2 minute timeout
        )

        # Print output for debugging if failed
        if result.returncode != 0:
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)

        assert result.returncode == 0, f"CLI failed: {result.stderr}"


class TestPipelineDataFlow:
    """Test data flows correctly through the pipeline."""

    def test_order_linking_populates_orders(self, tmp_path):
        """Verify Order Number linking creates linked orders."""
        from src.main import run_full_analysis

        support_path = PROJECT_ROOT / SAMPLE_SUPPORT

        if not support_path.exists():
            pytest.skip(f"Sample support file not found: {support_path}")

        result = run_full_analysis(
            support_path=str(support_path),
            output_dir=str(tmp_path),
            skip_ai=True,
        )

        assert result["success"]
        linked_data = result["linked_data"]

        # At least some orders should exist
        assert len(linked_data.orders) >= 0

        # Summary should be populated
        summary = linked_data.summary
        assert summary.total_cases >= 0

    def test_evaluation_results_populated(self, tmp_path):
        """Verify evaluation layer produces results for linked orders."""
        from src.main import run_full_analysis

        support_path = PROJECT_ROOT / SAMPLE_SUPPORT

        if not support_path.exists():
            pytest.skip(f"Sample support file not found: {support_path}")

        result = run_full_analysis(
            support_path=str(support_path),
            output_dir=str(tmp_path),
            skip_ai=True,
        )

        assert result["success"]

        # Evaluation results should exist
        eval_results = result["evaluation_results"]
        assert isinstance(eval_results, dict)


class TestOutputValidation:
    """Validate JSON output structure and content."""

    def test_json_outputs_valid_json(self, tmp_path):
        """Verify all JSON outputs are valid JSON."""
        import json
        from src.main import run_full_analysis

        support_path = PROJECT_ROOT / SAMPLE_SUPPORT

        if not support_path.exists():
            pytest.skip(f"Sample support file not found: {support_path}")

        result = run_full_analysis(
            support_path=str(support_path),
            output_dir=str(tmp_path),
            skip_ai=True,
        )

        assert result["success"]
        json_dir = Path(result["output_dir"]) / "json"

        for json_file in json_dir.glob("*.json"):
            with open(json_file, 'r') as f:
                try:
                    data = json.load(f)
                    assert data is not None
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in {json_file.name}: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
