"""Pydantic schemas for clawlite tool system."""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class DocOpenArgs(BaseModel):
    """Arguments for doc_open tool."""
    path: str = Field(..., description="Path to the document")
    format_hint: str = Field(default="auto", description="Format hint: pdf|txt|md|auto")
    max_chars: int = Field(default=50000, ge=1000, le=200000, description="Maximum characters to extract")


class DocCompareMode(str, Enum):
    """Comparison modes for doc_compare."""
    DIFF = "diff"
    SUMMARY = "summary"
    SEMANTIC = "semantic"


class DocReference(BaseModel):
    """Reference to a document (either by doc_id)."""
    doc_id: str = Field(..., description="Document ID")


class DocCompareArgs(BaseModel):
    """Arguments for doc_compare tool."""
    a: DocReference = Field(..., description="First document reference")
    b: DocReference = Field(..., description="Second document reference")
    mode: DocCompareMode = Field(default=DocCompareMode.SUMMARY, description="Comparison mode")
    max_output_chars: int = Field(default=12000, ge=1000, le=50000, description="Maximum output characters")


class WebSearchArgs(BaseModel):
    """Arguments for web_search tool."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    num_results: int = Field(default=5, ge=1, le=10, description="Number of results")
    recency_days: int = Field(default=30, ge=1, le=365, description="Recency filter in days")
    extract: str = Field(default="snippets", description="Extraction mode: snippets|readable_text")
    max_chars_per_result: int = Field(default=3000, ge=500, le=10000, description="Max chars per result")


class SummarizeStyle(str, Enum):
    """Summary styles."""
    EXEC = "exec"
    BULLETS = "bullets"
    TLDR = "tl;dr"
    DETAILED = "detailed"
    TABLE = "table"


class SummarizeAudience(str, Enum):
    """Target audience for summary."""
    INTERNAL = "internal"
    CLIENT = "client"
    MIXED = "mixed"


class SummarizeArgs(BaseModel):
    """Arguments for summarize tool."""
    input: DocReference = Field(..., description="Document to summarize")
    style: SummarizeStyle = Field(default=SummarizeStyle.BULLETS, description="Summary style")
    audience: SummarizeAudience = Field(default=SummarizeAudience.INTERNAL, description="Target audience")
    max_words: int = Field(default=250, ge=50, le=1000, description="Maximum words")


class WriteFileMode(str, Enum):
    """Write file modes."""
    OVERWRITE = "overwrite"
    APPEND = "append"


class WriteFileArgs(BaseModel):
    """Arguments for write_file tool."""
    path: str = Field(..., description="Path to write")
    content: str = Field(..., description="Content to write")
    mode: WriteFileMode = Field(default=WriteFileMode.OVERWRITE, description="Write mode")
    create_dirs: bool = Field(default=True, description="Create directories if needed")


class ActionItemsFormat(str, Enum):
    """Output format for action_items."""
    TABLE = "table"
    BULLETS = "bullets"


class ActionItemsArgs(BaseModel):
    """Arguments for action_items tool."""
    input: DocReference = Field(..., description="Document to extract from")
    format: ActionItemsFormat = Field(default=ActionItemsFormat.BULLETS, description="Output format")
    max_items: int = Field(default=25, ge=1, le=100, description="Maximum items")


class MeetingMinutesTemplate(str, Enum):
    """Template for meeting minutes."""
    STANDARD = "standard"
    CLIENT = "client"
    STANDUP = "standup"


class MeetingMinutesArgs(BaseModel):
    """Arguments for meeting_minutes tool."""
    input: DocReference = Field(..., description="Document containing notes/transcript")
    template: MeetingMinutesTemplate = Field(default=MeetingMinutesTemplate.STANDARD, description="Template style")
    include_decisions: bool = Field(default=True, description="Include decisions section")
    include_risks: bool = Field(default=True, description="Include risks section")


class EmailDraftTone(str, Enum):
    """Tone for email draft."""
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    FORMAL = "formal"
    FIRM = "firm"


class EmailDraftLength(str, Enum):
    """Email length."""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class EmailDraftArgs(BaseModel):
    """Arguments for email_draft tool."""
    to_role: str = Field(..., description="Recipient role/person")
    tone: EmailDraftTone = Field(default=EmailDraftTone.NEUTRAL, description="Email tone")
    goal: str = Field(..., description="Goal/purpose of the email")
    context: Optional[DocReference] = Field(default=None, description="Optional document context")
    length: EmailDraftLength = Field(default=EmailDraftLength.MEDIUM, description="Email length")


# Tool name to schema mapping
TOOL_SCHEMAS: dict[str, type[BaseModel]] = {
    "doc_open": DocOpenArgs,
    "doc_compare": DocCompareArgs,
    "web_search": WebSearchArgs,
    "summarize": SummarizeArgs,
    "write_file": WriteFileArgs,
    "action_items": ActionItemsArgs,
    "meeting_minutes": MeetingMinutesArgs,
    "email_draft": EmailDraftArgs,
}

# Tool names that require user approval
RISKY_TOOLS = {"write_file", "web_search"}


def validate_tool_args(tool_name: str, args: dict[str, Any]) -> tuple[bool, str]:
    """Validate tool arguments against schema.
    
    Returns (success, error_message).
    """
    if tool_name not in TOOL_SCHEMAS:
        return False, f"Unknown tool: {tool_name}"
    
    schema = TOOL_SCHEMAS[tool_name]
    try:
        schema.model_validate(args)
        return True, ""
    except Exception as e:
        return False, str(e)
