# ClawLite: Tiny Agent Specification

**Version**: 0.1.0
**Target Platform**: macOS
**Language**: Python 3.11+
**Purpose**: Terminal-based LLM agent optimized for small local models (7B-8B parameter range)

---

## 1. Project Overview

### 1.1 Goal
Build a reliable, terminal-based AI agent that works effectively with small local LLMs (llama3.1:8b, deepseek-r1:8b) through Ollama. The agent should handle everyday office tasks with:
- Strict output formatting to reduce hallucination
- Single-step tool execution for predictability
- Schema validation with automatic repair
- User approval for risky operations
- Workspace sandboxing for safety

### 1.2 Design Philosophy
Small models (7B-8B) struggle with:
- Complex multi-step reasoning
- Ambiguous output formats
- Arbitrary JSON generation
- Long context windows

**Solution**: Constrain the problem space with:
- Simple ACTION/FINAL output protocol
- One tool call per turn
- Pydantic schema validation
- Compact tool outputs (truncated)
- Clear system prompts with examples

---

## 2. Core Architecture

### 2.1 Control Flow

```
User Input → Orchestrator → LLM (via Ollama)
                ↓
         Parse Output (ACTION or FINAL)
                ↓
         Validate Schema
                ↓
         [Repair Loop if invalid]
                ↓
         Check Policy (approval, workspace)
                ↓
         Execute Tool
                ↓
         Format Result (compact)
                ↓
         Feed back to LLM → Repeat
```

### 2.2 Output Protocol

The LLM MUST output exactly ONE of these blocks per turn:

**ACTION Block** (propose a tool call):
```
ACTION
tool: <tool_name>
args: <json_object>
END_ACTION
```

**FINAL Block** (return answer to user):
```
FINAL
<markdown formatted answer>
END_FINAL
```

**No other output is valid.** If the LLM produces invalid output:
1. Extract the attempted tool/args
2. Repair common issues (quotes, braces, escaping)
3. Validate against tool schema
4. If repair fails after 2 attempts, abort with error

### 2.3 Components

#### `protocol.py`
- Parse ACTION/FINAL blocks from LLM output
- Repair common malformed outputs
- Validate against expected format

#### `schemas.py`
- Pydantic models for each tool's input arguments
- Tool result types
- Validation and serialization

#### `ollama_client.py`
- HTTP client for Ollama API
- Streaming support
- Model health checks
- Error handling for timeouts/connection issues

#### `orchestrator.py`
- Main control loop
- Tool registry and dispatch
- Policy enforcement (workspace, approval)
- Logging and observability

#### `tools/*.py`
- Individual tool implementations
- Each tool has: name, description, schema, execute function
- Tools return structured results (success/error + data)

---

## 3. Tool Specifications

### 3.1 Document Tools

#### `doc_open`
**Purpose**: Open and extract text from PDF, TXT, or MD files.

**Input Schema**:
```python
class DocOpenArgs(BaseModel):
    path: str  # Absolute or relative file path
    pages: Optional[str] = None  # For PDFs: "1-5", "all", or "3,7,9"
```

**Output**:
```python
{
    "success": bool,
    "text": str,  # Truncated to 8000 chars
    "metadata": {
        "file_type": str,
        "page_count": Optional[int],
        "char_count": int
    }
}
```

**Implementation**:
- PDF: Use PyMuPDF (fitz) for text extraction
- TXT/MD: Read with UTF-8 encoding
- Truncate output to 8000 chars with "..." indicator
- Handle missing files gracefully

---

#### `doc_compare`
**Purpose**: Compare two documents side-by-side.

**Input Schema**:
```python
class DocCompareArgs(BaseModel):
    path1: str
    path2: str
    mode: Literal["diff", "summary", "semantic"] = "summary"
```

**Modes**:
- `diff`: Line-by-line textual diff (unified format)
- `summary`: Bullet points of key differences
- `semantic`: Highlight conceptual differences (for small models, just use keyword overlap)

**Output**:
```python
{
    "success": bool,
    "comparison": str,  # Formatted result, truncated to 4000 chars
    "metadata": {
        "doc1_chars": int,
        "doc2_chars": int,
        "similarity_score": float  # 0.0-1.0
    }
}
```

