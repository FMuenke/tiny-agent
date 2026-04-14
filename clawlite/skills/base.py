"""Skill definition — the unit the broker selects and the executor runs."""

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class Skill:
    """
    A capability the agent can invoke.

    `summary` is what the SkillBroker sees (one line per skill, kept short so
    many skills fit in its context). `description` is the full instructions
    shown to the Executor only when this skill is selected for a task.
    """

    name: str
    summary: str
    description: str
    handler: Callable[..., Dict[str, Any]]
