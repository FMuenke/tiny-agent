# ClawLite - Tiny Agent for Local LLMs

A terminal-based AI agent optimized for small local models (7B-8B) via Ollama.

**Status**: ✅ MVP Working! (see [MVP_STATUS.md](MVP_STATUS.md))

---

## Quick Start

### 1. Prerequisites

```bash
# Install Ollama (if not already installed)
brew install ollama

# Start Ollama
ollama serve

# Pull a model
ollama pull llama3.1:8b
```

### 2. Install ClawLite

```bash
cd tiny-agent
pip install -e .
```

### 3. Run It!

```bash
# Go to a folder with documents
cd tests/fixtures/invoices

# Summarize all PDFs
clawlite "Summarize all PDF invoices" --model llama3.1:8b
```

---

## Usage

### Basic Commands

```bash
# Summarize documents
clawlite "Summarize all PDF files"

# Use specific model
clawlite "Summarize reports" --model deepseek-r1:8b

# Use faster model
clawlite "Quick summary" --model llama3.2:3b
```

### Options

```
--model, -m      Model to use (default: llama3.1:8b)
--workspace, -w  Working directory
--max-steps, -s  Maximum steps (default: 20)
--base-url       Ollama API URL (default: http://localhost:11434)
```

---

## What It Does

ClawLite is designed to handle everyday office tasks with small local LLMs:

✅ **Currently Working:**
- Open and read PDFs, text files, markdown
- Summarize single documents or entire folders
- Extract key information and sources

🚧 **Coming Soon:**
- Extract action items from meeting notes
- Generate meeting minutes
- Draft emails
- Parse calendar events
- Extract structured data (emails, phones, etc.)
- Create expense reports

---

## Architecture

```
User Input → Orchestrator → LLM (Ollama JSON mode)
                ↓
         Parse JSON Response
                ↓
         Execute Tool (doc_open, etc.)
                ↓
         Format Result
                ↓
         Feed back to LLM → Repeat
```

**Key Features:**
- **JSON Mode**: Uses Ollama's native JSON format for reliable outputs
- **Auto-repair**: Fixes common JSON errors from small models
- **Progress UI**: Live status updates with rich formatting
- **Multi-step**: Handles complex tasks requiring multiple steps
- **Lightweight**: Optimized for 8B models on consumer hardware

---

## Examples

### Invoice Summary

```bash
cd tests/fixtures/invoices
clawlite "Summarize all PDF invoices" --model llama3.1:8b
```

**Output:**
```markdown
Invoice Summary

Total: €AAAAAA
Period: Nov 2025 - Jan 2026

Breakdown:
• Jan 2026: €JJJJJJ (RE-2026-001)
• Dec 2025: €DDDDDD (RE-2025-017)
• Nov 2025: €NNNNNN (RE-2025-016)

Sources:
• invoice1.pdf (RE-2026-001)
• invoice2.pdf (RE-2025-017)
• invoice3.pdf (RE-2025-016)
```

### Markdown Summary

```bash
clawlite "Summarize all markdown documentation" --model llama3.2:3b
```

---

## Available Models

Tested and working:
- `llama3.2:3b` - Fastest, good for quick summaries
- `llama3.1:8b` - Best balance of speed and quality
- `deepseek-r1:8b` - Advanced reasoning (slower)

Check available models:
```bash
ollama list
```

---

## Performance

On Apple M1/M2 Mac:
- **llama3.2:3b**: ~15 seconds for 5 invoices
- **llama3.1:8b**: ~25 seconds for 5 invoices
- **Document loading**: < 1 second

**Optimized for:**
- ✅ Fast response times
- ✅ No system blocking
- ✅ Low memory usage
- ✅ Works offline (100% local)

---

## Project Structure

```
tiny-agent/
├── clawlite/              # Main package
│   ├── __main__.py        # CLI entry point
│   ├── ollama_client.py   # Ollama API client
│   ├── protocol.py        # JSON parser with repair
│   ├── orchestrator.py    # Main control loop
│   └── tools/             # Tool implementations
│       └── doc_open.py    # Document loader
├── tests/                 # Test files and fixtures
├── SPEC_v2.md            # Full specification
├── MINIMAL_MVP_GUIDE.md  # Implementation guide
├── MVP_STATUS.md         # Current status
└── README.md             # This file
```

---

## Development

### Run Tests

```bash
# Test document loading
python3 -c "
from clawlite.tools.doc_open import doc_open
result = doc_open('tests/fixtures/invoices')
print(f'Loaded {result[\"files_processed\"]} files')
"

# Test full pipeline
python3 -m clawlite.__main__ "Summarize test documents" --model llama3.2:3b
```

### Add New Tools

See [SPEC_v2.md](SPEC_v2.md) for tool specifications and [MINIMAL_MVP_GUIDE.md](MINIMAL_MVP_GUIDE.md) for implementation patterns.

---

## Troubleshooting

### "Cannot connect to Ollama"
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

### "Model not found"
```bash
# Pull the model
ollama pull llama3.1:8b
```

### Slow performance
```bash
# Use smaller model
clawlite "task" --model llama3.2:3b

# Or reduce max steps
clawlite "task" --max-steps 5
```

---

## Contributing

This is an MVP. Contributions welcome for:
- Additional tools (action_items, meeting_minutes, etc.)
- Better prompt engineering
- Performance optimizations
- Tests and documentation

---

## License

MIT

---

## Links

- [Ollama](https://ollama.ai) - Local LLM runtime
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF text extraction
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting

---

**Built with ❤️ for local LLMs**
