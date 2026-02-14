"""Email draft generation tool for clawlite."""

from typing import Any

from clawlite.schemas import EmailDraftLength, EmailDraftTone


def email_draft_tool(
    to_role: str,
    tone: str = "neutral",
    goal: str = "",
    context: dict | None = None,
    length: str = "medium",
    documents: dict | None = None,
) -> dict[str, Any]:
    """Draft a professional email.
    
    Args:
        to_role: Recipient role/person
        tone: Email tone (neutral|friendly|formal|firm)
        goal: Goal/purpose of the email
        context: Optional document reference {"doc_id": "..."}
        length: Email length (short|medium|long)
        documents: Dictionary of loaded documents
        
    Returns:
        Email draft result with structured output for LLM processing
    """
    documents = documents or {}
    
    # Get context text if provided
    context_text = ""
    context_title = ""
    if context:
        doc_id = context.get("doc_id")
        if doc_id and doc_id in documents:
            doc = documents[doc_id]
            context_text = doc.get("text", "")
            context_title = doc.get("title", "")
    
    tone_enum = EmailDraftTone(tone)
    length_enum = EmailDraftLength(length)
    
    # Generate email structure for LLM
    email_prompt = _build_email_prompt(to_role, tone_enum, goal, length_enum, context_text, context_title)
    
    return {
        "success": True,
        "to_role": to_role,
        "tone": tone,
        "goal": goal,
        "length": length,
        "email_prompt": email_prompt,
        "note": "Email drafted via prompt. Pass this to LLM to generate final email.",
    }


def _build_email_prompt(
    to_role: str,
    tone: EmailDraftTone,
    goal: str,
    length: EmailDraftLength,
    context_text: str,
    context_title: str,
) -> str:
    """Build email drafting prompt for LLM."""
    
    tone_instructions = {
        EmailDraftTone.NEUTRAL: "Use professional, neutral language. Be clear and direct.",
        EmailDraftTone.FRIENDLY: "Use warm, friendly language. Build rapport while staying professional.",
        EmailDraftTone.FORMAL: "Use formal business language. Be respectful and structured.",
        EmailDraftTone.FIRM: "Be direct and assertive. Make clear requests without being aggressive.",
    }
    
    length_instructions = {
        EmailDraftLength.SHORT: "Keep it brief (3-5 sentences). Get straight to the point.",
        EmailDraftLength.MEDIUM: "Moderate length (2-3 short paragraphs). Provide necessary context.",
        EmailDraftLength.LONG: "Comprehensive (3-5 paragraphs). Include full context and details.",
    }
    
    prompt = f"""# Email Drafting Task

**To**: {to_role}
**Tone**: {tone.value}
**Length**: {length.value}
**Goal**: {goal}

## Instructions

{tone_instructions.get(tone, tone_instructions[EmailDraftTone.NEUTRAL])}

{length_instructions.get(length, length_instructions[EmailDraftLength.MEDIUM])}

## Required Output Format

Please provide your response in this EXACT format:

SUBJECT: [Your subject line here]

BODY:
[Your email body here in markdown]

## Guidelines

1. **Subject Line**: Clear, specific, and action-oriented if needed
2. **Salutation**: Appropriate for the recipient
3. **Opening**: Brief context or reference to previous communication
4. **Body**: Main message with {length.value} level of detail
5. **Closing**: Clear next steps or call to action
6. **Sign-off**: Professional closing

{context_text if context_text else ""}

{context_title if context_title else ""}

## Example Output

```
SUBJECT: Project Update - Q4 Milestones Review

BODY:
Dear {to_role},

I hope this email finds you well. I'm writing to provide an update on our Q4 milestones.

[Main content here...]

Best regards,
[Your name]
```
"""
    
    return prompt