---

#### `summarize`
**Purpose**: Generate structured summaries of text or documents.

**Input Schema**:
```python
class SummarizeArgs(BaseModel):
    source: str  # File path OR raw text
    format: Literal["bullets", "paragraph", "abstract"] = "bullets"
    max_points: int = 5  # For bullet format
```

**Output**:
```python
{
    "success": bool,
    "summary": str,  # Formatted summary
    "word_count": int
}
```

**Implementation**:
- If source is a path, read file first
- Send text to LLM with format instructions
- For small models, use simple extraction prompts

---

### 3.2 Web Tools

#### `web_search`
**Purpose**: Search the web and summarize results.

**Input Schema**:
```python
class WebSearchArgs(BaseModel):
    query: str
    num_results: int = 5  # Max 10
```

**Output**:
```python
{
    "success": bool,
    "results": [
        {
            "title": str,
            "url": str,
            "snippet": str
        }
    ],
    "summary": str  # Auto-generated from snippets
}
```

**Implementation**:
- Use DuckDuckGo (no API key required)
- Use `duckduckgo-search` library
- Rate limit: 1 request per 2 seconds
- Requires user approval (unless `--no-approve`)
- Truncate snippets to 200 chars each

---

### 3.3 Office Productivity Tools

#### `action_items`
**Purpose**: Extract action items from meeting notes or documents.

**Input Schema**:
```python
class ActionItemsArgs(BaseModel):
    source: str  # File path or text
    format: Literal["markdown", "json"] = "markdown"
```

**Output**:
```python
{
    "success": bool,
    "action_items": [
        {
            "task": str,
            "owner": Optional[str],
            "due_date": Optional[str],
            "priority": Optional[Literal["high", "medium", "low"]]
        }
    ],
    "formatted_output": str  # Markdown or JSON
}
```

**Extraction Heuristics** (for small models):
- Look for bullet points with verbs (create, send, review, schedule)
- Detect names (capitalized words after ":", "@", or "assigned to")
- Detect dates (regex for "due X", "by Friday", ISO dates)

---

#### `meeting_minutes`
**Purpose**: Generate structured meeting minutes.

**Input Schema**:
```python
class MeetingMinutesArgs(BaseModel):
    source: str  # File path or raw notes
    meeting_title: Optional[str] = None
    attendees: Optional[List[str]] = None
```

**Output**:
```python
{
    "success": bool,
    "minutes": str,  # Markdown formatted
    "sections": {
        "attendees": List[str],
        "key_points": List[str],
        "decisions": List[str],
        "action_items": List[str]
    }
}
```

**Format Template**:
```markdown
# Meeting Minutes: {title}
**Date**: {date}
**Attendees**: {attendees}

## Key Discussion Points
- ...

## Decisions Made
- ...

## Action Items
- ...
```

---

#### `email_draft`
**Purpose**: Draft professional emails from bullet points or instructions.

**Input Schema**:
```python
class EmailDraftArgs(BaseModel):
    content: str  # Instructions or bullet points
    tone: Literal["formal", "casual", "friendly"] = "formal"
    include_greeting: bool = True
    include_signature: bool = True
```

**Output**:
```python
{
    "success": bool,
    "email": str,  # Full email text
    "subject_suggestion": Optional[str]
}
```

**Template Structure**:
```
Subject: {suggested_subject}

{greeting}

{body_paragraphs}

{closing}
{signature_placeholder}
```

---

### 3.4 File Management Tools

#### `write_file`
**Purpose**: Write content to a file in the workspace.

**Input Schema**:
```python
class WriteFileArgs(BaseModel):
    path: str  # Relative to workspace
    content: str
    mode: Literal["write", "append"] = "write"
```

**Output**:
```python
{
    "success": bool,
    "path": str,  # Absolute path written
    "bytes_written": int
}
```

**Safety**:
- Requires user approval (unless `--no-approve`)
- Must be within workspace if `--workspace` is set
- Creates parent directories if needed
- Handles encoding errors

---

### 3.5 Additional Helpful Office Tools

#### `calendar_parse`
**Purpose**: Parse dates and times from text and suggest calendar entries.

**Input Schema**:
```python
class CalendarParseArgs(BaseModel):
    text: str  # Text containing date/time references
    timezone: str = "America/Los_Angeles"  # macOS default
```

