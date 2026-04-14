"""Skill registry — all capabilities the agent can use."""

from typing import Dict

from clawlite.skills.base import Skill
from clawlite.skills.doc_open import DOC_OPEN
from clawlite.skills.write_file import WRITE_FILE

SKILLS: Dict[str, Skill] = {s.name: s for s in (DOC_OPEN, WRITE_FILE)}


def catalog() -> str:
    """One line per skill — used by the broker."""
    return "\n".join(f"- {s.name}: {s.summary}" for s in SKILLS.values())


def descriptions(names) -> str:
    """Full descriptions for the selected skills — used by the executor."""
    return "\n\n".join(
        SKILLS[n].description for n in names if n in SKILLS
    )


__all__ = ["Skill", "SKILLS", "catalog", "descriptions"]
