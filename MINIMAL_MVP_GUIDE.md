# Minimal MVP Implementation Guide

This guide shows **exactly** what to build first to get a working prototype.

---

## Goal: Invoice Summary in 1 Week

Build the absolute minimum needed to run:
```bash
clawlite "Summarize all PDF invoices in this folder"
```

---

## Day 1-2: Core Infrastructure

### 1. Project Setup

```bash
cd tiny-agent
mkdir -p clawlite/tools tests/fixtures/invoices tests/expected_outputs
```

### 2. Create `pyproject.toml`

```toml
[project]
name = "clawlite"
version = "0.2.0"
description = "Tiny Agent for Local LLMs"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12.0",
    "rich>=13.0.0",
    "pydantic>=2.0.0",
    "httpx>=0.27.0",
    "pymupdf>=1.24.0",
]

[project.scripts]
clawlite = "clawlite.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Install:
```bash
pip install -e .
```

### 3. Create `clawlite/ollama_client.py`

```python
import httpx
import json

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", model="llama3.1:8b-instruct"):
        self.base_url = base_url
        self.model = model

    def generate(self, prompt: str, system: str = "", format="json") -> dict:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "format": format,
            "options": {
                "temperature": 0.1,
                "num_predict": 800
            }
        }

        response = httpx.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=120.0
        )
        response.raise_for_status()

        result = response.json()
        return json.loads(result["response"])
```

### 4. Create `clawlite/protocol.py` (JSON parser + repair)

```python
import json
import re

def parse_llm_output(text: str) -> dict:
    """Parse JSON output from LLM with repair attempts."""
    # Attempt 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parse error: {e}")

    # Attempt 2: Common repairs
    repaired = text.strip()

    # Fix single quotes to double quotes
    repaired = repaired.replace("'", '"')

    # Remove trailing commas
    repaired = re.sub(r',(\s*[}\]])', r'\1', repaired)

    # Add missing closing braces (simple heuristic)
    open_braces = repaired.count('{')
    close_braces = repaired.count('}')
    if open_braces > close_braces:
        repaired += '}' * (open_braces - close_braces)

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        raise ValueError(f"Could not repair JSON: {text[:200]}")
```

---

## Day 3-4: Basic Tools

### 5. Create `clawlite/tools/doc_open.py`

```python
from pathlib import Path
from typing import List, Dict, Any
import pymupdf as fitz

def doc_open(path: str, recursive: bool = False, file_types: List[str] = None) -> Dict[str, Any]:
    """Open document(s) and extract text."""
    path_obj = Path(path)
    file_types = file_types or ["pdf", "txt", "md"]

    # Single file
    if path_obj.is_file():
        text = extract_text_from_file(path_obj)
        return {
            "success": True,
            "files_processed": 1,
            "sources": [{"path": str(path_obj), "type": path_obj.suffix[1:], "chars": len(text)}],
            "combined_text": text[:8000],
            "metadata": {"total_files": 1, "total_chars": len(text)}
        }

    # Folder
    elif path_obj.is_dir():
        all_texts = []
        sources = []

        for ext in file_types:
            pattern = f"**/*.{ext}" if recursive else f"*.{ext}"
            for file in path_obj.glob(pattern):
                text = extract_text_from_file(file)
                all_texts.append(f"--- {file.name} ---\n{text}\n")
                sources.append({
                    "path": str(file),
                    "type": ext,
                    "chars": len(text),
                    "excerpt": text[:200]
                })

        combined = "\n".join(all_texts)
        return {
            "success": True,
            "files_processed": len(sources),
            "sources": sources,
            "combined_text": combined[:8000],
            "metadata": {
                "total_files": len(sources),
                "total_chars": len(combined)
            }
        }

    return {"success": False, "error": "Path not found"}

def extract_text_from_file(path: Path) -> str:
    """Extract text from PDF, TXT, or MD."""
    if path.suffix == ".pdf":
        doc = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    else:
        return path.read_text(encoding="utf-8")
```

### 6. Create `clawlite/tools/summarize.py`

```python
def summarize_stub(source: str, format: str = "structured") -> dict:
    """
    For MVP: This is just a stub that formats the LLM's response.
    The actual summarization happens in the orchestrator by sending
    the document text to the LLM with a summarization prompt.
    """
    return {
        "success": True,
        "summary": source,  # Will be replaced by LLM output
        "sources": [],
        "metadata": {}
    }
```

---

## Day 5-6: Orchestrator

### 7. Create `clawlite/orchestrator.py`

```python
from clawlite.ollama_client import OllamaClient
from clawlite.protocol import parse_llm_output
from clawlite.tools.doc_open import doc_open
from rich.live import Live
from rich.panel import Panel

SYSTEM_PROMPT = """You are a helpful assistant that uses tools.

OUTPUT FORMAT (JSON only):
{
  "action": "tool_name",
  "args": {"param": "value"}
}

OR for final answer:
{
  "action": "final",
  "result": "Your markdown answer"
}

TOOLS:
- doc_open: {"path": "file or folder", "recursive": false, "file_types": ["pdf", "txt", "md"]}
- final: Return final answer

EXAMPLE:
User: "Summarize all PDFs"
{"action": "doc_open", "args": {"path": ".", "file_types": ["pdf"]}}

[After getting documents]
{"action": "final", "result": "## Summary\\n- Point 1\\n- Point 2"}
"""

