# Test Invoice Fixtures

This directory contains **completely fictional test data** for ClawLite invoice summarization.

---

## Test Data

### 5 Fictional Invoices for TechCorp GmbH

All test data is **100% fictional** - no real companies, persons, or data.

| File | Contractor | Month | Amount | Hours | Rate |
|------|-----------|-------|--------|-------|------|
| invoice_2026_01_contractor_a.md | Alice Smith | Jan 2026 | €4,000.00 | 80h | €50/h |
| invoice_2025_12_contractor_b.md | Bob Johnson | Dec 2025 | €4,641.00 | 65h | €60/h |
| invoice_2025_11_contractor_a.md | Alice Smith | Nov 2025 | €3,600.00 | 72h | €50/h |
| invoice_2026_01_contractor_c.md | Carol Martinez | Jan 2026 | €5,890.50 | 90h | €55/h |
| invoice_2025_12_contractor_c.md | Carol Martinez | Dec 2025 | €5,563.25 | 85h | €55/h |

**Total:** €23,694.75

---

## Fictional Entities

### Client
- **TechCorp GmbH** - Fictional technology company
- Contact: Max Mustermann (common German placeholder name)
- Address: Industrieweg 50, 10115 Berlin

### Contractors
- **Alice Smith** - Technical Services, Software Development
- **Bob Johnson** - Consulting Services, Technical Consulting
- **Carol Martinez** - IT Solutions, Database Administration

### Services
- Software Development (Frontend/Backend)
- Technical Consulting (Cloud Architecture)
- Database Administration (Optimization/Migration)

---

## Why Fictional Data?

✅ **Safe for public repositories**
✅ **No privacy concerns**
✅ **Can be freely shared**
✅ **Easy to understand and modify**

---

## Usage

### Test Single Invoice
```bash
cd tests/fixtures/invoices
clawlite "Summarize invoice_2026_01_contractor_a.md"
```

### Test All Invoices
```bash
clawlite "Summarize all markdown invoices"
```

### Run Test Suite
```bash
# From project root
python3 tests/test_summaries.py

# Or shell script
bash tests/test_individual_summaries.sh
```

---

## Expected Results

### Single Invoice Summary
- Time: ~20 seconds
- Accuracy: 100% (fictional data is clean)
- Format: Markdown with breakdown and sources

### Multiple Invoices Summary
- Time: ~35 seconds
- Coverage: 4-5 of 5 invoices mentioned
- Total: ~€23,700 (LLM may approximate)

---

## File Format

Each markdown file contains:
- Invoice number and date
- Contractor information (fictional)
- Client information (fictional)
- Services table with hours and rates
- Payment details (fictional IBANs)
- Notes about the services

---

## Adding New Test Cases

To add a new fictional invoice:

1. **Create markdown file:**
   ```markdown
   # Invoice: [Month Year] - [Contractor Name]

   ## Invoice Details
   **Invoice Number:** INV-YYYY-NNN
   **From:** [Fictional Contractor]
   **To:** TechCorp GmbH

   ## Services
   | Description | Hours | Rate | Amount |
   ```

2. **Update test suite:**
   - Add to `EXPECTED_INVOICES` in `test_summaries.py`
   - Update `TOTAL_EXPECTED`
   - Add test case to shell script

3. **Use fictional data only:**
   - Generic names (John Doe, Jane Smith, etc.)
   - Fictional addresses
   - Made-up IBANs (DE89 1234 5678...)
   - Placeholder tax IDs

---

## Notes

- All data is completely fictional
- No connection to real entities
- Safe for public repositories
- Easy to modify and extend

---

**Test Data Version:** 1.0
**Created:** 2026-02-16
**Type:** Completely fictional test data
