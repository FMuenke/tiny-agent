# ClawLite Quick Start Guide

Get up and running with ClawLite in 5 minutes.

---

## Prerequisites Check

```bash
# 1. Check Python (need 3.10+)
python3 --version

# 2. Check Ollama
which ollama

# 3. Check if model is available
ollama list | grep llama3.1
```

If anything is missing, see [INSTALL.md](INSTALL.md)

---

## Installation

```bash
cd /Users/fmuenke/projects/tiny-agent
pip install -e .
```

**Verify:**
```bash
clawlite --help
```

---

## Your First Command

### Example 1: Summarize Invoices

```bash
cd tests/fixtures/invoices
clawlite "Summarize all markdown invoices"
```

**Expected output** (~35 seconds):
```markdown
Invoice Summary

Total: ~€23,700
Period: Nov 2025 - Jan 2026
Contractors: 3 (Alice, Bob, Carol)

Breakdown:
• Jan 2026: €4,000 + €5,890.50
• Dec 2025: €4,641 + €5,563.25
• Nov 2025: €3,600

Sources:
• [5 invoices from TechCorp GmbH]
```

### Example 2: Single Document

```bash
clawlite "Summarize invoice_2026_01_contractor_a.md"
```

**Expected output** (~20 seconds):
```markdown
Invoice Summary

Total: €4,000.00
Period: January 2026
Contractor: Alice Smith
Services: Software Development (80h @ €50/h)
```

### Example 3: Fast Mode

```bash
clawlite "Quick summary of invoices" --model llama3.2:3b
```

**Expected output** (~15 seconds):
Similar summary but faster processing

---

## Common Use Cases

### Summarize Documents in Current Folder

```bash
cd /path/to/your/documents
clawlite "Summarize all PDF files"
```

### Summarize Specific File

```bash
clawlite "Summarize report.pdf"
```

### Use Different Model

```bash
# Fastest
clawlite "task" --model llama3.2:3b

# Best quality
clawlite "task" --model llama3.1:8b

# Advanced reasoning
clawlite "task" --model deepseek-r1:8b
```

### Work in Different Directory

```bash
clawlite "Summarize PDFs" --workspace ~/Documents/reports
```

---

## Options Reference

```bash
clawlite TASK [OPTIONS]

Required:
  TASK              What you want to do (in quotes)

Options:
  --model, -m       Model name [default: llama3.1:8b]
  --workspace, -w   Working directory [default: current]
  --max-steps, -s   Max steps [default: 20]
  --base-url        Ollama URL [default: http://localhost:11434]
  --help            Show help
```

---

## Troubleshooting

### Error: "Cannot connect to Ollama"

```bash
# Start Ollama in another terminal
ollama serve
```

### Error: "Model not found"

```bash
# Pull the model
ollama pull llama3.1:8b
```

### Slow Performance

```bash
# Use faster model
clawlite "task" --model llama3.2:3b
```

### Command Not Found

```bash
# Reinstall
pip install -e .
```

---

## What Can It Do?

### ✅ Currently Working
- Open and read PDF, TXT, MD files
- Summarize single documents
- Summarize entire folders
- Extract key information
- List sources

### 🚧 Coming Soon
- Extract action items from notes
- Generate meeting minutes
- Draft emails
- Parse calendar events
- Create expense reports
- Write files

---

## Performance Expectations

| Model | Files | Time | Quality |
|-------|-------|------|---------|
| llama3.2:3b | 1 | ~12s | Good |
| llama3.2:3b | 5 | ~20s | Good |
| llama3.1:8b | 1 | ~20s | Better |
| llama3.1:8b | 5 | ~35s | Better |

**Recommendation:** Use llama3.1:8b for best results

---

## Next Steps

1. **Try it with your documents:**
   ```bash
   cd /path/to/your/files
   clawlite "Summarize all documents"
   ```

2. **Experiment with different models:**
   ```bash
   ollama list  # See available models
   ollama pull llama3.2:3b  # Try faster model
   ```

3. **Read the docs:**
   - [README.md](README.md) - Full usage guide
   - [MVP_STATUS.md](MVP_STATUS.md) - Features and limitations
   - [TESTING_RESULTS.md](TESTING_RESULTS.md) - Test data

---

## Example Session

```bash
# Navigate to test folder
cd /Users/fmuenke/projects/tiny-agent/tests/fixtures/invoices

# Run summary
clawlite "Summarize all PDF invoices" --model llama3.1:8b

# Output appears in 30-40 seconds
# Shows: Total amount, breakdown by month, sources

# Try single file
clawlite "Summarize 01 Januar Rechnung.pdf" --model llama3.1:8b

# Output appears in 20 seconds
# Shows: Detailed info for one invoice
```

---

## Getting Help

```bash
# Show all options
clawlite --help

# Check installation
pip show clawlite

# Check Ollama status
curl http://localhost:11434/api/tags
```

---

## Tips

💡 **Use specific models**: Different models have different speeds and accuracies
💡 **Keep tasks simple**: One clear task per command works best
💡 **Check file locations**: Make sure PDFs are in current directory or use --workspace
💡 **Be patient**: First run may take longer as model loads

---

**Ready to go! Try: `clawlite "Summarize all PDF invoices" --model llama3.1:8b`** 🚀
