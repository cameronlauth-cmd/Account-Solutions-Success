"""
Command-line interface for TrueNAS Sentiment Analysis.

Usage:
    python -m src.cli analyze input/salesforce_export.xlsx
    python -m src.cli analyze input/export.xlsx --output custom_output/
    python -m src.cli analyze input/export.xlsx --skip-sonnet  # Faster, cheaper
"""

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

from .core import Config
from .main import run_analysis, run_full_analysis


console = Console()


@click.group()
def cli():
    """TrueNAS Customer Sentiment Analysis CLI."""
    pass


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', default=None, help='Output directory (default: outputs/)')
@click.option('--skip-sonnet', is_flag=True, help='Skip Claude Sonnet analysis (faster, cheaper)')
def analyze(input_file: str, output: str, skip_sonnet: bool):
    """
    Run sentiment analysis on an Excel file.

    INPUT_FILE: Path to Excel file with case data (Salesforce export)

    Example:
        python -m src.cli analyze input/customer_cases.xlsx
    """
    input_path = Path(input_file)

    if not input_path.suffix.lower() in ['.xlsx', '.xls']:
        console.print(f"[red]Error: Input file must be an Excel file (.xlsx or .xls)[/red]")
        sys.exit(1)

    console.print(f"[dim]Input file: {input_path}[/dim]")
    console.print(f"[dim]Output directory: {output or 'outputs/'}[/dim]")
    if skip_sonnet:
        console.print(f"[yellow]Skipping Claude Sonnet analysis (--skip-sonnet)[/yellow]")
    console.print()

    try:
        result = run_analysis(
            input_file=str(input_path),
            output_dir=output,
            skip_sonnet=skip_sonnet,
        )

        if result["success"]:
            console.print()
            console.print(f"[green bold]Success![/green bold]")
            console.print(f"  Customer: {result['customer_name']}")
            console.print(f"  Health Score: {result['health_score']:.0f}/100")
            console.print(f"  Total Cases: {result['total_cases']}")
            console.print(f"  Critical Cases: {result['critical_cases']}")
            console.print(f"  Analysis Time: {result['analysis_time']:.1f}s")
            console.print()
            console.print(f"[dim]Output saved to: {result['output_dir']}[/dim]")
        else:
            console.print(f"[red]Analysis failed: {result.get('error', 'Unknown error')}[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


@cli.command('analyze-full')
@click.option('--opportunities', '-o', default=None, help='Path to Opportunities Excel file (glob pattern allowed)')
@click.option('--deployments', '-d', default=None, help='Path to Deployments Excel file (glob pattern allowed)')
@click.option('--support', '-s', default=None, help='Path to Support Cases Excel file (glob pattern allowed)')
@click.option('--output', default=None, help='Output directory (default: outputs/)')
@click.option('--quick', is_flag=True, help='Skip all AI analysis (fastest, for testing)')
@click.option('--skip-sonnet', is_flag=True, help='Skip Sonnet analysis (faster, cheaper)')
def analyze_full(opportunities: str, deployments: str, support: str, output: str, quick: bool, skip_sonnet: bool):
    """
    Run full 4-layer analysis across all data sources.

    This command orchestrates the complete analysis pipeline:
    - Load Opportunities, Deployments, and Support Cases
    - Link data via Order Number
    - Run 4-layer AI analysis
    - Calculate multi-dimensional metrics
    - Generate JSON outputs

    Example:
        python -m src.cli analyze-full \\
            --opportunities "input/Ai Opportunities*.xlsx" \\
            --deployments "input/PS Deploy*.xlsx" \\
            --support "input/Account AI Email Body*.xlsx"

    Quick test mode (no AI):
        python -m src.cli analyze-full --quick \\
            --support "input/cases.xlsx"
    """
    # Validate that at least one source is provided
    if not opportunities and not deployments and not support:
        console.print("[red]Error: At least one data source must be provided[/red]")
        console.print("[dim]Use --opportunities, --deployments, or --support[/dim]")
        sys.exit(1)

    console.print(f"[bold]Account Solutions Full Analysis[/bold]")
    console.print()
    console.print("[dim]Data Sources:[/dim]")
    console.print(f"  Opportunities: {opportunities or 'Not provided'}")
    console.print(f"  Deployments: {deployments or 'Not provided'}")
    console.print(f"  Support Cases: {support or 'Not provided'}")
    console.print(f"[dim]Output directory: {output or 'outputs/'}[/dim]")
    if quick:
        console.print(f"[yellow]Quick mode: Skipping all AI analysis[/yellow]")
    elif skip_sonnet:
        console.print(f"[yellow]Skipping Claude Sonnet analysis (--skip-sonnet)[/yellow]")
    console.print()

    try:
        result = run_full_analysis(
            opportunities_path=opportunities,
            deployments_path=deployments,
            support_path=support,
            output_dir=output,
            skip_ai=quick,
            skip_sonnet=skip_sonnet,
        )

        if result["success"]:
            console.print()
            console.print(f"[green bold]Success![/green bold]")
            console.print(f"  Opportunities Analyzed: {result['opportunities_analyzed']}")
            console.print(f"  Deployments Analyzed: {result['deployments_analyzed']}")
            console.print(f"  Support Cases Analyzed: {result['cases_analyzed']}")
            console.print(f"  Orders Linked: {result['linked_orders']}")
            console.print(f"  Fully Linked Orders: {result['fully_linked_orders']}")
            console.print(f"  Analysis Time: {result['analysis_time']:.1f}s")
            console.print()
            console.print(f"[dim]Output saved to: {result['output_dir']}[/dim]")
        else:
            console.print(f"[red]Analysis failed: {result.get('error', 'Unknown error')}[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


@cli.command()
def check():
    """Check configuration and dependencies."""
    console.print("[bold]Checking configuration...[/bold]")
    console.print()

    errors = Config.validate()

    if errors:
        console.print("[red]Configuration errors found:[/red]")
        for error in errors:
            console.print(f"  [red]- {error}[/red]")
        sys.exit(1)
    else:
        console.print("[green]Configuration OK[/green]")

    # Check for logo
    logo_path = Config.get_logo_path()
    if logo_path:
        console.print(f"[green]Logo found: {logo_path}[/green]")
    else:
        console.print("[yellow]Logo not found (will use text header)[/yellow]")

    # Check directories
    console.print()
    console.print("[bold]Directories:[/bold]")
    console.print(f"  Input: {Config.INPUT_DIR}")
    console.print(f"  Output: {Config.OUTPUT_DIR}")
    console.print(f"  Assets: {Config.ASSETS_DIR}")

    console.print()
    console.print("[green]All checks passed![/green]")


@cli.command()
def version():
    """Show version information."""
    from .core import LOCAL_VERSION, PART1_VERSION, PART2_VERSION, PART3_VERSION, PART4_VERSION, PART5_VERSION

    console.print("[bold]TrueNAS Sentiment Analysis[/bold]")
    console.print(f"  Local Version: {LOCAL_VERSION}")
    console.print()
    console.print("[dim]Original Abacus AI components:[/dim]")
    console.print(f"  Part 1 (Core): {PART1_VERSION}")
    console.print(f"  Part 2 (Sonnet): {PART2_VERSION}")
    console.print(f"  Part 3 (Viz): {PART3_VERSION}")
    console.print(f"  Part 4 (PDF): {PART4_VERSION}")
    console.print(f"  Part 5 (Orchestration): {PART5_VERSION}")


@cli.command()
@click.option('--port', '-p', default=8501, help='Port to run dashboard on')
@click.option('--folder', '-f', default=None, help='Specific analysis folder to load')
def dashboard(port: int, folder: str):
    """
    Launch interactive dashboard for exploring analysis results.

    Opens a web browser with the Streamlit dashboard where you can:
    - View health scores and key metrics
    - Browse cases with drill-down details
    - Explore interaction timelines
    - Export to PDF or HTML

    Example:
        python -m src.cli dashboard
        python -m src.cli dashboard --port 8502
    """
    import webbrowser
    from threading import Timer

    dashboard_path = Path(__file__).parent / "dashboard" / "app.py"

    if not dashboard_path.exists():
        console.print("[red]Error: Dashboard not found at {dashboard_path}[/red]")
        sys.exit(1)

    console.print("[bold]Launching TrueNAS Sentiment Analysis Dashboard[/bold]")
    console.print(f"[dim]URL: http://localhost:{port}[/dim]")
    console.print()
    console.print("[dim]Press Ctrl+C to stop the dashboard[/dim]")
    console.print()

    # Open browser after a short delay
    def open_browser():
        webbrowser.open(f"http://localhost:{port}")

    Timer(2.0, open_browser).start()

    # Run streamlit
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(dashboard_path),
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard stopped[/yellow]")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