**Output**:
```python
{
    "success": bool,
    "events": [
        {
            "title": str,
            "start_datetime": str,  # ISO 8601
            "end_datetime": Optional[str],
            "location": Optional[str],
            "notes": str
        }
    ],
    "ical_format": str  # Ready to import
}
```

**Implementation**:
- Use regex + dateutil for parsing
- Handle relative dates ("next Tuesday", "in 2 weeks")
- Generate .ics file content for macOS Calendar import

---

#### `text_extract_structured`
**Purpose**: Extract structured data from unstructured text (names, emails, phone numbers, addresses).

**Input Schema**:
```python
class ExtractStructuredArgs(BaseModel):
    source: str  # File path or text
    extract: List[Literal["emails", "phones", "urls", "names", "addresses"]]
```

**Output**:
```python
{
    "success": bool,
    "extracted": {
        "emails": List[str],
        "phones": List[str],
        "urls": List[str],
        "names": List[str],
        "addresses": List[str]
    },
    "formatted": str  # Markdown table
}
```

**Implementation**:
- Use regex for emails, phones, URLs
- Use spaCy (if available) or simple heuristics for names
- Format as markdown table for easy copying

---

#### `expense_report`
**Purpose**: Parse receipts/expenses and generate a summary report.

**Input Schema**:
```python
class ExpenseReportArgs(BaseModel):
    source: str  # File with expense data
    currency: str = "USD"
    format: Literal["markdown", "csv"] = "markdown"
```

**Output**:
```python
{
    "success": bool,
    "expenses": [
        {
            "date": str,
            "vendor": str,
            "amount": float,
            "category": str,
            "description": str
        }
    ],
    "total": float,
    "formatted_report": str
}
```

**Implementation**:
- Parse common expense formats (CSV, receipt text)
- Use LLM to extract amount, vendor, category
- Generate markdown table with totals

---

## 4. CLI Interface

### 4.1 Command Structure

```bash
clawlite [OPTIONS] [TASK]
```

### 4.2 Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--workspace` | `-w` | PATH | `./` | Restrict file operations to this directory |
| `--model` | `-m` | STR | `llama3.1:8b-instruct` | Ollama model name |
| `--approve` | `-a` | FLAG | `True` | Ask before writes/web searches |
| `--no-approve` | `-A` | FLAG | - | Skip approval prompts |
| `--dry-run` | `-d` | FLAG | `False` | Show actions without executing |
| `--max-steps` | `-s` | INT | `20` | Max steps before stopping |
| `--log` | `-l` | PATH | - | Save JSONL logs to file |
| `--no-web` | | FLAG | `False` | Disable web search tool |
| `--version` | `-v` | FLAG | - | Show version |
| `--help` | | FLAG | - | Show help |

### 4.3 Usage Examples

```bash
# Interactive mode
clawlite

# Summarize a document
clawlite "Summarize quarterly_report.pdf"

# Compare two files
clawlite "Compare draft_v1.md and draft_v2.md"

# Extract action items
clawlite "Extract action items from team_meeting.txt"

# Draft an email
clawlite "Draft a formal email thanking the client for their business"

# Web search and summarize
clawlite "Search for Python async best practices 2024"

# With workspace restriction
clawlite -w ~/Documents/project "Summarize all markdown files"

# With different model
clawlite -m deepseek-r1:8b "Compare report1.pdf and report2.pdf"

# Dry run mode
clawlite -d "Write a summary to output.txt"
```

---

## 5. Technical Requirements

### 5.1 Dependencies

**Core**:
- `typer>=0.12.0` - CLI framework
- `rich>=13.0.0` - Terminal formatting
- `pydantic>=2.0.0` - Schema validation
- `httpx>=0.27.0` - Ollama API client

**Document Processing**:
- `pymupdf>=1.24.0` - PDF text extraction
- `beautifulsoup4>=4.12.0` - HTML parsing (for web)
- `readability-lxml>=0.8.1` - Web article extraction

**Web Search**:
- `duckduckgo-search>=5.0.0` - DuckDuckGo search

**Date/Time**:
- `python-dateutil>=2.8.0` - Date parsing
- `icalendar>=5.0.0` - Calendar file generation

