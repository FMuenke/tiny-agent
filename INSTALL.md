# ClawLite Installation Guide

Quick guide to get ClawLite up and running.

---

## Prerequisites

### 1. Python 3.10 or higher

```bash
python3 --version
# Should show: Python 3.10.x or higher
```

### 2. Ollama

```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama server
ollama serve

# In another terminal, pull a model
ollama pull llama3.1:8b
```

---

## Installation

### Method 1: Install from source (Recommended)

```bash
# Navigate to project directory
cd /Users/fmuenke/projects/tiny-agent

# Install in editable mode
pip install -e .
```

**Benefits of editable mode:**
- Changes to code take effect immediately
- No need to reinstall after modifications
- Ideal for development

### Method 2: Regular install

```bash
cd /Users/fmuenke/projects/tiny-agent
pip install .
```

---

## Verify Installation

### Check if installed

```bash
pip show clawlite
```

**Expected output:**
```
Name: clawlite
Version: 0.2.0
Summary: Tiny Agent for Local LLMs
Location: ...
Editable project location: /Users/fmuenke/projects/tiny-agent
Requires: httpx, pydantic, pymupdf, rich, typer
```

### Check command availability

```bash
which clawlite
# Should show: /path/to/bin/clawlite

clawlite --help
# Should show usage information
```

---

## Quick Test

```bash
# Go to test invoices folder
cd /Users/fmuenke/projects/tiny-agent/tests/fixtures/invoices

# Run a quick test
clawlite "Summarize all PDF invoices" --model llama3.1:8b
```

**Expected result:** Summary of 5 invoices in ~30 seconds

---

## Troubleshooting

### "command not found: clawlite"

**Solution:**
```bash
# Reinstall
pip uninstall clawlite
pip install -e .

# Verify installation
which clawlite
```

### "Cannot connect to Ollama"

**Solution:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve

# In another terminal, verify
ollama list
```

### "Model not found"

**Solution:**
```bash
# Pull the model
ollama pull llama3.1:8b

# Verify
ollama list
# Should show llama3.1:8b in the list
```

### "ModuleNotFoundError"

**Solution:**
```bash
# Reinstall dependencies
pip install -e .

# Or install manually
pip install typer rich pydantic httpx pymupdf
```

### Changes not taking effect

If you installed without `-e` flag:
```bash
# Reinstall in editable mode
pip uninstall clawlite
pip install -e .
```

---

## Available Models

Check what models you have:
```bash
ollama list
```

**Recommended models:**
- `llama3.1:8b` - Best balance (default)
- `llama3.2:3b` - Fastest
- `deepseek-r1:8b` - Advanced reasoning

**Pull a new model:**
```bash
ollama pull llama3.2:3b
```

---

## Uninstall

```bash
pip uninstall clawlite
```

---

## Update

```bash
# If installed in editable mode, just pull latest code
cd /Users/fmuenke/projects/tiny-agent
git pull  # if using git

# If not editable, reinstall
pip install -e . --force-reinstall
```

---

## Dependencies

ClawLite automatically installs:

- **typer** - CLI framework
- **rich** - Terminal formatting
- **pydantic** - Data validation
- **httpx** - HTTP client for Ollama
- **pymupdf** - PDF text extraction

All dependencies are listed in `pyproject.toml`

---

## Directory Structure After Install

```
/Users/fmuenke/projects/tiny-agent/
├── clawlite/              # Source code
│   ├── __main__.py        # CLI entry point
│   ├── ollama_client.py   # Ollama integration
│   ├── orchestrator.py    # Main logic
│   └── tools/             # Tool implementations
├── tests/                 # Test files
├── pyproject.toml         # Package config
└── README.md              # Documentation
```

---

## Next Steps

After installation:

1. **Run the tests:**
   ```bash
   cd tests/fixtures/invoices
   clawlite "Summarize all PDF invoices" --model llama3.1:8b
   ```

2. **Read the docs:**
   - `README.md` - Usage guide
   - `MVP_STATUS.md` - Current status
   - `TESTING_RESULTS.md` - Test results

3. **Try different tasks:**
   ```bash
   clawlite "Summarize this document" --model llama3.2:3b
   clawlite "Read report.pdf and extract key points"
   ```

---

## Getting Help

```bash
# Show help
clawlite --help

# Show available options
clawlite --help | grep Options -A 10
```

---

**Installation complete! 🎉**

Try: `clawlite "Summarize all PDF invoices" --model llama3.1:8b`
