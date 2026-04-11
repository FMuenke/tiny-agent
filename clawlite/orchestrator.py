"""Main orchestrator for ClawLite agent."""

from typing import List, Dict, Any, Optional
from clawlite.ollama_client import OllamaClient
from clawlite.protocol import parse_llm_output, validate_action
from clawlite.tools.doc_open import doc_open
from rich.live import Live
from rich.panel import Panel
from rich.console import Console

console = Console()

# System prompt optimized for small models
SYSTEM_PROMPT = """You are a helpful assistant that uses tools to complete tasks.

CRITICAL: You MUST respond with valid JSON only. No other text.

OUTPUT FORMAT:
For tool actions:
{
  "action": "tool_name",
  "args": {"param": "value"},
  "reasoning": "brief explanation"
}

For final answer:
{
  "action": "final",
  "result": "Your markdown-formatted answer here"
}

AVAILABLE TOOLS:

1. doc_open - Open and extract text from files or folders
   Args: {"path": "file or folder path", "recursive": false, "file_types": ["pdf", "txt", "md"]}
   Returns: Combined text from all documents

2. final - Return final answer to user
   Args: None, just set "action": "final" and "result": "your answer"

WORKFLOW FOR DOCUMENT SUMMARIZATION:
1. If user asks to summarize documents, use doc_open to load them
2. After receiving document text, analyze it and return summary using "final" action
3. Include sources/filenames in your summary

EXAMPLE 1:
User: "Summarize all PDF invoices in this folder"
Response:
{
  "action": "doc_open",
  "args": {"path": ".", "file_types": ["pdf"]},
  "reasoning": "Load all PDF files first"
}

[After receiving document text with 5 invoices]
Response:
{
  "action": "final",
  "result": "## Invoice Summary\\n\\n**Total**: €6,500\\n**Period**: Nov 2025 - Jan 2026\\n\\n### Breakdown:\\n- Invoice 1: €1,000\\n- Invoice 2: €2,500\\n\\n### Sources:\\n- invoice1.pdf\\n- invoice2.pdf",
  "reasoning": "Analyzed all documents and prepared comprehensive summary"
}

EXAMPLE 2:
User: "Read report.pdf and tell me the key points"
Response:
{
  "action": "doc_open",
  "args": {"path": "report.pdf"},
  "reasoning": "Load the report file"
}

[After receiving text]
Response:
{
  "action": "final",
  "result": "## Key Points from report.pdf\\n\\n1. Point one\\n2. Point two\\n3. Point three"
}

CRITICAL RULES:
- You MUST respond with {"action": "...", ...} format
- If you need to read files: {"action": "doc_open", "args": {...}}
- After receiving document content: {"action": "final", "result": "markdown text here"}
- For invoice summaries: include totals, dates, breakdown by person/month, and sources
- The "result" field must contain clean markdown text (not nested JSON)
- NEVER output {"summary": ...} - always use {"action": "final", "result": "..."}
- Keep reasoning brief (one sentence)
"""


class Orchestrator:
    """Main control loop for the agent."""

    def __init__(
        self,
        model: str = "llama3.1:8b",
        max_steps: int = 20,
        base_url: str = "http://localhost:11434",
    ):
        self.client = OllamaClient(base_url=base_url, model=model)
        self.max_steps = max_steps
        self.history: List[Dict[str, Any]] = []
        self.model = model

    def run(self, user_input: str) -> str:
        """
        Run the orchestrator with the given user input.

        Args:
            user_input: User's task/question

        Returns:
            Final result as markdown string
        """
        # Check Ollama health first
        if not self.client.check_health():
            return (
                f"❌ **Error**: Cannot connect to Ollama or model '{self.model}' not found.\n\n"
                f"Please ensure:\n"
                f"1. Ollama is running: `ollama serve`\n"
                f"2. Model is installed: `ollama pull {self.model}`"
            )

        with Live(
            Panel("🤔 Thinking...", title="ClawLite", border_style="blue"),
            refresh_per_second=4,
        ) as live:
            try:
                for step in range(1, self.max_steps + 1):
                    live.update(
                        Panel(
                            f"Step {step}/{self.max_steps}\n\n🤔 Processing...",
                            title="ClawLite",
                            border_style="blue",
                        )
                    )

                    # Build prompt with context
                    prompt = self._build_prompt(user_input)

                    # Call LLM
                    live.update(
                        Panel(
                            f"Step {step}/{self.max_steps}\n\n🧠 Calling LLM...",
                            title="ClawLite",
                            border_style="yellow",
                        )
                    )

                    try:
                        response = self.client.generate(
                            prompt=prompt,
                            system=SYSTEM_PROMPT,
                            format="json",
                            temperature=0.1,
                            max_tokens=1500,  # Increased for comprehensive summaries
                        )
                    except Exception as e:
                        return f"❌ **LLM Error**: {str(e)}"

                    # Validate response
                    if not validate_action(response):
                        return (
                            f"❌ **Invalid LLM Response**\n\n"
                            f"Expected JSON with 'action' and 'args' or 'result'.\n"
                            f"Got: {response}"
                        )

                    action = response.get("action")
                    reasoning = response.get("reasoning", "")

                    # Handle final action
                    if action == "final":
                        result = response.get("result", "")
                        return result

                    # Handle tool actions
                    elif action == "doc_open":
                        live.update(
                            Panel(
                                f"Step {step}/{self.max_steps}\n\n🔍 Opening documents...\n{reasoning}",
                                title="ClawLite",
                                border_style="green",
                            )
                        )

                        args = response.get("args", {})
                        tool_result = doc_open(**args)

                        # Add to history
                        self.history.append(
                            {
                                "action": "doc_open",
                                "args": args,
                                "result": tool_result,
                            }
                        )

                        if not tool_result.get("success"):
                            error = tool_result.get("error", "Unknown error")
                            return f"❌ **Error opening documents**: {error}"

                        # Update user input to include document text for next iteration
                        files_count = tool_result["files_processed"]
                        combined_text = tool_result["combined_text"]
                        sources = [s["name"] for s in tool_result["sources"]]

                        user_input = (
                            f"Documents loaded successfully.\n\n"
                            f"Files: {files_count}\n"
                            f"Sources: {', '.join(sources)}\n\n"
                            f"Content:\n{combined_text}\n\n"
                            f"Original request: {user_input}\n\n"
                            f"Now provide your final summary."
                        )

                        live.update(
                            Panel(
                                f"Step {step}/{self.max_steps}\n\n"
                                f"✅ Loaded {files_count} documents\n"
                                f"📄 {', '.join(sources[:3])}{'...' if len(sources) > 3 else ''}",
                                title="ClawLite",
                                border_style="green",
                            )
                        )

                    else:
                        return f"❌ **Unknown action**: {action}\n\nAvailable: doc_open, final"

                return f"⚠️ **Max steps reached** ({self.max_steps})\n\nTask incomplete."

            except KeyboardInterrupt:
                return "\n\n⏸️ **Interrupted by user**"
            except Exception as e:
                return f"❌ **Unexpected error**: {str(e)}"

    def _build_prompt(self, user_input: str) -> str:
        """Build prompt with context from history."""
        if not self.history:
            return user_input

        # Include last action in prompt for context
        last_action = self.history[-1]
        context = (
            f"\n\nPrevious action: {last_action['action']}\n"
            f"Status: {'Success' if last_action['result'].get('success') else 'Failed'}"
        )

        return f"{user_input}{context}"
