"""Meeting minutes generation tool for clawlite."""

import re
from typing import Any

from clawlite.schemas import MeetingMinutesTemplate


def meeting_minutes_tool(
    input: dict,
    template: str = "standard",
    include_decisions: bool = True,
    include_risks: bool = True,
    documents: dict | None = None,
) -> dict[str, Any]:
    """Generate meeting minutes from notes or transcript.
    
    Args:
        input: Document reference {"doc_id": "..."}
        template: Template style (standard|client|standup)
        include_decisions: Include decisions section
        include_risks: Include risks section
        documents: Dictionary of loaded documents
        
    Returns:
        Meeting minutes result
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
    title = doc.get("title", "Meeting Notes")
    
    if not text:
        return {
            "success": False,
            "error": "Document has no text content.",
        }
    
    template_enum = MeetingMinutesTemplate(template)
    
    # Parse meeting content
    parsed = _parse_meeting_content(text)
    
    # Generate minutes based on template
    minutes = _generate_minutes(parsed, template_enum, include_decisions, include_risks, title)
    
    return {
        "success": True,
        "doc_id": doc_id,
        "title": title,
        "template": template,
        "minutes": minutes,
    }


def _parse_meeting_content(text: str) -> dict:
    """Parse meeting content to extract structure."""
    result = {
        "attendees": [],
        "agenda": [],
        "discussions": [],
        "decisions": [],
        "action_items": [],
        "risks": [],
    }
    
    lines = text.split('\n')
    current_section = None
    
    section_patterns = {
        "attendees": r'(?i)(attendees?|participants?|present)',
        "agenda": r'(?i)(agenda|topics?|items?)',
        "discussions": r'(?i)(discussion|notes?|highlights?)',
        "decisions": r'(?i)(decisions?|decided|agreed|resolved)',
        "action_items": r'(?i)(action items?|todos?|tasks?|next steps?)',
        "risks": r'(?i)(risks?|issues?|concerns?|blockers?)',
    }
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for section headers
        lower = line.lower()
        for section, pattern in section_patterns.items():
            if re.search(pattern, lower) and len(line) < 50:
                current_section = section
                continue
        
        # Parse attendees
        if current_section == "attendees":
            # Look for names (comma-separated or on separate lines)
            for name in re.split(r'[,;]', line):
                name = name.strip().strip('*-_[]')
                if name and len(name) > 2:
                    result["attendees"].append(name)
        
        # Parse agenda items
        elif current_section == "agenda":
            item = re.sub(r'^[\d.\-\*]+\s*', '', line).strip()
            if item and len(item) > 5:
                result["agenda"].append(item)
        
        # Parse discussions
        elif current_section == "discussions" or current_section is None:
            # Collect discussion points
            if len(line) > 20:
                result["discussions"].append(line)
        
        # Parse decisions
        elif current_section == "decisions":
            decision = re.sub(r'^[\-\*•]+\s*', '', line).strip()
            if decision and len(decision) > 10:
                result["decisions"].append(decision)
        
        # Parse action items
        elif current_section == "action_items":
            action = re.sub(r'^[\-\*•\[\]]+\s*', '', line).strip()
            if action and len(action) > 5:
                result["action_items"].append(action)
        
        # Parse risks
        elif current_section == "risks":
            risk = re.sub(r'^[\-\*•]+\s*', '', line).strip()
            if risk and len(risk) > 5:
                result["risks"].append(risk)
    
    # Try to infer decisions from text patterns
    decision_patterns = [
        r'(?i)(we|the team) (decided|agreed|chose|selected)\s+(?:to|on)?\s*([^\.]+)',
        r'(?i)(decision|outcome)\s*[:\-]\s*([^\.]+)',
    ]
    
    for pattern in decision_patterns:
        for match in re.finditer(pattern, text):
            decision = match.group(2 if len(match.groups()) > 1 else 0).strip()
            if decision and len(decision) > 10:
                result["decisions"].append(decision)
    
    # Try to infer action items from text patterns
    action_patterns = [
        r'(?i)(\w[\w\s]+)\s+(will|needs? to|should|must)\s+([^\.]+)',
        r'(?i)(action|task)\s*[:\-]\s*([^\.]+)',
    ]
    
    for pattern in action_patterns:
        for match in re.finditer(pattern, text):
            action = match.group(0).strip()
            if action and len(action) > 10 and action not in result["action_items"]:
                result["action_items"].append(action)
    
    return result


def _generate_minutes(
    parsed: dict,
    template: MeetingMinutesTemplate,
    include_decisions: bool,
    include_risks: bool,
    title: str,
) -> str:
    """Generate formatted meeting minutes."""
    lines = []
    
    # Header
    if template == MeetingMinutesTemplate.STANDUP:
        lines.append(f"# Stand-up Notes")
    else:
        lines.append(f"# Meeting Minutes: {title}")
    
    lines.append("")
    
    # Attendees
    if parsed["attendees"]:
        lines.append("## Attendees")
        for attendee in parsed["attendees"][:10]:  # Limit to 10
            lines.append(f"- {attendee}")
        lines.append("")
    
    # Agenda
    if parsed["agenda"]:
        lines.append("## Agenda")
        for item in parsed["agenda"]:
            lines.append(f"- {item}")
        lines.append("")
    
    # Discussion Highlights
    if parsed["discussions"]:
        lines.append("## Discussion Highlights")
        # Take first few points to avoid overwhelming output
        for point in parsed["discussions"][:8]:
            # Clean up the point
            point = re.sub(r'^[\-\*•]+\s*', '', point).strip()
            if point:
                lines.append(f"- {point}")
        if len(parsed["discussions"]) > 8:
            lines.append(f"- *...and {len(parsed["discussions"]) - 8} more discussion points*")
        lines.append("")
    
    # Decisions
    if include_decisions and parsed["decisions"]:
        lines.append("## Decisions")
        for decision in parsed["decisions"][:10]:
            lines.append(f"- ✅ {decision}")
        lines.append("")
    
    # Action Items
    if parsed["action_items"]:
        lines.append("## Action Items")
        for action in parsed["action_items"][:15]:
            lines.append(f"- [ ] {action}")
        if len(parsed["action_items"]) > 15:
            lines.append(f"- *...and {len(parsed["action_items"]) - 15} more items*")
        lines.append("")
    
    # Risks
    if include_risks and parsed["risks"]:
        lines.append("## Risks & Blockers")
        for risk in parsed["risks"][:8]:
            lines.append(f"- ⚠️ {risk}")
        lines.append("")
    
    # Next Meeting (for client/standard templates)
    if template != MeetingMinutesTemplate.STANDUP:
        lines.append("## Next Steps")
        lines.append("- Review action items before next meeting")
        lines.append("")
    
    return '\n'.join(lines)
