"""CLI entry point for ClawLite.

Usage:
    clawlite "task"                 → agent on a task (shorthand for `clawlite run`)
    clawlite run "task"             → same, explicit form
    clawlite feeds <action> ...     → RSS feed subcommands
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from clawlite import feeds as feed_module
from clawlite.ollama_client import OllamaClient
from clawlite.orchestrator import Orchestrator

console = Console()

app = typer.Typer(
    help="ClawLite: Tiny Agent for Local LLMs",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
feeds_app = typer.Typer(help="Manage RSS feed subscriptions and digests.")
app.add_typer(feeds_app, name="feeds")


# ---------- agent task (run) ----------

@app.command("run")
def run_task(
    task: str = typer.Argument(..., help="Task for the agent"),
    model: str = typer.Option("gemma4:e4b", "--model", "-m"),
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w"),
    max_steps: int = typer.Option(20, "--max-steps", "-s"),
    base_url: str = typer.Option("http://localhost:11434", "--base-url"),
):
    """Run the agent on a task."""
    if workspace:
        wp = Path(workspace)
        if not wp.exists():
            console.print(f"[red]❌ Workspace not found: {workspace}[/red]")
            raise typer.Exit(1)
        os.chdir(wp)
        console.print(f"[dim]📁 Working directory: {wp.absolute()}[/dim]\n")

    console.print()
    console.print(Panel(f"[bold]{task}[/bold]", title="🎯 Task", border_style="cyan"))
    console.print()

    result = Orchestrator(model=model, max_steps=max_steps, base_url=base_url).run(task)

    console.print("\n" + "=" * 70 + "\n")
    console.print(Markdown(result))
    console.print("\n" + "=" * 70 + "\n")


# ---------- feeds subcommands ----------

@feeds_app.command("add")
def feeds_add(url: str):
    """Subscribe to an RSS/Atom feed."""
    result = feed_module.add_subscription(url)
    if result["status"] == "exists":
        console.print(f"[yellow]Already subscribed:[/yellow] {result['feed']['title']}")
    else:
        f = result["feed"]
        console.print(f"[green]✅ Added[/green] [bold]{f['title']}[/bold]")
        console.print(f"    [dim]{f['url']} → slug: {f['slug']}[/dim]")
        if result.get("warning"):
            console.print(f"    [yellow]⚠ discovery warning: {result['warning']}[/yellow]")


@feeds_app.command("list")
def feeds_list():
    """Show current subscriptions."""
    feeds = feed_module.list_subscriptions()
    if not feeds:
        console.print("[dim]No subscriptions. Add one with `clawlite feeds add <url>`.[/dim]")
        return
    console.print(f"[bold]{len(feeds)} subscription(s):[/bold]")
    for f in feeds:
        console.print(f"  • [bold]{f['title']}[/bold]")
        console.print(f"    [dim]{f['url']}[/dim]")


@feeds_app.command("remove")
def feeds_remove(url: str):
    """Unsubscribe from a feed."""
    r = feed_module.remove_subscription(url)
    if r["status"] == "removed":
        console.print(f"[green]Removed:[/green] {url}")
    else:
        console.print(f"[yellow]Not subscribed:[/yellow] {url}")


@feeds_app.command("fetch")
def feeds_fetch():
    """Pull new items for every subscription (no summarization)."""
    results = feed_module.fetch_all()
    if not results:
        console.print("[dim]No subscriptions.[/dim]")
        return
    for slug, count in results.items():
        if isinstance(count, int):
            style = "green" if count > 0 else "dim"
            console.print(f"  [{style}]{slug}: {count} new[/{style}]")
        else:
            console.print(f"  [red]{slug}: {count}[/red]")


DIGEST_SYSTEM = (
    "You summarize RSS feed items into a concise markdown digest.\n"
    "Respond with ONLY a JSON object: {\"digest\": \"markdown text\"}\n"
    "Use bullet points: - [title](link) — short take.\n"
    "Keep each bullet to ONE short sentence. Be very concise."
)

BATCH_SIZE = 10


def _digest_one_feed(client, feed_path) -> tuple[str, str]:
    """Read a single JSONL feed file and ask the LLM to digest it.

    Processes items in batches to avoid token-limit truncation.
    Returns (feed_title, digest_markdown). digest_markdown is empty on
    skip, or starts with '*Error' on failure.
    """
    content = feed_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not content:
        return (feed_path.stem, "")

    # Parse JSONL and extract only title + link to keep the prompt lean.
    items = []
    feed_title = feed_path.stem
    for line in content.splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not feed_title or feed_title == feed_path.stem:
            feed_title = obj.get("feed_title", feed_path.stem)
        title = obj.get("title", "").strip()
        link = obj.get("link", "").strip()
        if title:
            items.append(f"- {title}  {link}")

    if not items:
        return (feed_title, "")

    # Process in batches to stay within token limits.
    digest_parts = []
    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i : i + BATCH_SIZE]
        item_list = "\n".join(batch)

        prompt = (
            f"Digest these {len(batch)} items from \"{feed_title}\".\n"
            f"For each: - [title](link) — one short sentence.\n\n"
            f"{item_list}"
        )

        try:
            response = client.generate(
                prompt=prompt,
                system=DIGEST_SYSTEM,
                format="json",
                temperature=0.1,
                max_tokens=1500,
            )
            part = response.get("digest", "")
            if part:
                digest_parts.append(part)
        except Exception as e:
            digest_parts.append(f"*Error on batch {i // BATCH_SIZE + 1}: {e}*")

    return (feed_title, "\n".join(digest_parts))


@feeds_app.command("digest")
def feeds_digest(
    keep: bool = typer.Option(False, "--keep", help="Don't clear feed files after the digest."),
    model: str = typer.Option("gemma4:e4b", "--model", "-m"),
    base_url: str = typer.Option("http://localhost:11434", "--base-url"),
):
    """Fetch → LLM summarizes each feed → print digest → clear inbox (unless --keep)."""
    console.print("[dim]Fetching feeds...[/dim]")
    fetch_results = feed_module.fetch_all()
    new_total = sum(v for v in fetch_results.values() if isinstance(v, int))
    for slug, v in fetch_results.items():
        if isinstance(v, str):
            console.print(f"  [red]{slug}: {v}[/red]")

    files = feed_module.inbox_files()
    if not files:
        console.print("[dim]Inbox is empty — nothing to digest.[/dim]")
        return

    console.print(
        f"[dim]Inbox: {len(files)} feed file(s), {new_total} new item(s) this fetch.[/dim]\n"
    )

    client = OllamaClient(base_url=base_url, model=model)
    if not client.check_health():
        console.print(
            f"[red]Cannot reach Ollama or model `{model}` missing.[/red]\n"
            f"1. `ollama serve`  2. `ollama pull {model}`"
        )
        return

    any_ok = False
    all_failed = True
    for f in files:
        console.print(f"\n[dim]  Digesting {f.stem}...[/dim]")
        feed_title, digest_text = _digest_one_feed(client, f)

        if not digest_text:
            console.print(f"  [dim]{feed_title}: empty, skipped.[/dim]")
            continue

        is_error = digest_text.startswith("*Error")
        if is_error:
            console.print(f"  [red]{feed_title}: {digest_text}[/red]")
        else:
            all_failed = False
            any_ok = True
            section = f"## {feed_title}\n\n{digest_text}"
            console.print()
            console.print(Markdown(section))
            console.print()

    if not any_ok:
        console.print("[dim]No digest content produced.[/dim]")

    if keep:
        console.print("[yellow dim]--keep set; feed inbox retained.[/yellow dim]")
    elif all_failed:
        console.print("[yellow]Digest looks failed; feed inbox retained so you can retry.[/yellow]")
    else:
        cleared = feed_module.clear_inbox()
        console.print(f"\n[dim]Cleared {len(cleared)} feed file(s).[/dim]")


# ---------- entry point ----------

_KNOWN_SUBCOMMANDS = {"run", "feeds"}
_HELP_FLAGS = {"--help", "-h", "--install-completion", "--show-completion"}


def cli():
    """
    Entry point. Preserves `clawlite "task"` as shorthand for `clawlite run "task"`
    by prepending `run` to argv when the first positional looks like a task.
    """
    argv = sys.argv
    if len(argv) >= 2:
        first = argv[1]
        if (
            first not in _KNOWN_SUBCOMMANDS
            and not first.startswith("-")
            and first not in _HELP_FLAGS
        ):
            sys.argv = [argv[0], "run", *argv[1:]]
    app()


if __name__ == "__main__":
    cli()
