"""Summarization tool for clawlite - uses LLM with constrained prompts."""

from typing import Any

from clawlite.schemas import SummarizeAudience, SummarizeStyle


def summarize_tool(
    input: dict,
    style: str = "bullets",
    audience: str = "internal",
    max_words: int = 250,
    documents: dict | None = None,
) -> dict[str, Any]:
    """Generate a summary of a document.
    
    Args:
        input: Document reference {"doc_id": "..."}
        style: Summary style (exec|bullets|tl;dr|detailed|table)
        audience: Target audience (internal|client|mixed)
        max_words: Maximum words
        documents: Dictionary of loaded documents
        
    Returns:
        Summary result
    """
    documents = documents or {}
    
    doc_id = input.get("doc_id")
    if doc_id not in documents:
        return {
            "success": False,
            "error": f"Document {doc_id} not found. Open it first with doc_open.",
        }
    
    doc = documents[doc_id]
    text = doc.get("text", "")
    title = doc.get("title", "Document")
    
    if not text:
        return {
            "success": False,
            "error": "Document has no text content.",
        }
    
    style_enum = SummarizeStyle(style)
    audience_enum = SummarizeAudience(audience)
    
    # Build structured summary prompt
    summary_prompt = _build_summary_prompt(text, title, style_enum, audience_enum, max_words)
    
    return {
        "success": True,
        "doc_id": doc_id,
        "title": title,
        "style": style,
        "audience": audience,
        "summary_prompt": summary_prompt,
        "note": "Summary generated via prompt. Pass this to LLM with summarize instructions.",
    }


def _build_summary_prompt(
    text: str,
    title: str,
    style: SummarizeStyle,
    audience: SummarizeAudience,
    max_words: int,
) -> str:
    """Build a constrained summarization prompt.
    
    This prepares the document text and instructions for LLM summarization.
    """
    # Truncate text for the prompt (keep enough for summary)
    max_input_chars = 15000
    truncated_text = text[:max_input_chars]
    
    style_instructions = {
        SummarizeStyle.EXEC: "Write an executive summary (3-5 paragraphs) highlighting key findings and recommendations.",
        SummarizeStyle.BULLETS: "Use bullet points (5-10 bullets) for easy scanning.",
        SummarizeStyle.TLDR: "Provide a brief tl;dr (1-2 sentences maximum).",
        SummarizeStyle.DETAILED: "Provide a detailed summary covering all major sections.",
        SummarizeStyle.TABLE: "Use a markdown table with columns: Section | Key Points.",
    }
    
    audience_instructions = {
        SummarizeAudience.INTERNAL: "Use internal terminology and assume reader context.",
        SummarizeAudience.CLIENT: "Use professional, accessible language. Avoid jargon.",
        SummarizeAudience.MIXED: "Balance technical detail with accessibility.",
    }
    
    prompt = f"""# Summarization Task

**Document**: {title}
**Style**: {style.value}
**Audience**: {audience.value}
**Max Words**: {max_words}

## Instructions

{style_instructions.get(style, style_instructions[SummarizeStyle.BULLETS])}

{audience_instructions.get(audience, audience_instructions[SummarizeAudience.INTERNAL])}

Key requirements:
- Keep under {max_words} words
- Be factual and grounded in the text
- Include 3-5 key quotes if relevant
- Note any assumptions you made

## Document Text

```
{truncated_text}
```

{'[Note: Document truncated for summarization]' if len(text) > max_input_chars else ''}

## Output Format

Please provide your summary in markdown format below.
"""
    
    return prompt