**Development**:
- `pytest>=8.0.0`
- `pytest-asyncio>=0.23.0`
- `black>=24.0.0`
- `ruff>=0.4.0`

### 5.2 Python Version
- Minimum: Python 3.11
- Recommended: Python 3.12

### 5.3 External Requirements
- Ollama installed and running (`brew install ollama` on macOS)
- At least one model pulled (e.g., `ollama pull llama3.1:8b-instruct`)

---

## 6. Implementation Details

### 6.1 Project Structure

```
tiny-agent/
├── clawlite/
│   ├── __init__.py
│   ├── __main__.py           # CLI entry point
│   ├── orchestrator.py       # Main control loop
│   ├── protocol.py           # ACTION/FINAL parser
│   ├── schemas.py            # Pydantic models
│   ├── ollama_client.py      # Ollama HTTP client
│   ├── prompts.py            # System prompts
│   └── tools/
│       ├── __init__.py
│       ├── doc_open.py
│       ├── doc_compare.py
│       ├── summarize.py
│       ├── web_search.py
│       ├── action_items.py
│       ├── meeting_minutes.py
│       ├── email_draft.py
│       ├── write_file.py
│       ├── calendar_parse.py
│       ├── text_extract_structured.py
│       └── expense_report.py
├── tests/
│   ├── __init__.py
│   ├── test_protocol.py
│   ├── test_schemas.py
│   ├── test_tools.py
│   └── fixtures/
│       ├── sample.pdf
│       ├── sample.txt
│       └── sample.md
├── pyproject.toml
├── README.md
├── SPEC.md
└── LICENSE
```

### 6.2 System Prompt Strategy

**For small models, the system prompt must be**:
1. **Concise** (< 1000 tokens)
2. **Explicit** (show exact format)
3. **Example-driven** (show 2-3 examples)

**Template**:
```
You are a helpful agent that uses tools to complete tasks.

OUTPUT RULES:
1. Output EXACTLY one ACTION or FINAL block per turn
2. Never output both
3. Never output anything else

FORMAT:
ACTION
tool: tool_name
args: {"key": "value"}
END_ACTION

Or:

FINAL
Your final answer here in markdown.
END_FINAL

EXAMPLES:
User: "Summarize report.pdf"
Assistant:
ACTION
tool: doc_open
args: {"path": "report.pdf"}
END_ACTION

[After tool result]
Assistant:
FINAL
## Summary of report.pdf
- Key point 1
- Key point 2
- Key point 3
END_FINAL

AVAILABLE TOOLS:
{tool_list_with_schemas}
```

### 6.3 Error Handling

**Levels**:
1. **Tool Execution Errors**: Catch exceptions, return error result to LLM
2. **Protocol Errors**: Attempt repair, fallback to error message
3. **Ollama Connection Errors**: Retry with backoff, abort after 3 attempts
4. **Validation Errors**: Show user the invalid output, ask to retry

**Logging**:
- Log all LLM inputs/outputs to JSONL (if `--log` specified)
- Log tool calls and results
- Log validation failures and repairs

### 6.4 Safety and Sandboxing

**Workspace Enforcement**:
```python
def check_workspace(path: str, workspace: Path) -> bool:
    resolved = Path(path).resolve()
    return resolved.is_relative_to(workspace)
```

**Approval Prompts**:
- Show exact operation before execution
- Options: [y]es, [n]o, [a]lways, [q]uit
- Store "always" decisions in memory (per session)

**Rate Limiting**:
- Web searches: 1 per 2 seconds
- Tool calls: No limit (but max_steps applies)

**Output Truncation**:
- Tool results: 8000 chars max
- Web snippets: 200 chars each
- Total context: Keep under 4000 tokens for small models

---

## 7. Testing Requirements

### 7.1 Unit Tests

**Protocol Parser** (`test_protocol.py`):
- Parse valid ACTION blocks
- Parse valid FINAL blocks
- Detect and repair malformed JSON
- Handle edge cases (newlines, quotes, braces)

**Schemas** (`test_schemas.py`):
- Validate all tool input schemas
- Test required vs optional fields
- Test type coercion

