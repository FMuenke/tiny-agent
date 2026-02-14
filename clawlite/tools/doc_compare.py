"""Document comparison tool for clawlite."""

import difflib
import re
from typing import Any

from clawlite.schemas import DocCompareMode


def doc_compare_tool(
    a: dict,
    b: dict,
    mode: str = "summary",
    max_output_chars: int = 12000,
    documents: dict | None = None,
) -> dict[str, Any]:
    """Compare two documents.
    
    Args:
        a: Document reference {"doc_id": "..."}
        b: Document reference {"doc_id": "..."}
        mode: Comparison mode (diff|summary|semantic)
        max_output_chars: Maximum output characters
        documents: Dictionary of loaded documents
        
    Returns:
        Comparison result
    """
    documents = documents or {}
    
    # Get documents
    doc_a_id = a.get("doc_id")
    doc_b_id = b.get("doc_id")
    
    if doc_a_id not in documents:
        return {
            "success": False,
            "error": f"Document {doc_a_id} not found. Open it first with doc_open.",
        }
    
    if doc_b_id not in documents:
        return {
            "success": False,
            "error": f"Document {doc_b_id} not found. Open it first with doc_open.",
        }
    
    doc_a = documents[doc_a_id]
    doc_b = documents[doc_b_id]
    
    text_a = doc_a.get("text", "")
    text_b = doc_b.get("text", "")
    title_a = doc_a.get("title", "Document A")
    title_b = doc_b.get("title", "Document B")
    
    mode_enum = DocCompareMode(mode)
    
    if mode_enum == DocCompareMode.DIFF:
        result = _compute_diff(text_a, text_b, title_a, title_b, max_output_chars)
    elif mode_enum == DocCompareMode.SUMMARY:
        result = _compute_summary(text_a, text_b, title_a, title_b, max_output_chars)
    elif mode_enum == DocCompareMode.SEMANTIC:
        # For semantic mode, return structured data for LLM processing
        result = _compute_semantic(text_a, text_b, title_a, title_b, max_output_chars)
    else:
        return {
            "success": False,
            "error": f"Unknown mode: {mode}",
        }
    
    return {
        "success": True,
        "doc_a_id": doc_a_id,
        "doc_b_id": doc_b_id,
        "mode": mode,
        "result": result[:max_output_chars] if len(result) > max_output_chars else result,
        "truncated": len(result) > max_output_chars,
    }


def _normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Normalize line endings
    text = text.replace('\r\n', '\n')
    # Collapse excessive whitespace (but preserve paragraph structure)
    lines = text.split('\n')
    normalized = []
    for line in lines:
        line = line.strip()
        if line:
            normalized.append(line)
    return '\n'.join(normalized)


def _compute_diff(text_a: str, text_b: str, title_a: str, title_b: str, max_chars: int) -> str:
    """Compute unified diff."""
    norm_a = _normalize_text(text_a)
    norm_b = _normalize_text(text_b)
    
    lines_a = norm_a.split('\n')
    lines_b = norm_b.split('\n')
    
    diff = list(difflib.unified_diff(
        lines_a,
        lines_b,
        fromfile=title_a,
        tofile=title_b,
        lineterm='',
    ))
    
    result = '\n'.join(diff)
    
    # Truncate if too long
    if len(result) > max_chars:
        result = result[:max_chars] + "\n\n[...diff truncated...]"
    
    return result


def _compute_summary(text_a: str, text_b: str, title_a: str, title_b: str, max_chars: int) -> str:
    """Compute summary comparison."""
    # Extract basic metrics
    len_a = len(text_a)
    len_b = len(text_b)
    
    # Simple word overlap analysis
    words_a = set(re.findall(r'\b\w+\b', text_a.lower()))
    words_b = set(re.findall(r'\b\w+\b', text_b.lower()))
    
    common = words_a & words_b
    only_a = words_a - words_b
    only_b = words_b - words_a
    
    overlap_ratio = len(common) / max(len(words_a), 1)
    
    # Build summary
    lines = [
        f"# Comparison: {title_a} vs {title_b}",
        "",
        "## Overview",
        f"- **{title_a}**: {len_a:,} characters",
        f"- **{title_b}**: {len_b:,} characters",
        f"- **Size difference**: {len_b - len_a:+,} characters",
        f"- **Word overlap**: {overlap_ratio:.1%}",
        "",
        "## Key Differences",
        f"- Unique to **{title_a}**: {len(only_a)} words",
        f"- Unique to **{title_b}**: {len(only_b)} words",
        f"- Shared vocabulary: {len(common)} words",
    ]
    
    # Show sample unique terms if not too long
    if only_a and len(str(only_a)) < 500:
        lines.extend(["", f"### Sample terms only in {title_a}"])
        lines.append(f"- {', '.join(list(only_a)[:10])}")
    
    if only_b and len(str(only_b)) < 500:
        lines.extend(["", f"### Sample terms only in {title_b}"])
        lines.append(f"- {', '.join(list(only_b)[:10])}")
    
    result = '\n'.join(lines)
    
    if len(result) > max_chars:
        result = result[:max_chars] + "\n\n[...truncated...]"
    
    return result


def _compute_semantic(text_a: str, text_b: str, title_a: str, title_b: str, max_chars: int) -> str:
    """Prepare semantic comparison data.
    
    Returns structured comparison data for LLM processing.
    """
    # Truncate texts for semantic analysis
    sample_a = text_a[:5000]
    sample_b = text_b[:5000]
    
    lines = [
        f"# Semantic Comparison Data: {title_a} vs {title_b}",
        "",
        "## Document A Sample (first 5000 chars)",
        "---",
        sample_a,
        "---",
        "",
        "## Document B Sample (first 5000 chars)",
        "---",
        sample_b,
        "---",
        "",
        "## Analysis Request",
        "Identify key semantic differences between these documents:",
        "- Main topics covered in each",
        "- Differences in perspective or approach",
        "- Missing information in either document",
        "- Contradictions or conflicting information",
    ]
    
    result = '\n'.join(lines)
    
    if len(result) > max_chars:
        result = result[:max_chars] + "\n\n[...truncated...]"
    
    return result
