"""
Progress tracking and reporting utilities using rich.
"""

from contextlib import contextmanager
from typing import Iterator

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

console = Console()


def create_progress_bar() -> Progress:
    """
    Create a rich Progress bar with custom formatting.

    Returns:
        Configured Progress instance
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )


@contextmanager
def track_progress(description: str, total: int | None = None) -> Iterator[Progress]:
    """
    Context manager for tracking progress with a progress bar.

    Usage:
        with track_progress("Processing files", total=10) as progress:
            task = progress.add_task("processing", total=10)
            for i in range(10):
                # do work
                progress.update(task, advance=1)

    Args:
        description: Description to show in progress bar
        total: Total number of steps (None for indeterminate progress)

    Yields:
        Progress instance
    """
    progress = create_progress_bar()
    with progress:
        yield progress


@contextmanager
def operation_status(operation: str) -> Iterator[None]:
    """
    Context manager to show operation status with timing.

    Usage:
        with operation_status("Importing file"):
            # do work
            pass

    Args:
        operation: Description of the operation

    Yields:
        None
    """
    console.print(f"[bold blue]{operation}...[/bold blue]")

    try:
        yield
        console.print(f"[green]✓ {operation} complete[/green]")
    except Exception as e:
        console.print(f"[red]✗ {operation} failed: {e}[/red]")
        raise


class ProgressTracker:
    """
    Progress tracker for multi-step operations.

    Tracks overall progress, timing, and can report statistics.
    """

    def __init__(self, operation_name: str):
        """
        Initialize progress tracker.

        Args:
            operation_name: Name of the operation being tracked
        """
        self.operation_name = operation_name
        self.steps_completed = 0
        self.steps_total = 0
        self.stats: dict[str, int | float] = {}

    def start(self, total_steps: int):
        """
        Start tracking with total number of steps.

        Args:
            total_steps: Total number of steps expected
        """
        self.steps_total = total_steps
        self.steps_completed = 0
        console.print(
            f"[bold blue]Starting {self.operation_name}[/bold blue] ({total_steps} steps)"
        )

    def step(self, step_name: str):
        """
        Record completion of a step.

        Args:
            step_name: Name of the completed step
        """
        self.steps_completed += 1
        progress_pct = (
            (self.steps_completed / self.steps_total * 100) if self.steps_total > 0 else 0
        )
        console.print(
            f"  [{self.steps_completed}/{self.steps_total}] "
            f"[dim]({progress_pct:.0f}%)[/dim] {step_name}"
        )

    def complete(self):
        """Mark operation as complete and show summary."""
        console.print(
            f"[green]✓ {self.operation_name} complete "
            f"({self.steps_completed}/{self.steps_total} steps)[/green]"
        )

        if self.stats:
            console.print("\n[bold]Statistics:[/bold]")
            for key, value in self.stats.items():
                console.print(f"  {key}: {value}")

    def add_stat(self, key: str, value: int | float):
        """
        Add a statistic to report.

        Args:
            key: Statistic name
            value: Statistic value
        """
        self.stats[key] = value


def show_summary(title: str, items: dict[str, str | int]):
    """
    Show a formatted summary box.

    Args:
        title: Summary title
        items: Dictionary of items to show (key: value pairs)
    """
    from rich.panel import Panel
    from rich.table import Table

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    for key, value in items.items():
        table.add_row(key, str(value))

    panel = Panel(table, title=f"[bold]{title}[/bold]", border_style="blue")
    console.print(panel)
