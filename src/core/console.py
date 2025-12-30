"""
Rich console output for TrueNAS Sentiment Analysis.
Replaces Abacus AI's client.stream_message() with beautiful terminal output.
"""

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from typing import Optional
import sys


# Global console instance
console = Console()


def print_header(title: str, subtitle: Optional[str] = None) -> None:
    """Print a styled header."""
    console.print()
    console.print(Panel(
        f"[bold blue]{title}[/bold blue]" + (f"\n[dim]{subtitle}[/dim]" if subtitle else ""),
        border_style="blue"
    ))
    console.print()


def print_stage(stage_num: int, title: str, description: str = "") -> None:
    """Print a stage header."""
    console.print()
    console.print(f"[bold cyan]{'='*70}[/bold cyan]")
    console.print(f"[bold white]STAGE {stage_num}: {title}[/bold white]")
    if description:
        console.print(f"[dim]{description}[/dim]")
    console.print(f"[bold cyan]{'='*70}[/bold cyan]")
    console.print()


def print_progress(message: str, style: str = "dim") -> None:
    """Print a progress message."""
    console.print(f"[{style}]{message}[/{style}]")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]{message}[/green]")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]{message}[/yellow]")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]{message}[/bold red]")


def print_metric(label: str, value: str, style: str = "white") -> None:
    """Print a labeled metric."""
    console.print(f"  [dim]{label}:[/dim] [{style}]{value}[/{style}]")


def print_divider(char: str = "=", width: int = 70) -> None:
    """Print a divider line."""
    console.print(f"[dim]{char * width}[/dim]")


def print_case_progress(current: int, total: int, case_num: int) -> None:
    """Print case analysis progress."""
    pct = (current / total) * 100
    console.print(f"[dim][{current}/{total}] ({pct:.1f}%) Analyzing case #{case_num}...[/dim]")


def create_progress_bar(description: str = "Processing") -> Progress:
    """Create a rich progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    )


def print_summary_table(metrics: dict) -> None:
    """Print a summary table of metrics."""
    table = Table(title="Analysis Summary", border_style="blue")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    for key, value in metrics.items():
        table.add_row(key, str(value))

    console.print(table)


def print_health_score(score: float, customer_name: str) -> None:
    """Print the account health score with color coding."""
    if score >= 85:
        color = "green"
        status = "Healthy - Low Risk"
    elif score >= 70:
        color = "yellow"
        status = "Stable - Minor Concerns"
    elif score >= 60:
        color = "orange3"
        status = "At Risk - Moderate Concerns"
    else:
        color = "red"
        status = "Critical - High Renewal Risk"

    console.print()
    console.print(Panel(
        f"[bold]Account:[/bold] {customer_name}\n"
        f"[bold]Health Score:[/bold] [{color}]{score:.0f}/100[/{color}]\n"
        f"[bold]Status:[/bold] [{color}]{status}[/{color}]",
        title="Account Health Assessment",
        border_style=color
    ))
    console.print()


class StreamingOutput:
    """
    Compatibility class that mimics Abacus AI's client.stream_message().
    Can be passed to functions that expect a client object with stream_message method.
    """

    def stream_message(self, message: str) -> None:
        """Stream a message to console (compatibility with Abacus API)."""
        # Remove trailing newlines for cleaner output
        message = message.rstrip('\n')
        if message:
            console.print(message)

    def print(self, message: str) -> None:
        """Alias for stream_message."""
        self.stream_message(message)


# Global streaming output instance for compatibility
streaming_output = StreamingOutput()


class StreamlitStreamingOutput:
    """
    Captures progress messages for Streamlit UI display.
    Can be used as a drop-in replacement for StreamingOutput when running
    analysis from within the Streamlit dashboard.
    """

    def __init__(self):
        self.messages = []
        self.current_stage = 0
        self.total_stages = 9

    def stream_message(self, message: str) -> None:
        """Capture message for Streamlit display."""
        message = message.rstrip('\n')
        if message:
            self.messages.append(message)

    def print(self, message: str) -> None:
        """Alias for stream_message."""
        self.stream_message(message)

    def get_messages(self) -> list:
        """Get all captured messages."""
        return self.messages

    def get_recent_messages(self, count: int = 15) -> list:
        """Get the most recent messages."""
        return self.messages[-count:]

    def clear(self) -> None:
        """Clear all captured messages."""
        self.messages = []
        self.current_stage = 0
