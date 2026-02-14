# clawlite

Terminal LLM Agent for Small Local Models (Ollama 8B-friendly)

## Overview

clawlite is a terminal-based agent that helps you:
- Open and read PDFs, text files, and markdown
- Summarize and compare documents
- Perform web searches and summarize results
- Generate office-friendly outputs (bullet summaries, action items, meeting minutes, email drafts)

**Key Design Principle**: Built for reliability with small local LLMs (7B-8B) using:
- Strict output formats (ACTION/FINAL blocks only)
- Single-step tool invocation per turn
- Schema validation + repair loop
- Transparent execution with user approval for risky operations

## Requirements

- Python 3.11+
- Ollama running locally with at least one model (default: `llama3.1:8b-instruct`)

## Installation

```bash
# Clone or create project directory
cd clawlite

# Install dependencies
pip install -e ".[dev]"

# Or install from pyproject.toml
pip install -r requirements.txt
```

## Usage

### Interactive Mode

```bash
clawlite
```

### Single-Shot Tasks

```bash
# Summarize a PDF
clawlite "Summarize ./docs/report.pdf"

# Compare two documents
clawlite "Compare ./doc1.txt and ./doc2.txt"

# Web search
clawlite "Search for Python best practices and summarize"

# Extract action items
clawlite "Extract action items from ./meeting_notes.txt"
```

### Options

```bash
clawlite [OPTIONS] [TASK]

Options:
  --workspace, -w PATH      Restrict scope to this directory
  --model, -m MODEL         Ollama model to use [default: llama3.1:8b-instruct]
  --approve, -a / --no-approve, -A   Ask before write/risky actions [default: True]
  --dry-run, -d             Show actions without executing
  --max-steps, -s INTEGER   Maximum steps before stopping [default: 20]
  --log, -l PATH           Save structured logs to JSONL file
  --no-web                 Disable web search tool
  --version, -v            Show version and exit
  --help                   Show this message and exit
```

## Tools

1. **doc_open** - Open PDF/TXT/MD files and extract text
2. **doc_compare** - Compare two documents (diff, summary, or semantic)
3. **web_search** - Search the web (DuckDuckGo, no API key needed)
4. **summarize** - Generate structured summaries
5. **write_file** - Write output to workspace
6. **action_items** - Extract action items, owners, and due dates
7. **meeting_minutes** - Generate structured meeting minutes
8. **email_draft** - Draft professional emails

## Architecture

### Core Loop: Propose → Validate → Execute → Observe

1. **LLM proposes** exactly one tool action OR outputs FINAL
2. **Orchestrator validates** output structure, tool allowlist, argument schema, policy checks
3. **Orchestrator executes** the tool (sandboxed, with approval)
4. **Tool result** is fed back to LLM in compact format
5. **Repeat** until FINAL

### Output Format

The LLM MUST output exactly one of:

**ACTION block:**
```
ACTION
tool: <tool_name>
args: <json_object>
END_ACTION
```

**FINAL block:**
```
FINAL
<final answer text in markdown>
END_FINAL
```

## Development

```bash
# Run tests
pytest

# Format code
black clawlite tests
ruff check clawlite tests
```

## Safety

- **Workspace sandbox**: If `--workspace` is set, all file operations are restricted to that directory
- **Approval required**: Write operations and web searches require user approval (unless `--no-approve`)
- **No arbitrary execution**: No shell command execution in MVP
- **Rate limiting**: Web searches are rate-limited
- **Output truncation**: All tool outputs are truncated before being returned to LLM

## License

MIT
