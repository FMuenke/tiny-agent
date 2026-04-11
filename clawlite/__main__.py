"""CLI entry point for ClawLite."""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from clawlite.orchestrator import Orchestrator

console = Console()


def main(
    task: str,
    model: str = "llama3.1:8b",
    workspace: Optional[str] = None,
    max_steps: int = 20,
    base_url: str = "http://localhost:11434",
):
    """
    ClawLite: Tiny Agent for Local LLMs

    Args:
        task: Task to perform (e.g., 'Summarize all PDFs')
        model: Ollama model to use (default: llama3.1:8b)
        workspace: Working directory (default: current directory)
        max_steps: Maximum steps before stopping (default: 20)
        base_url: Ollama API base URL (default: http://localhost:11434)

    Examples:

        clawlite "Summarize all PDF invoices"

        clawlite "Summarize reports" --model deepseek-r1:8b

        clawlite "Quick summary" --model llama3.2:3b
    """
    # Change to workspace if specified
    if workspace:
        workspace_path = Path(workspace)
        if not workspace_path.exists():
            console.print(f"[red]❌ Workspace not found: {workspace}[/red]")
            raise typer.Exit(1)
        import os
        os.chdir(workspace_path)
        console.print(f"[dim]📁 Working directory: {workspace_path.absolute()}[/dim]\n")

    # Show what we're doing
    console.print()
    console.print(
        Panel(
            f"[bold]{task}[/bold]",
            title="🎯 Task",
            border_style="cyan",
        )
    )
    console.print()

    # Run orchestrator
    orch = Orchestrator(
        model=model,
        max_steps=max_steps,
        base_url=base_url,
    )

    result = orch.run(task)

    # Display result
    console.print("\n" + "=" * 70 + "\n")
    console.print(Markdown(result))
    console.print("\n" + "=" * 70 + "\n")


def cli():
    """Entry point for the CLI."""
    typer.run(main)


if __name__ == "__main__":
    cli()
