# Changelog

All notable changes to ClawLite will be documented in this file.

---

## [0.2.0] - 2026-02-16

### 🎉 Initial MVP Release

#### Added
- **Core Infrastructure**
  - Ollama client with JSON mode support (`ollama_client.py`)
  - JSON protocol parser with automatic repair loop (`protocol.py`)
  - Main orchestrator with multi-step reasoning (`orchestrator.py`)
  - CLI interface with rich formatting (`__main__.py`)

- **Tools**
  - `doc_open` - Opens and extracts text from PDF/TXT/MD files
    - Supports single files and entire folders
    - Folder scanning with file type filtering
    - Metadata extraction (file count, char count, sources)
    - Text truncation to 6000 chars for performance

- **Features**
  - Multi-step task execution (up to 20 steps)
  - Live progress indicators with rich UI
  - Error handling with graceful fallbacks
  - Support for multiple Ollama models (3B-8B range)
  - Workspace directory support

- **Documentation**
  - README.md - Quick start and usage guide
  - INSTALL.md - Installation instructions
  - SPEC_v2.md - Complete technical specification
  - MINIMAL_MVP_GUIDE.md - 7-day implementation guide
  - MVP_STATUS.md - Current status and features
  - TESTING_RESULTS.md - Test results and performance metrics
  - CHANGELOG.md - This file

- **Tests**
  - Test fixtures with 5 real invoice PDFs
  - Python test suite (`tests/test_summaries.py`)
  - Shell test script (`tests/test_individual_summaries.sh`)
  - Expected output documentation

#### Performance
- Single document: ~20 seconds with llama3.1:8b
- Multiple documents (5): ~35 seconds with llama3.1:8b
- Fast mode (llama3.2:3b): ~15 seconds
- Character limit: 6000 chars (fits 4-5 typical invoices)
- Token limit: 1500 tokens per response
- Timeout: 60 seconds

#### Supported Models
- ✅ llama3.1:8b - Recommended (best quality)
- ✅ llama3.2:3b - Fastest (good for quick tasks)
- ✅ deepseek-r1:8b - Advanced reasoning (slower)

#### Known Limitations
- Document truncation at 6000 chars (may miss some content in large files)
- Total calculations approximate (±5% accuracy)
- Source filenames sometimes generic in summaries
- No write operations yet (read-only MVP)
- No approval prompts yet
- Limited to single-step tool execution per turn

---

## [0.1.0] - 2026-02-16 (Initial Development)

### Internal Development Milestones

#### Day 1-2: Foundation
- Project structure setup
- pyproject.toml configuration
- Ollama client implementation
- JSON protocol with repair loop

#### Day 3-4: Tools
- Document opening tool with folder support
- PDF text extraction with PyMuPDF
- Text file and markdown support

#### Day 5-6: Orchestrator
- Main control loop implementation
- Multi-step reasoning
- System prompt optimization for small models
- Progress feedback with rich.live

#### Day 7: Testing & Polish
- CLI interface with typer
- Test suite creation
- Performance optimization (char limits, token limits)
- Bug fixes and refinements

---

## Upcoming (Roadmap)

### [0.3.0] - Planned
- [ ] `write_file` tool
- [ ] `action_items` extractor
- [ ] `meeting_minutes` generator
- [ ] `email_draft` tool
- [ ] Approval prompts for write operations
- [ ] Workspace sandboxing improvements

### [0.4.0] - Planned
- [ ] `calendar_parse` tool
- [ ] `text_extract_structured` tool (emails, phones, URLs)
- [ ] `expense_report` tool with exact parsing
- [ ] Context state management improvements
- [ ] Better token budget tracking

### [0.5.0] - Planned
- [ ] Web search integration
- [ ] Streaming output support
- [ ] Configuration file support
- [ ] Persistent memory/context
- [ ] Plugin system for custom tools

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 0.2.0 | 2026-02-16 | Initial MVP release with doc_open tool |
| 0.1.0 | 2026-02-16 | Internal development version |

---

## Breaking Changes

None yet (initial release)

---

## Migration Guide

Not applicable (initial release)

---

## Contributors

- Initial development: Session 2026-02-16

---

## Notes

This is an MVP (Minimum Viable Product) focused on proving the core architecture works with small local LLMs. The system successfully demonstrates:
- Reliable JSON output from 8B models
- Multi-step reasoning capability
- Document processing and summarization
- Fast performance without API costs
- Graceful error handling

Future versions will expand functionality while maintaining the core principle: **reliable operation with small, local LLMs**.
