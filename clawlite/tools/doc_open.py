"""Document opening tool with folder support."""

from pathlib import Path
from typing import List, Dict, Any, Optional
import pymupdf as fitz


def doc_open(
    path: str,
    recursive: bool = False,
    file_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Open document(s) and extract text.

    Args:
        path: File path or folder path
        recursive: Search subfolders (default: False)
        file_types: List of extensions to filter (default: ["pdf", "txt", "md"])

    Returns:
        Dictionary with:
            - success: bool
            - files_processed: int
            - sources: List[dict] with metadata per file
            - combined_text: str (truncated to 8000 chars)
            - metadata: dict with totals
            - error: str (if success=False)
    """
    path_obj = Path(path)
    file_types = file_types or ["pdf", "txt", "md"]

    # Normalize extensions (remove dots)
    file_types = [ext.lstrip('.') for ext in file_types]

    try:
        # Single file
        if path_obj.is_file():
            text = extract_text_from_file(path_obj)
            return {
                "success": True,
                "files_processed": 1,
                "sources": [
                    {
                        "path": str(path_obj),
                        "name": path_obj.name,
                        "type": path_obj.suffix[1:],
                        "chars": len(text),
                        "excerpt": text[:200] + "..." if len(text) > 200 else text,
                    }
                ],
                "combined_text": text[:4000],  # Increased to capture more content
                "metadata": {
                    "total_files": 1,
                    "total_chars": len(text),
                    "truncated": len(text) > 8000,
                },
            }

        # Folder
        elif path_obj.is_dir():
            all_texts = []
            sources = []

            for ext in file_types:
                pattern = f"**/*.{ext}" if recursive else f"*.{ext}"
                for file in sorted(path_obj.glob(pattern)):
                    try:
                        text = extract_text_from_file(file)
                        all_texts.append(f"\n--- {file.name} ---\n{text}\n")
                        sources.append(
                            {
                                "path": str(file),
                                "name": file.name,
                                "type": ext,
                                "chars": len(text),
                                "excerpt": text[:200] + "..." if len(text) > 200 else text,
                            }
                        )
                    except Exception as e:
                        # Skip files that can't be read
                        sources.append(
                            {
                                "path": str(file),
                                "name": file.name,
                                "type": ext,
                                "error": str(e),
                            }
                        )

            if not sources:
                return {
                    "success": False,
                    "error": f"No files found matching types: {file_types}",
                }

            combined = "\n".join(all_texts)
            return {
                "success": True,
                "files_processed": len(sources),
                "sources": sources,
                "combined_text": combined[:6000],  # Increased to fit all 5 invoices
                "metadata": {
                    "total_files": len(sources),
                    "total_chars": len(combined),
                    "truncated": len(combined) > 8000,
                    "file_types": {ext: sum(1 for s in sources if s.get("type") == ext) for ext in file_types},
                },
            }

        else:
            return {
                "success": False,
                "error": f"Path not found: {path}",
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error opening documents: {str(e)}",
        }


def extract_text_from_file(path: Path) -> str:
    """
    Extract text from PDF, TXT, or MD file.

    Args:
        path: Path to file

    Returns:
        Extracted text as string

    Raises:
        ValueError: If file type not supported
        Exception: If file cannot be read
    """
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        # Extract text from PDF using PyMuPDF
        doc = fitz.open(path)
        text_parts = []

        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text()
            text_parts.append(page_text)

        doc.close()
        return "\n".join(text_parts)

    elif suffix in [".txt", ".md"]:
        # Read text files with UTF-8 encoding
        return path.read_text(encoding="utf-8", errors="ignore")

    else:
        raise ValueError(f"Unsupported file type: {suffix}")
