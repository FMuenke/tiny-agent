"""Action items extraction tool for clawlite."""

import re
from typing import Any

from clawlite.schemas import ActionItemsFormat


def action_items_tool(
    input: dict,
    format: str = "bullets",
    max_items: int = 25,
    documents: dict | None = None,
) -> dict[str, Any]:
    """Extract action items from text.
    
    Args:
        input: Document reference {"doc_id": "..."}
        format: Output format (table|bullets)
        max_items: Maximum items
        documents: Dictionary of loaded documents
        
    Returns:
        Action items result
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
    
    # Extract action items using regex patterns
    items = _extract_action_items(text, max_items)
    
    format_enum = ActionItemsFormat(format)
    
    if format_enum == ActionItemsFormat.TABLE:
        output = _format_as_table(items)
    else:
        output = _format_as_bullets(items)
    
    return {
        "success": True,
        "doc_id": doc_id,
        "title": title,
        "format": format,
        "count": len(items),
        "output": output,
    }


def _extract_action_items(text: str, max_items: int) -> list[dict]:
    """Extract action items from text.
    
    Uses pattern matching to identify likely action items.
    """
    items = []
    
    # Split into sentences/lines
    lines = text.split('\n')
    
    # Pattern: lines starting with action keywords
    action_patterns = [
        r'(?i)^(.*?)(?:\s*[-–—]\s*|\s*:\s*)(.+)$',  # "Owner - Action" or "Owner: Action"
        r'(?i)^\s*[\-\*\•]\s*(.+)$',  # Bullet points
        r'(?i)^\s*\[\s*\]\s*(.+)$',  # Checkboxes
        r'(?i)^\s*(action item|todo|task)\s*[:\-]\s*(.+)$',  # "Action item: ..."
    ]
    
    # Keywords that suggest action items
    action_keywords = [
        'action', 'todo', 'task', 'follow up', 'follow-up', 'need to',
        'should', 'must', 'will', 'going to', 'plan to', 'assigned to',
    ]
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue
        
        # Check for action patterns
        is_action = False
        owner = None
        due = None
        
        # Check for keywords
        lower = line.lower()
        for kw in action_keywords:
            if kw in lower:
                is_action = True
                break
        
        # Try to extract owner (person before dash or colon)
        for pattern in action_patterns[:1]:
            match = re.match(pattern, line)
            if match:
                potential_owner = match.group(1).strip()
                action_text = match.group(2).strip()
                # Owner is typically a short name (1-3 words)
                if potential_owner and len(potential_owner.split()) <= 3:
                    owner = potential_owner
                    line = action_text
                    is_action = True
                break
        
        # Extract dates (simple patterns)
        date_patterns = [
            r'\b(by|due|before)\s+([A-Za-z]+ \d{1,2}|\d{1,2}[\/\-]\d{1,2}[\/\-]?\d{2,4})',
            r'\b(next week|this week|tomorrow|by Monday|by Tuesday|by Wednesday|by Thursday|by Friday)\b',
            r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}?',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                due = match.group(0)
                break
        
        if is_action:
            # Clean up the action text
            action_text = re.sub(r'^[\-\*\•\[\]\(\)]+\s*', '', line)
            action_text = re.sub(r'\s+', ' ', action_text).strip()
            
            items.append({
                "action": action_text,
                "owner": owner,
                "due": due,
                "context": "",
            })
            
            if len(items) >= max_items:
                break
    
    return items


def _format_as_table(items: list[dict]) -> str:
    """Format items as markdown table."""
    lines = [
        "| Action | Owner | Due | Context |",
        "|--------|-------|-----|----------|",
    ]
    
    for item in items:
        action = item["action"].replace('|', '\\|')
        owner = (item["owner"] or "—").replace('|', '\\|')
        due = (item["due"] or "—").replace('|', '\\|')
        context = (item["context"] or "").replace('|', '\\|')
        
        lines.append(f"| {action} | {owner} | {due} | {context} |")
    
    return '\n'.join(lines)


def _format_as_bullets(items: list[dict]) -> str:
    """Format items as markdown bullets."""
    lines = []
    
    for item in items:
        parts = [f"- [ ] {item['action']}"]
        
        if item["owner"]:
            parts.append(f"— **{item['owner']}**")
        if item["due"]:
            parts.append(f"— *{item['due']}*")
        
        lines.append(' '.join(parts))
    
    return '\n'.join(lines)
