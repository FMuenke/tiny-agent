#!/bin/bash
# Test individual invoice summaries using fictional markdown files
# Run from project root: bash tests/test_individual_summaries.sh

cd tests/fixtures/invoices

echo "=================================================="
echo "Testing Individual Invoice Summaries"
echo "Using fictional test data (TechCorp GmbH)"
echo "=================================================="
echo ""

# Test 1: January 2026 - Alice Smith
echo "Test 1: January 2026 Invoice (Alice Smith)"
echo "--------------------------------------------------"
clawlite "Summarize invoice_2026_01_contractor_a.md"
echo ""
echo ""

# Test 2: December 2025 - Bob Johnson
echo "Test 2: December 2025 Invoice (Bob Johnson)"
echo "--------------------------------------------------"
clawlite "Summarize invoice_2025_12_contractor_b.md"
echo ""
echo ""

# Test 3: November 2025 - Alice Smith
echo "Test 3: November 2025 Invoice (Alice Smith)"
echo "--------------------------------------------------"
clawlite "Summarize invoice_2025_11_contractor_a.md"
echo ""
echo ""

# Test 4: January 2026 - Carol Martinez
echo "Test 4: January 2026 Invoice (Carol Martinez)"
echo "--------------------------------------------------"
clawlite "Summarize invoice_2026_01_contractor_c.md"
echo ""
echo ""

# Test 5: December 2025 - Carol Martinez
echo "Test 5: December 2025 Invoice (Carol Martinez)"
echo "--------------------------------------------------"
clawlite "Summarize invoice_2025_12_contractor_c.md"
echo ""
echo ""

echo "=================================================="
echo "All tests complete!"
echo "All test data is completely fictional"
echo "=================================================="