class Orchestrator:
    def __init__(self, model="llama3.1:8b-instruct", max_steps=20):
        self.client = OllamaClient(model=model)
        self.max_steps = max_steps
        self.context = []

    def run(self, user_input: str):
        with Live(Panel("🤔 Thinking..."), refresh_per_second=4) as live:
            for step in range(self.max_steps):
                live.update(Panel(f"Step {step+1}/{self.max_steps}: Processing...", title="🔄 Working"))

                # Build prompt
                prompt = self._build_prompt(user_input)

                # Call LLM
                try:
                    response = self.client.generate(prompt, system=SYSTEM_PROMPT)
                except Exception as e:
                    return f"❌ Error: {e}"

                action = response.get("action")

                # Final answer
                if action == "final":
                    return response.get("result", "Done")

                # Tool call
                elif action == "doc_open":
                    args = response.get("args", {})
                    result = doc_open(**args)
                    self.context.append({"action": "doc_open", "result": result})

                    # If this was a doc_open, next step is to summarize
                    # So we add the text to prompt and ask for summary
                    if result["success"]:
                        user_input = f"Summarize these documents:\n\n{result['combined_text'][:4000]}"

                else:
                    return f"❌ Unknown action: {action}"

            return "⚠️ Max steps reached"

    def _build_prompt(self, user_input: str) -> str:
        context_str = ""
        if self.context:
            context_str = f"\n\nPrevious actions:\n{self.context[-1]}"

        return f"{user_input}{context_str}"
```

---

## Day 7: CLI + Testing

### 8. Create `clawlite/__main__.py`

```python
import typer
from clawlite.orchestrator import Orchestrator
from rich.console import Console
from rich.markdown import Markdown

app = typer.Typer()
console = Console()

@app.command()
def main(
    task: str = typer.Argument(None, help="Task to perform"),
    model: str = typer.Option("llama3.1:8b-instruct", "--model", "-m"),
    max_steps: int = typer.Option(20, "--max-steps", "-s"),
):
    """ClawLite: AI assistant for local LLMs"""

    if not task:
        console.print("[yellow]Enter a task:[/yellow]")
        task = input("> ")

    orch = Orchestrator(model=model, max_steps=max_steps)
    result = orch.run(task)

    console.print("\n" + "="*60 + "\n")
    console.print(Markdown(result))

if __name__ == "__main__":
    app()
```

### 9. Copy Invoice Fixtures

```bash
# Copy the 5 invoice PDFs to tests/fixtures/invoices/
cp *.pdf tests/fixtures/invoices/
```

### 10. Test It!

```bash
# Make sure Ollama is running
ollama serve

# Pull model if needed
ollama pull llama3.1:8b-instruct

# Run the test
cd tests/fixtures/invoices
clawlite "Summarize all PDF invoices"
```

---

## What's Missing (Add Later)

These are **not** in the MVP:
- ❌ Write file tool
- ❌ Web search
- ❌ Action items extractor
- ❌ Meeting minutes
- ❌ Email drafts
- ❌ Calendar parsing
- ❌ Text extraction
- ❌ Expense reports
- ❌ Approval prompts (add in week 2)
- ❌ Workspace sandboxing (add in week 2)
- ❌ Full context state management (simplified for now)
- ❌ Token budget tracking (add when needed)
- ❌ Comprehensive error handling
- ❌ Tests (add after it works)

---

## Success Criteria for MVP

✅ **Milestone achieved when:**
1. Can run `clawlite "Summarize all PDFs in folder"`
2. Loads all 5 invoice PDFs
3. Generates a structured summary with:
   - Total amount
   - Contractor names
   - Date ranges
   - Sources listed
4. Output is readable markdown
5. Completes in < 2 minutes

**Don't worry about:**
- Perfect accuracy (aim for 70-80%)
- Beautiful formatting
- Edge cases
- Performance optimization

**Just get it working end-to-end first!**

---

## Next Steps After MVP

Once the basic invoice summary works:

**Week 2**: Add remaining tools (write_file, action_items, etc.)
**Week 3**: Add approval prompts and workspace sandboxing
**Week 4**: Add proper error handling and tests
**Week 5**: Polish and documentation

---

## Debugging Tips

**If LLM outputs garbage:**
- Check Ollama is running: `ollama list`
- Try a different model: `ollama pull deepseek-r1:8b`
- Add more examples to system prompt

**If JSON parsing fails:**
- Print raw LLM output before parsing
- Check the repair loop is catching common errors
- Reduce temperature to 0.0

**If it's too slow:**
- Use smaller context (truncate to 2000 chars instead of 8000)
- Reduce num_predict to 300
- Try haiku-speed models

**If summary is bad:**
- Add explicit instructions: "Focus on amounts, dates, names"
- Show an example summary in the system prompt
- Break into smaller steps (extract data first, then summarize)

---

**Good luck! Start with Day 1 and don't skip ahead.**
