"""SkillBroker — maps an intent to the minimal set of skills needed."""

from typing import List

from clawlite.ollama_client import OllamaClient
from clawlite.skills import SKILLS, catalog

BROKER_PROMPT = """You select the skills needed to complete a task.
Respond with JSON only.

FORMAT:
{{"skills": ["skill_name", ...]}}

SKILL CATALOG:
{catalog}

RULES:
- Only use names from the catalog above. Never invent skills.
- Order skills in the sequence they should run (e.g. read before write).
- Include only what is strictly necessary.
- If no skills match, return {{"skills": []}}.
"""


class SkillBroker:
    def __init__(self, client: OllamaClient):
        self.client = client
        self.system = BROKER_PROMPT.format(catalog=catalog())

    def select(self, intent: str) -> List[str]:
        response = self.client.generate(
            prompt=f"Task: {intent}",
            system=self.system,
            format="json",
            temperature=0.0,
            max_tokens=200,
        )
        raw = response.get("skills", [])
        if not isinstance(raw, list):
            return []
        return [s for s in raw if isinstance(s, str) and s in SKILLS]
