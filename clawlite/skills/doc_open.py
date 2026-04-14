"""Read skill — open files or folders and extract text."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pymupdf as fitz

from clawlite.config import MEMORY_DIR
from clawlite.skills.base import Skill


def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        doc = fitz.open(path)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text
    if suffix in (".txt", ".md", ".jsonl", ".json"):
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type: {suffix}")


def _resolve(path: str) -> Path:
    """Bare filenames resolve inside the memory folder."""
    p = Path(path).expanduser()
    return p if p.is_absolute() else (MEMORY_DIR / p)


def doc_open(
    path: str,
    recursive: bool = False,
    file_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    target = _resolve(path)
    file_types = [ext.lstrip(".") for ext in (file_types or ["pdf", "txt", "md", "jsonl"])]

    try:
        if target.is_file():
            text = _extract_text(target)
            return {
                "success": True,
                "files_processed": 1,
                "sources": [{"name": target.name, "chars": len(text)}],
                "combined_text": text[:4000],
            }

        if target.is_dir():
            texts, sources = [], []
            for ext in file_types:
                pattern = f"**/*.{ext}" if recursive else f"*.{ext}"
                for f in sorted(target.glob(pattern)):
                    try:
                        text = _extract_text(f)
                        texts.append(f"\n--- {f.name} ---\n{text}\n")
                        sources.append({"name": f.name, "chars": len(text)})
                    except Exception as e:
                        sources.append({"name": f.name, "error": str(e)})
            if not sources:
                return {"success": False, "error": f"No {file_types} files in {target}"}
            return {
                "success": True,
                "files_processed": len(sources),
                "sources": sources,
                "combined_text": "\n".join(texts)[:6000],
            }

        return {"success": False, "error": f"Path not found: {target}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


DOC_OPEN = Skill(
    name="doc_open",
    summary="Read text from a file or folder (PDF, TXT, MD).",
    description=(
        'doc_open — read files or folders.\n'
        'Args: {"path": str, "recursive": bool (default false), '
        '"file_types": list[str] (default ["pdf","txt","md"])}\n'
        'Path: absolute, or bare filename = inside the memory folder.\n'
        'Returns: {success, files_processed, sources[{name, chars}], combined_text}.\n'
        'Example: {"action": "doc_open", "args": {"path": "notes.md"}}\n'
        'Example: {"action": "doc_open", "args": {"path": "/Users/x/docs", '
        '"file_types": ["pdf"]}}'
    ),
    handler=doc_open,
)
