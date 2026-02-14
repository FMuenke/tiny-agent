"""CLI entry point for clawlite."""

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from clawlite.orchestrator import Orchestrator

app = typer.Typer(
    name="clawlite",
    help="Terminal LLM Agent for Small Local Models",
    rich_markup_mode="rich",
)
console = Console()


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        console.print("[bold blue]clawlite[/bold blue] version 0.1.0")
        raise typer.Exit()


@app.command()
def main(
    task: Optional[str] = typer.Argument(
        None,
        help="Task to execute (optional - runs interactive mode if not provided)",
    ),
    workspace: str = typer.Option(
        "",
        "--workspace",
        "-w",
        help="Restrict read/write/search scope to this directory",
    ),
    model: str = typer.Option(
        "llama3.1:8b-instruct",
        "--model",
        "-m",
        help="Ollama model to use",
    ),
    approve: bool = typer.Option(
        True,
        "--approve/--no-approve",
        "-a/-A",
        help="Ask before write or risky actions",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Show actions but do not execute",
    ),
    max_steps: int = typer.Option(
        20,
        "--max-steps",
        "-s",
        help="Maximum steps before stopping",
    ),
    log: Optional[str] = typer.Option(
        None,
        "--log",
        "-l",
        help="Save structured logs to JSONL file",
    ),
    no_web: bool = typer.Option(
        False,
        "--no-web",
        help="Disable web search tool",
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
    """
    Terminal LLM Agent for Small Local Models (Ollama 8B-friendly)

    [bold]Examples:[/bold]

    # Interactive session
    $ clawlite

    # Single-shot task
    $ clawlite "Summarize ./report.pdf"

    # With specific model
    $ clawlite --model llama3.2 "Compare doc1.txt and doc2.txt"

    # Restrict to workspace
    $ clawlite --workspace ~/documents "Open and summarize notes.txt"

    # Dry run (see what it would do)
    $ clawlite --dry-run "Write a summary to output.md"
    """
    # Print banner
    console.print(Panel(
        Text("clawlite", style="bold blue") + Text(" — Terminal LLM Agent", style="dim"),
        border_style="blue",
    ))
    
    # Check Ollama
    console.print("[dim]Checking Ollama...[/dim]")
    from clawlite.ollama_client import OllamaClient
    client = OllamaClient(model=model)
    
    if not client.is_healthy():
        console.print("[red]✗ Cannot connect to Ollama[/red]")
        console.print("[dim]Make sure Ollama is running: ollama serve[/dim]")
        sys.exit(1)
    
    console.print(f"[green]✓ Connected to Ollama ({model})[/green]\n")
    client.close()
    
    # Create orchestrator
    orch = Orchestrator(
        model=model,
        workspace=workspace,
        approve=approve,
        dry_run=dry_run,
        max_steps=max_steps,
        web_enabled=not no_web,
        log_path=log or "",
        console=console,
    )
    
    try:
        if task:
            # Single-shot mode
            orch.run(task)
        else:
            # Interactive mode
            console.print("[bold]Interactive mode[/bold] (type 'quit' or 'exit' to stop)\n")
            
            while True:
                try:
                    user_input = console.input("[bold green]>[/bold green] ")
                    
                    if user_input.lower() in ("quit", "exit", "q"):
                        console.print("[dim]Goodbye![/dim]")
                        break
                    
                    if not user_input.strip():
                        continue
                    
                    orch.run(user_input)
                    console.print()
                    
                except KeyboardInterrupt:
                    console.print("\n[dim]Interrupted. Type 'quit' to exit.[/dim]")
                    continue
                except EOFError:
                    break
    
    finally:
        orch.close()


if __name__ == "__main__":
    app()
