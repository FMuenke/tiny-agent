"""Document opening tool for clawlite."""

import hashlib
import os
from pathlib import Path
from typing import Any


def doc_open_tool(path: str, format_hint: str = "auto", max_chars: int = 50000, workspace: str = "") -> dict[str, Any]:
    """Open and extract text from PDF, TXT, or MD files.
    
    Args:
        path: Path to the document
        format_hint: Format hint (pdf|txt|md|auto)
        max_chars: Maximum characters to extract
        workspace: Restricted workspace path
        
    Returns:
        Document data with text, metadata, and doc_id
    """
    # Resolve path
    file_path = Path(path).expanduser().resolve()
    
    # Check workspace constraint
    if workspace:
        workspace_path = Path(workspace).expanduser().resolve()
        try:
            file_path.relative_to(workspace_path)
        except ValueError:
            return {
                "success": False,
                "error": f"Path {path} is outside workspace {workspace}",
            }
    
    # Check file exists
    if not file_path.exists():
        return {
            "success": False,
            "error": f"File not found: {path}",
        }
    
    # Determine format
    if format_hint == "auto":
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            format_hint = "pdf"
        elif ext == ".md":
            format_hint = "md"
        elif ext == ".txt":
            format_hint = "txt"
        else:
            return {
                "success": False,
                "error": f"Cannot determine format for: {path}. Use format_hint.",
            }
    
    # Extract text
    try:
        if format_hint == "pdf":
            text = _extract_pdf(file_path, max_chars)
        elif format_hint in ("txt", "md"):
            text = _extract_text(file_path, max_chars)
        else:
            return {
                "success": False,
                "error": f"Unsupported format: {format_hint}",
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Extraction failed: {e}",
        }
    
    # Generate doc_id (stable hash)
    stat = file_path.stat()
    hash_input = f"{file_path}:{stat.st_mtime}:{stat.st_size}"
    doc_id = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    return {
        "success": True,
        "doc_id": doc_id,
        "title": file_path.name,
        "text": text,
        "meta": {
            "path": str(file_path),
            "format": format_hint,
            "chars": len(text),
            "truncated": len(text) >= max_chars,
        },
    }


def _extract_pdf(path: Path, max_chars: int) -> str:
    """Extract text from PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("pymupdf required for PDF extraction. Install with: pip install pymupdf")
    
    doc = fitz.open(path)
    text_parts = []
    total_chars = 0
    
    for page_num, page in enumerate(doc):
        page_text = page.get_text()
        if total_chars + len(page_text) > max_chars:
            remaining = max_chars - total_chars
            text_parts.append(page_text[:remaining])
            break
        text_parts.append(page_text)
        total_chars += len(page_text)
    
    doc.close()
    return "\n\n".join(text_parts)


def _extract_text(path: Path, max_chars: int) -> str:
    """Extract text from plain text file."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read(max_chars + 100)  # Read a bit more to handle encoding
    return text[:max_chars]