**Tools** (`test_tools.py`):
- Mock file system for doc_open, write_file
- Mock HTTP responses for web_search
- Test error handling (missing files, invalid inputs)

### 7.2 Integration Tests

**End-to-End**:
- Full orchestrator loop with mock LLM
- Test multi-step tasks
- Test approval flow
- Test workspace restriction

### 7.3 Test Fixtures
- `sample.pdf` (3-page document)
- `sample.txt` (meeting notes)
- `sample.md` (markdown document)
- Mock Ollama responses (JSON)

---

## 8. Performance Targets

**For 8B models on MacBook Pro (M1/M2)**:
- Token generation: 20-50 tokens/sec
- Action parsing: < 50ms
- Tool execution: < 2 sec (local files), < 5 sec (web)
- Full turn latency: 3-10 seconds

**Context Budget**:
- System prompt: ~800 tokens
- Tool results: ~500 tokens each (truncated)
- Max history: 10 turns (keep only essential context)

---

## 9. Future Enhancements (Post-MVP)

1. **Multi-file operations**: Process directory of documents
2. **Streaming output**: Show LLM response as it generates
3. **Tool chaining**: Pre-plan multiple steps (for larger models)
4. **Context caching**: Reuse document embeddings
5. **Plugin system**: User-defined tools
6. **Web UI**: Simple browser interface (optional)
7. **Voice input**: macOS speech recognition integration

---

## 10. Success Criteria

**MVP is successful if**:
1. Reliably executes 8/10 single-step tasks on first try (8B models)
2. Completes 6/10 multi-step tasks within 10 steps
3. Generates valid ACTION blocks >90% of the time
4. Zero unsafe operations without approval
5. Handles common errors gracefully (missing files, network issues)

**Usability**:
- Clear error messages
- Fast response time (< 10 sec per turn)
- No crashes on malformed LLM output
- Works offline (except web search)

---

## 11. Development Roadmap

### Phase 1: Core Infrastructure (Week 1)
- [ ] Set up project structure and dependencies
- [ ] Implement Ollama client with basic error handling
- [ ] Implement protocol parser with repair loop
- [ ] Define Pydantic schemas for all tools
- [ ] Set up CLI with Typer

### Phase 2: Document Tools (Week 2)
- [ ] Implement `doc_open` (PDF, TXT, MD)
- [ ] Implement `doc_compare` (diff, summary modes)
- [ ] Implement `summarize` tool
- [ ] Write unit tests for document tools

### Phase 3: Web and Write Tools (Week 3)
- [ ] Implement `web_search` with DuckDuckGo
- [ ] Implement `write_file` with workspace checks
- [ ] Add approval flow for risky operations
- [ ] Test rate limiting and error handling

### Phase 4: Office Productivity Tools (Week 4)
- [ ] Implement `action_items` extractor
- [ ] Implement `meeting_minutes` generator
- [ ] Implement `email_draft` generator
- [ ] Implement `calendar_parse` tool
- [ ] Implement `text_extract_structured` tool
- [ ] Implement `expense_report` tool

### Phase 5: Orchestrator and Integration (Week 5)
- [ ] Implement orchestrator main loop
- [ ] Add policy enforcement (workspace, approval)
- [ ] Add logging and observability
- [ ] Integration tests with mock LLM
- [ ] End-to-end testing with real Ollama models

### Phase 6: Polish and Documentation (Week 6)
- [ ] Refine error messages and user feedback
- [ ] Add examples to README
- [ ] Performance profiling and optimization
- [ ] Create demo video
- [ ] Package for distribution

---

## 12. Open Questions

1. **Model selection**: Should we support model switching mid-session?
2. **Context management**: How many turns should we keep in history?
3. **Tool composability**: Should we allow tools to call other tools?
4. **Streaming**: Should we stream LLM output to terminal (rich.live)?
5. **Caching**: Should we cache document content between turns?

---

## 13. References

- Ollama API: https://github.com/ollama/ollama/blob/main/docs/api.md
- PyMuPDF docs: https://pymupdf.readthedocs.io/
- Pydantic validation: https://docs.pydantic.dev/
- Typer CLI: https://typer.tiangolo.com/

---

**Document Status**: Draft v1.0
**Last Updated**: 2026-02-16
**Author**: Project Specification for ClawLite
