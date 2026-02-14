"""Tools module for clawlite."""

from .doc_open import doc_open_tool
from .doc_compare import doc_compare_tool
from .web_search import web_search_tool
from .summarize import summarize_tool
from .write_file import write_file_tool
from .action_items import action_items_tool
from .meeting_minutes import meeting_minutes_tool
from .email_draft import email_draft_tool

__all__ = [
    "doc_open_tool",
    "doc_compare_tool",
    "web_search_tool",
    "summarize_tool",
    "write_file_tool",
    "action_items_tool",
    "meeting_minutes_tool",
    "email_draft_tool",
]
