# ClawLite: Tiny Agent Specification v2.0

**Version**: 0.2.0
**Target Platform**: macOS
**Language**: Python 3.11+
**Purpose**: Terminal-based LLM agent optimized for small local models (7B-8B parameter range)
**Deployment**: 100% local execution via Ollama (no API costs)

---

## 1. Project Overview

### 1.1 Goal
Build a reliable, terminal-based AI agent that works effectively with small local LLMs (llama3.1:8b, deepseek-r1:8b) through Ollama. Focus on document processing and office productivity with:
- **Ollama JSON mode** for structured outputs
- **Folder/batch document processing**
- **Multi-step state management**
- **Live progress feedback**
- **Robust error recovery**

### 1.2 Design Philosophy
Small models (7B-8B) work best with:
- ✅ Structured JSON output (Ollama's native format)
- ✅ Clear tool schemas with examples
- ✅ Single-step reasoning
- ✅ Explicit state between turns
- ✅ Visual progress indicators

---

## 2. Core Architecture

### 2.1 Control Flow

```
User Input → Orchestrator → LLM (Ollama JSON mode)
                ↓
         Parse JSON Output (tool + args OR final)
                ↓
         Validate Against Tool Schema
                ↓
         [Repair Loop if malformed: max 2 attempts]
                ↓
         Check Policy (approval, workspace)
                ↓
         Execute Tool (with rich.live progress)
                ↓
         Update Context State
                ↓
         Format Result (compact + summary)
                ↓
         Feed back to LLM → Repeat (max 20 steps)
```

### 2.2 Output Protocol: Ollama JSON Mode

**All LLM responses use Ollama's `format: "json"` parameter.**

The LLM MUST output exactly this JSON structure:

```json
{
  "action": "tool_name",
  "args": {
    "param1": "value1",
    "param2": "value2"
  },
  "reasoning": "Brief explanation of why this action"
}
```

**OR for final answer:**

```json
{
  "action": "final",
  "result": "Markdown formatted final answer to user"
}
```

**Key fields:**
- `action` (required): Tool name OR "final"
- `args` (required if action != "final"): Tool parameters as object
- `reasoning` (optional): For debugging, not shown to user
- `result` (required if action == "final"): Final markdown output

### 2.3 Repair Loop for Malformed JSON

Even with JSON mode, small models can produce invalid output. The repair loop:

**Attempt 1**: Parse JSON
- If valid → proceed to validation
- If invalid → apply common fixes

**Common Fixes**:
1. Add missing closing braces/brackets
2. Escape unescaped quotes in strings
3. Remove trailing commas
4. Fix common typos: `"action"` vs `"act"`, `"args"` vs `"arguments"`
5. Convert single quotes to double quotes

**Attempt 2**: Re-prompt LLM with error message
```
Your previous output was invalid JSON:
{error_message}

Please output valid JSON following this exact format:
{schema_example}
```

**Attempt 3**: If still invalid, abort with error to user

**Implementation**: Use `json.loads()` with custom `JSONDecoder` for common repairs.

### 2.4 Context State Management (Multi-Step Memory)

For tasks requiring multiple steps, the orchestrator maintains a **context state** between turns:

```python
class ContextState:
    step_number: int = 0
    max_steps: int = 20
    task_description: str  # Original user request
    completed_actions: List[Dict]  # History of tool calls
    intermediate_results: Dict[str, Any]  # Key-value store for results
    token_budget_used: int = 0
    token_budget_limit: int = 6000  # For 8K context models
```

**Example multi-step task:**
```
User: "Compare all invoices in the folder and create a summary report"

Step 1: ACTION doc_open with folder path
        → State stores: {"invoice_texts": [...]}

Step 2: ACTION summarize with all invoice data
        → State stores: {"summary": "..."}

Step 3: ACTION write_file with summary
        → FINAL
```

The state is passed to the LLM as:
```json
{
  "current_step": 2,
  "max_steps": 20,
  "completed": [
    {"action": "doc_open", "status": "success", "files_found": 5}
  ],
  "available_data": {
    "invoice_texts": "5 documents loaded"
  }
}
```

### 2.5 Token Budget (Local Models)

Since computation is **100% local** (no API costs), the only constraint is **context window size**:

**For 8B models with 8K context:**
- System prompt: 800 tokens
- Tool schemas: 600 tokens
- Context state: 400 tokens
- Tool result (per turn): 1000 tokens max
- User message: 200 tokens
- LLM response buffer: 500 tokens
- History (last 3 turns): 2500 tokens
- **Total budget: ~6000 tokens** (leaving 2K margin)

**For larger contexts (32K models like deepseek-r1:8b):**
- Scale linearly: 24,000 token budget

**Truncation Strategy:**
- Tool outputs: Truncate to 1000 tokens with "... (truncated)" marker
- Document texts: First 800 + last 200 tokens
- History: Keep only last 3 turns, summarize older turns

**Time Expectations:**
- 8B model on M1 Mac: ~30 tokens/sec
- Typical response: 200 tokens = ~7 seconds
- Multi-step task (5 steps): ~45 seconds
- **Target: Complete simple tasks in < 1 minute**

### 2.6 Progress Feedback with rich.live

Use `rich.live.Live` for real-time status updates:

```python
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel

with Live(Spinner("dots", text="Thinking..."), refresh_per_second=10) as live:
    # Update status as work progresses
    live.update(Panel("🔍 Opening documents...", title="Step 1/3"))
    # ... tool execution ...
    live.update(Panel("✅ Loaded 5 invoices\n📝 Generating summary...", title="Step 2/3"))
```

**Status Indicators:**
- 🤔 Waiting for LLM response
- 🔍 Reading files
- 📝 Processing documents
- 🌐 Searching web
- ✍️ Writing files
- ✅ Success
- ❌ Error
- ⏭️ Moving to next step

---

## 3. Tool Specifications

### 3.1 Enhanced Document Tools

#### `doc_open`
**Purpose**: Open and extract text from single file OR all files in a folder.

**Input Schema**:
```json
{
  "path": "string (file or folder path)",
  "recursive": "boolean (search subfolders, default: false)",
  "file_types": ["pdf", "txt", "md"] (filter types, default: all)
}
```

**Behavior**:
- If `path` is a file: Extract text from that file
- If `path` is a folder: Extract text from all matching files
- Return metadata + combined/individual texts

**Output**:
```json
{
  "success": true,
  "files_processed": 5,
  "sources": [
    {
      "path": "invoice1.pdf",
      "type": "pdf",
      "pages": 2,
      "chars": 1523,
      "excerpt": "First 200 chars..."
    }
  ],
  "combined_text": "Full text of all files, separated by \\n---\\n",
  "metadata": {
    "total_chars": 8432,
    "total_files": 5,
    "file_types": {"pdf": 5}
  }
}
```

**Implementation Notes**:
- Use `pymupdf` for PDFs
- Use `pathlib.Path.glob()` for folder scanning
- Truncate combined_text to 8000 chars total
- Store individual file texts in state for later reference

---

#### `summarize`
**Purpose**: Generate structured summaries of documents or text.

**Input Schema**:
```json
{
  "source": "string (file path, folder path, or raw text)",
  "format": "bullets | paragraph | structured (default: structured)",
  "focus": "optional string (what to focus on: dates, amounts, people, etc.)"
}
```

**For multi-document summaries:**
- Use `doc_open` first to load documents into state
- Then call LLM with special summarization prompt
- Generate cross-document insights

**Output**:
```json
{
  "success": true,
  "summary": "Markdown formatted summary",
  "sources": ["file1.pdf", "file2.pdf"],
  "key_points": [
    "Point 1",
    "Point 2"
  ],
  "metadata": {
    "source_count": 5,
    "summary_length": 342
  }
}
```

**Structured Format Example** (for invoices):
```markdown
## Summary of 5 Invoices

**Period**: November 2025 - January 2026
**Total Amount**: €6,759.98

### By Contractor:
- **Alice Smith**: €7,600.00 (152h) - Software Development
- **Bob Johnson**: €4,641.00 (65h) - Technical Consulting
- **Carol Martinez**: €11,453.75 (175h) - Database Administration

### By Month:
- November 2025: €3,600.00
- December 2025: €10,204.25
- January 2026: €9,890.50

### Client:
All invoices for TechCorp GmbH (fictional company).

### Sources:
- `invoice_2025_11_contractor_a.md`
- `invoice_2025_12_contractor_b.md`
- `invoice_2025_12_contractor_c.md`
- `invoice_2026_01_contractor_a.md`
- `invoice_2026_01_contractor_c.md`

*Note: All test data is completely fictional*
```

---

### 3.2 Office Productivity Tools (Refined)

#### `action_items`
**Purpose**: Extract action items with owners, due dates, priority.

**Input Schema**:
```json
{
  "source": "string (file path or text)",
  "format": "markdown | json (default: markdown)"
}
```

**Output**:
```json
{
  "success": true,
  "action_items": [
    {
      "task": "Review Q4 report",
      "owner": "John Smith",
      "due_date": "2026-02-20",
      "priority": "high",
      "context": "Mentioned in meeting notes line 42"
    }
  ],
  "formatted": "Markdown checklist"
}
```

---

#### `meeting_minutes`
**Purpose**: Generate structured meeting minutes.

**Input Schema**:
```json
{
  "source": "string (file path or raw notes)",
  "meeting_title": "optional string",
  "attendees": ["optional", "list"]
}
```

**Output**: Structured markdown with sections for attendees, discussion, decisions, actions.

---

#### `email_draft`
**Purpose**: Draft professional emails.

**Input Schema**:
```json
{
  "content": "Instructions or bullet points",
  "tone": "formal | casual | friendly (default: formal)",
  "include_subject": true
}
```

**Output**: Email with subject line and body.

---

### 3.3 Additional Helper Tools

#### `calendar_parse`
**Purpose**: Extract dates/times and generate .ics files.

**Input Schema**:
```json
{
  "text": "Text containing dates",
  "timezone": "America/Los_Angeles (default: system)"
}
```

**Output**: List of events + .ics file content.

**Implementation**: Use `dateutil.parser` + `icalendar` library.

---

#### `text_extract_structured`
**Purpose**: Extract emails, phones, URLs, etc.

**Input Schema**:
```json
{
  "source": "file or text",
  "extract": ["emails", "phones", "urls", "names", "addresses"]
}
```

**Output**: Structured data as markdown table.

**Implementation**: Regex patterns, no NLP needed for MVP.

---

#### `expense_report`
**Purpose**: Parse text-based expense data (NO OCR).

**Input Schema**:
```json
{
  "source": "file path (CSV, TXT, or structured PDF)",
  "currency": "EUR (default: EUR)",
  "format": "markdown | csv"
}
```

**Output**: Expense table with totals.

**Implementation**:
- Parse CSV directly
- For PDFs with text: Extract tabular data using regex
- For unstructured text: Use LLM to extract amounts, vendors, dates
- **No OCR**: Assume PDFs are text-based (like the sample invoices)

---

### 3.4 File Management

#### `write_file`
**Purpose**: Write content to workspace.

**Input Schema**:
```json
{
  "path": "relative path",
  "content": "text content",
  "mode": "write | append (default: write)"
}
```

**Output**: Success message with path.

**Safety**: Always requires approval unless `--no-approve`.

---

## 4. CLI Interface

### 4.1 Command Structure

```bash
clawlite [OPTIONS] [TASK]
```

### 4.2 Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--workspace` | `-w` | PATH | `./` | Restrict operations to directory |
| `--model` | `-m` | STR | `llama3.1:8b-instruct` | Ollama model |
| `--approve` | `-a` | FLAG | `True` | Ask before writes/web |
| `--no-approve` | `-A` | FLAG | - | Skip approval |
| `--dry-run` | `-d` | FLAG | `False` | Show actions only |
| `--max-steps` | `-s` | INT | `20` | Max steps before stop |
| `--log` | `-l` | PATH | - | Save logs to JSONL |
| `--no-web` | | FLAG | `False` | Disable web search |
| `--version` | `-v` | FLAG | - | Show version |
| `--help` | | FLAG | - | Show help |

### 4.3 Usage Examples

```bash
# Summarize all invoices in current folder
clawlite "Summarize all PDF invoices in this folder"

# Compare two documents
clawlite "Compare draft_v1.md and draft_v2.md"

# Extract action items
clawlite "Extract action items from meeting_notes.txt"

# Multi-step: read folder, summarize, save
clawlite "Read all markdown files, create a summary, and save to summary.txt"

# With workspace restriction
clawlite -w ~/Documents/invoices "Summarize all invoices"

# With different model
clawlite -m deepseek-r1:8b "Analyze quarterly_report.pdf"
```

---

## 5. Test Cases

### 5.1 Invoice Summary Test Case

**Test ID**: `test_invoice_summary_001`

**Input Files** (in `tests/fixtures/invoices/`):
1. `invoice_2026_01_contractor_a.md` - Alice Smith, Jan 2026, 80h @ €50 = €4,000
2. `invoice_2025_12_contractor_b.md` - Bob Johnson, Dec 2025, 65h @ €60 = €4,641
3. `invoice_2025_11_contractor_a.md` - Alice Smith, Nov 2025, 72h @ €50 = €3,600
4. `invoice_2026_01_contractor_c.md` - Carol Martinez, Jan 2026, 90h @ €55 = €5,890.50
5. `invoice_2025_12_contractor_c.md` - Carol Martinez, Dec 2025, 85h @ €55 = €5,563.25
*Note: All test data is completely fictional (TechCorp GmbH)*

**Command**:
```bash
clawlite -w tests/fixtures/invoices "Summarize all invoices"
```

**Expected Steps**:
1. ACTION `doc_open` with path=".", recursive=false, file_types=["pdf"]
2. ACTION `summarize` with loaded documents
3. FINAL with summary

**Expected Output** (see `tests/expected_outputs/invoice_summary.md`):

```markdown
## Invoice Summary Report

**Analysis of 5 Invoices**
**Period**: November 2025 - January 2026
**Client**: TechCorp GmbH (Fictional)
**Total Amount**: €23,694.75

### Breakdown by Contractor

| Contractor | Invoices | Total Hours | Total Amount |
|-----------|----------|-------------|--------------|
| Alice Smith | 2 | 152h | €7,600.00 |
| Bob Johnson | 1 | 65h | €4,641.00 |
| Carol Martinez | 2 | 175h | €11,453.75 |

### Monthly Breakdown

| Month | Amount | Hours |
|-------|--------|-------|
| November 2025 | €3,600.00 | 72h |
| December 2025 | €10,204.25 | 150h |
| January 2026 | €9,890.50 | 170h |

### Work Description
All invoices are for software development and IT services (Fictional):
- Software Development (Alice Smith)
- Technical Consulting (Bob Johnson)
- Database Administration (Carol Martinez)

### Key Details
- **Payment Terms**: Net 30 days
- **Tax Status**:
  - Alice Smith: No VAT (Kleinunternehmer)
  - Bob Johnson & Carol Martinez: 19% VAT included
- **Hourly Rates**: €50-60/hour

### Sources
1. `invoice_2026_01_contractor_a.md` (INV-2026-001)
2. `invoice_2025_12_contractor_b.md` (INV-2025-017)
3. `invoice_2025_11_contractor_a.md` (INV-2025-016)
4. `invoice_2026_01_contractor_c.md` (INV-2026-002)
5. `invoice_2025_12_contractor_c.md` (INV-2025-018)
```

**Acceptance Criteria**:
- ✅ All 5 invoices loaded
- ✅ Total amount calculated correctly
- ✅ Contractor names extracted
- ✅ Dates parsed correctly
- ✅ Summary is structured and readable
- ✅ Sources listed with filenames

---

## 6. Implementation Details

### 6.1 Project Structure

```
tiny-agent/
├── clawlite/
│   ├── __init__.py
│   ├── __main__.py           # CLI entry
│   ├── orchestrator.py       # Main loop with context state
│   ├── ollama_client.py      # Ollama HTTP client (JSON mode)
│   ├── protocol.py           # JSON parser + repair loop
│   ├── schemas.py            # Pydantic models
│   ├── prompts.py            # System prompts for each tool
│   ├── context_state.py      # Multi-step state management
│   └── tools/
│       ├── __init__.py
│       ├── doc_open.py       # With folder support
│       ├── summarize.py      # Multi-doc aware
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
│   ├── test_tools.py
│   ├── test_invoice_summary.py
│   ├── fixtures/
│   │   └── invoices/         # 5 sample invoices
│   └── expected_outputs/
│       └── invoice_summary.md
├── pyproject.toml
├── SPEC_v2.md
└── README.md
```

### 6.2 Ollama Client with JSON Mode

```python
import httpx
import json

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", model="llama3.1:8b-instruct"):
        self.base_url = base_url
        self.model = model

    def generate(self, prompt: str, system: str = None, format="json") -> dict:
        """
        Call Ollama with JSON format enforcement.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": format,  # "json" enforces structured output
            "options": {
                "temperature": 0.1,  # Low temp for consistency
                "num_predict": 500   # Max tokens per response
            }
        }

        if system:
            payload["system"] = system

        response = httpx.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=120.0
        )

        response.raise_for_status()
        result = response.json()

        # Parse JSON from response
        output_text = result["response"]
        return json.loads(output_text)
```

### 6.3 System Prompt Template

```
You are a helpful office assistant that uses tools to complete tasks.

IMPORTANT OUTPUT FORMAT:
You MUST respond with valid JSON only. No other text.

For tool actions:
{
  "action": "tool_name",
  "args": {
    "param1": "value",
    "param2": "value"
  },
  "reasoning": "why this action"
}

For final answer:
{
  "action": "final",
  "result": "Your markdown-formatted answer here"
}

AVAILABLE TOOLS:
{tool_descriptions}

CURRENT CONTEXT:
- Step: {step_number}/{max_steps}
- Completed actions: {completed_actions}
- Available data: {available_data}

EXAMPLES:
User: "Summarize report.pdf"
{
  "action": "doc_open",
  "args": {"path": "report.pdf"},
  "reasoning": "Need to read the file first"
}

[After receiving file content]
{
  "action": "final",
  "result": "## Summary\\n- Key point 1\\n- Key point 2"
}

Now respond to: {user_query}
```

### 6.4 Token Budget Tracking

```python
class TokenBudget:
    def __init__(self, max_tokens=6000):
        self.max_tokens = max_tokens
        self.used_tokens = 0
        self.system_prompt_tokens = 800
        self.tool_schemas_tokens = 600

    def estimate_tokens(self, text: str) -> int:
        """Rough estimate: 1 token ≈ 4 characters"""
        return len(text) // 4

    def can_fit(self, text: str) -> bool:
        estimated = self.estimate_tokens(text)
        return (self.used_tokens + estimated) < self.max_tokens

    def truncate_if_needed(self, text: str, max_tokens=1000) -> str:
        estimated = self.estimate_tokens(text)
        if estimated > max_tokens:
            # Keep first 80% and last 20%
            chars_limit = max_tokens * 4
            first_part = int(chars_limit * 0.8)
            last_part = int(chars_limit * 0.2)
            return text[:first_part] + "\n\n... (truncated) ...\n\n" + text[-last_part:]
        return text
```

---

## 7. Development Roadmap (Minimal MVP)

### Phase 1: Core Infrastructure (Week 1)
- [x] Project setup with pyproject.toml
- [ ] Ollama client with JSON mode
- [ ] JSON protocol parser with repair loop
- [ ] Pydantic schemas for all tools
- [ ] CLI with Typer + rich.live progress
- [ ] Context state management

### Phase 2: Essential Tools (Week 2)
- [ ] `doc_open` with folder support
- [ ] `summarize` tool
- [ ] `write_file` tool
- [ ] Basic orchestrator loop
- [ ] Unit tests for tools

### Phase 3: Invoice Test Case (Week 3)
- [ ] Set up test fixtures with 5 sample invoices
- [ ] Implement invoice summary test
- [ ] Validate against expected output
- [ ] Debug and refine prompts

### Phase 4: Remaining Tools (Week 4)
- [ ] `action_items`, `meeting_minutes`, `email_draft`
- [ ] `calendar_parse`, `text_extract_structured`, `expense_report`
- [ ] Integration tests

### Phase 5: Polish (Week 5)
- [ ] Error handling improvements
- [ ] Progress feedback refinement
- [ ] Documentation
- [ ] README with examples

---

## 8. Success Criteria

**MVP is successful if:**
1. ✅ Invoice summary test case passes with >90% accuracy
2. ✅ Handles folder with 5+ documents reliably
3. ✅ Completes multi-step tasks within 20 steps
4. ✅ JSON output is valid >95% of the time
5. ✅ Progress feedback is clear and helpful
6. ✅ Runs locally with no external API calls
7. ✅ Response time < 60 seconds for typical tasks

---

## 9. Open Questions (RESOLVED)

1. ~~**LLM-powered tools**~~ → Use LLM for summarize, send full text in prompt
2. ~~**Context management**~~ → Explicit ContextState class with token budget
3. ~~**Model compatibility**~~ → Test with both llama3.1:8b and deepseek-r1:8b, use JSON mode
4. ~~**Repair loop**~~ → Max 2 attempts with specific regex fixes
5. ~~**Expense report OCR**~~ → No OCR, text-based PDFs only
6. ~~**Multi-step memory**~~ → Context state with intermediate_results dict
7. ~~**Progress feedback**~~ → rich.live with status indicators
8. ~~**Cost constraint**~~ → No cost (local), only time constraint (~1 min target)

---

**Document Status**: v2.0 - Ready for Implementation
**Last Updated**: 2026-02-16
**Next Step**: Begin Phase 1 - Core Infrastructure
