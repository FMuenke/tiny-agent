"""ClawLite memory folder — the agent's personal read/write scratchpad."""

from pathlib import Path

# Project-local memory folder. Resolved from the package location so it is
# stable regardless of the caller's cwd (including --workspace).
MEMORY_DIR: Path = (Path(__file__).resolve().parent.parent / "memory").resolve()

# Ensure it exists on import — the agent should always be able to read/write.
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def is_write_allowed(target: Path) -> bool:
    """True iff `target` resolves to a path inside MEMORY_DIR."""
    try:
        resolved = target.expanduser().resolve(strict=False)
    except (OSError, RuntimeError):
        return False
    try:
        resolved.relative_to(MEMORY_DIR)
        return True
    except ValueError:
        return False
