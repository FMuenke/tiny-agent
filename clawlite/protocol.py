"""JSON protocol parser with repair loop for small LLMs."""

import json
import re
from typing import Dict, Any, Tuple


def parse_llm_output(text: str, max_attempts: int = 2) -> Dict[str, Any]:
    """
    Parse JSON output from LLM with automatic repair attempts.

    Args:
        text: Raw text output from LLM
        max_attempts: Maximum repair attempts (default: 2)

    Returns:
        Parsed JSON as dictionary

    Raises:
        ValueError: If JSON cannot be parsed after all repair attempts
    """
    # Attempt 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError as first_error:
        if max_attempts <= 1:
            raise ValueError(f"Invalid JSON (no repairs attempted): {first_error}\n{text[:200]}")

    # Attempt 2: Apply common repairs
    repaired, applied_fixes = repair_json(text)

    try:
        result = json.loads(repaired)
        # Successfully repaired
        return result
    except json.JSONDecodeError as repair_error:
        raise ValueError(
            f"Could not repair JSON after {len(applied_fixes)} fixes.\n"
            f"Original error: {first_error}\n"
            f"After repairs: {repair_error}\n"
            f"Applied fixes: {applied_fixes}\n"
            f"Text: {text[:300]}"
        )


def repair_json(text: str) -> Tuple[str, list]:
    """
    Apply common JSON repair strategies for small LLM outputs.

    Returns:
        (repaired_text, list_of_applied_fixes)
    """
    repaired = text.strip()
    fixes_applied = []

    # Fix 1: Extract JSON if wrapped in markdown code blocks
    if "```json" in repaired or "```" in repaired:
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', repaired, re.DOTALL)
        if match:
            repaired = match.group(1)
            fixes_applied.append("extracted_from_markdown")

    # Fix 2: Convert single quotes to double quotes (but not in strings)
    # Simple heuristic: replace single quotes around keys
    repaired = re.sub(r"'(\w+)':", r'"\1":', repaired)
    if "'" in text:
        fixes_applied.append("single_to_double_quotes")

    # Fix 3: Remove trailing commas before closing braces/brackets
    original = repaired
    repaired = re.sub(r',(\s*[}\]])', r'\1', repaired)
    if original != repaired:
        fixes_applied.append("removed_trailing_commas")

    # Fix 4: Common typo fixes
    typo_fixes = {
        '"act"': '"action"',
        '"arguments"': '"args"',
        '"params"': '"args"',
        '"response"': '"result"',
    }
    for wrong, correct in typo_fixes.items():
        if wrong in repaired:
            repaired = repaired.replace(wrong, correct)
            fixes_applied.append(f"typo_{wrong}_to_{correct}")

    # Fix 5: Add missing closing braces (simple heuristic)
    open_braces = repaired.count('{')
    close_braces = repaired.count('}')
    if open_braces > close_braces:
        repaired += '}' * (open_braces - close_braces)
        fixes_applied.append(f"added_{open_braces - close_braces}_closing_braces")

    # Fix 6: Add missing closing brackets
    open_brackets = repaired.count('[')
    close_brackets = repaired.count(']')
    if open_brackets > close_brackets:
        repaired += ']' * (open_brackets - close_brackets)
        fixes_applied.append(f"added_{open_brackets - close_brackets}_closing_brackets")

    # Fix 7: Escape unescaped quotes in string values (complex, best effort)
    # This is tricky, so we skip for now in MVP

    return repaired, fixes_applied


def validate_action(action_dict: Dict[str, Any]) -> bool:
    """
    Validate that action dictionary has required fields.

    Required:
        - "action": str (tool name or "final")
        - "args": dict (if action != "final")
        - "result": str (if action == "final")

    Returns:
        True if valid, False otherwise
    """
    if "action" not in action_dict:
        return False

    action = action_dict["action"]

    if action == "final":
        return "result" in action_dict
    else:
        return "args" in action_dict and isinstance(action_dict["args"], dict)
