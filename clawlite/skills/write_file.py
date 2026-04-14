"""Write skill — write text to the memory folder (only)."""

from pathlib import Path
from typing import Any, Dict

from clawlite.config import MEMORY_DIR, is_write_allowed
from clawlite.skills.base import Skill


def write_file(path: str, content: str) -> Dict[str, Any]:
    try:
        raw = Path(path).expanduser()
        target = raw if raw.is_absolute() else (MEMORY_DIR / raw)

        if not is_write_allowed(target):
            return {
                "success": False,
                "error": f"Refused: {target} is outside memory ({MEMORY_DIR}).",
            }

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "path": str(target.resolve()),
            "bytes_written": len(content.encode("utf-8")),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


WRITE_FILE = Skill(
    name="write_file",
    summary="Write text to a file in the memory folder (persistent scratchpad).",
    description=(
        'write_file — save text into the memory folder.\n'
        'Args: {"path": str, "content": str}\n'
        'Path: bare filename is placed inside the memory folder; absolute paths '
        f'must be inside {MEMORY_DIR}.\n'
        'Returns: {success, path, bytes_written}.\n'
        'Example: {"action": "write_file", "args": {"path": "summary.md", '
        '"content": "# Notes\\n..."}}'
    ),
    handler=write_file,
)
