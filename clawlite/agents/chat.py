"""ChatAgent — the user-facing voice. Decides: chit-chat or dispatch."""

from typing import Any, Dict

from clawlite.config import MEMORY_DIR
from clawlite.ollama_client import OllamaClient
from clawlite.skills import catalog

CHAT_PROMPT = """You are the user's assistant. Respond with JSON only.

TWO RESPONSE TYPES:

1. Direct reply (greetings, questions you can answer, chit-chat):
{{"action": "reply", "text": "your response"}}

2. Dispatch a task (when tools are needed — reading files, writing notes, etc.):
{{"action": "execute", "intent": "one-sentence description of the task"}}

CAPABILITIES (high-level — you do NOT need to know how they work):
{capabilities}

MEMORY FOLDER: {memory_dir}
A persistent scratchpad. Reads and writes to it are always available.

RULES:
- Pick "execute" ONLY when tools are needed — reading files, writing files, opening documents.
- Pick "reply" for conversation, explanations, opinions, rephrasing, rewriting, translating, answering questions, summarizing text the user provided inline, or any task you can complete using only the text in the user's message.
- In "intent", be specific about paths and filenames the user mentioned.
- Never make up file contents — dispatch a task to read first.
"""


class ChatAgent:
    def __init__(self, client: OllamaClient):
        self.client = client
        self.system = CHAT_PROMPT.format(
            capabilities=catalog(),
            memory_dir=MEMORY_DIR,
        )

    def decide(self, user_input: str) -> Dict[str, Any]:
        return self.client.generate(
            prompt=user_input,
            system=self.system,
            format="json",
            temperature=0.1,
            max_tokens=400,
        )
