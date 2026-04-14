"""Executor — runs the selected skills in a tool loop.

Sees only the full descriptions of the skills the broker selected, so its
context stays small even as the overall skill catalog grows.
"""

from typing import Callable, List, Optional

from rich.panel import Panel

from clawlite.config import MEMORY_DIR
from clawlite.ollama_client import OllamaClient
from clawlite.skills import SKILLS, descriptions

EXECUTOR_PROMPT = """You execute a task using ONLY the skills listed below.
Respond with JSON only.

OUTPUT FORMAT:
For a skill call:
{{"action": "<skill_name>", "args": {{...}}, "reasoning": "brief"}}

For the final answer:
{{"action": "final", "result": "markdown answer"}}

MEMORY FOLDER: {memory_dir}
Bare filenames resolve inside the memory folder.

AVAILABLE SKILLS:

{skills}

RULES:
- Pick the next single step. Do not plan many steps in one response.
- After a skill returns data, analyse it and emit "final" with the answer.
- Never call a skill that isn't in the list above.
- Keep "reasoning" to one short sentence.
"""


class Executor:
    def __init__(self, client: OllamaClient, max_steps: int = 10):
        self.client = client
        self.max_steps = max_steps

    def run(
        self,
        intent: str,
        skill_names: List[str],
        status: Optional[Callable[[str, str], None]] = None,
    ) -> str:
        """
        Args:
            intent: Task description from the ChatAgent.
            skill_names: Skill IDs chosen by the broker.
            status: Optional callback (stage, detail) → None for UI updates.
        """
        if not skill_names:
            return "❌ **No skills selected** — the task could not be routed."

        system = EXECUTOR_PROMPT.format(
            memory_dir=MEMORY_DIR,
            skills=descriptions(skill_names),
        )

        prompt = intent

        for step in range(1, self.max_steps + 1):
            if status:
                status("thinking", f"Step {step}/{self.max_steps}")

            try:
                response = self.client.generate(
                    prompt=prompt,
                    system=system,
                    format="json",
                    temperature=0.1,
                    max_tokens=1500,
                )
            except Exception as e:
                return f"❌ **Executor LLM error**: {e}"

            action = response.get("action")
            reasoning = response.get("reasoning", "")

            if action == "final":
                return response.get("result", "")

            if action not in skill_names:
                return (
                    f"❌ **Invalid action** `{action}`. "
                    f"Available: {', '.join(skill_names) or 'none'}, final."
                )

            if status:
                status(action, reasoning)

            handler = SKILLS[action].handler
            args = response.get("args", {}) or {}
            try:
                result = handler(**args)
            except TypeError as e:
                return f"❌ **Bad args for `{action}`**: {e}"

            if not result.get("success"):
                return f"❌ **`{action}` failed**: {result.get('error', 'unknown')}"

            prompt = self._feedback(action, intent, result)

        return f"⚠️ **Max steps reached** ({self.max_steps}) — task incomplete."

    @staticmethod
    def _feedback(action: str, intent: str, result: dict) -> str:
        """Build the next prompt from a skill's result."""
        if action == "doc_open":
            sources = ", ".join(s.get("name", "?") for s in result.get("sources", []))
            return (
                f"Documents loaded ({result['files_processed']} files: {sources}).\n\n"
                f"Content:\n{result['combined_text']}\n\n"
                f"Task: {intent}\n\n"
                f"Now emit the final answer."
            )
        if action == "write_file":
            return (
                f"File written: {result['path']} ({result['bytes_written']} bytes).\n\n"
                f"Task: {intent}\n\n"
                f"Confirm completion with a final answer."
            )
        # Generic fallback for future skills
        return (
            f"Skill `{action}` returned: {result}\n\n"
            f"Task: {intent}\n\n"
            f"Continue or emit the final answer."
        )
