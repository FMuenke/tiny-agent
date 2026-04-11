"""Test cases for invoice summarization using fictional markdown files."""

import subprocess
from pathlib import Path

# Test data - completely fictional invoices for TechCorp GmbH
EXPECTED_INVOICES = [
    {
        "file": "invoice_2026_01_contractor_a.md",
        "contractor": "Alice Smith",
        "month": "January 2026",
        "amount": 4000.00,
        "hours": 80,
        "rate": 50.00,
    },
    {
        "file": "invoice_2025_12_contractor_b.md",
        "contractor": "Bob Johnson",
        "month": "December 2025",
        "amount": 4641.00,  # Including 19% VAT
        "hours": 65,
        "rate": 60.00,
    },
    {
        "file": "invoice_2025_11_contractor_a.md",
        "contractor": "Alice Smith",
        "month": "November 2025",
        "amount": 3600.00,
        "hours": 72,
        "rate": 50.00,
    },
    {
        "file": "invoice_2026_01_contractor_c.md",
        "contractor": "Carol Martinez",
        "month": "January 2026",
        "amount": 5890.50,  # Including 19% VAT
        "hours": 90,
        "rate": 55.00,
    },
    {
        "file": "invoice_2025_12_contractor_c.md",
        "contractor": "Carol Martinez",
        "month": "December 2025",
        "amount": 5563.25,  # Including 19% VAT
        "hours": 85,
        "rate": 55.00,
    },
]

TOTAL_EXPECTED = 23694.75  # Sum of all invoices


def test_single_invoice(invoice_file, model="llama3.1:8b"):
    """Test summarization of a single invoice (fictional markdown)."""
    print(f"\n{'='*70}")
    print(f"Testing: {invoice_file}")
    print(f"{'='*70}")

    cmd = [
        "python3", "-m", "clawlite.__main__",
        f"Summarize {invoice_file}",
        "--model", model
    ]

    result = subprocess.run(
        cmd,
        cwd="tests/fixtures/invoices",
        capture_output=True,
        text=True,
        timeout=60
    )

    print(result.stdout)

    if result.returncode != 0:
        print(f"❌ FAILED: {result.stderr}")
        return False

    print(f"✅ SUCCESS")
    return True


def test_all_invoices(model="llama3.1:8b"):
    """Test summarization of all markdown invoices together."""
    print(f"\n{'='*70}")
    print(f"Testing: ALL MARKDOWN INVOICES TOGETHER")
    print(f"{'='*70}")

    cmd = [
        "python3", "-m", "clawlite.__main__",
        "Summarize all markdown invoices",
        "--model", model
    ]

    result = subprocess.run(
        cmd,
        cwd="tests/fixtures/invoices",
        capture_output=True,
        text=True,
        timeout=90
    )

    print(result.stdout)

    if result.returncode != 0:
        print(f"❌ FAILED: {result.stderr}")
        return False

    # Check if output mentions multiple invoices
    output = result.stdout.lower()

    # Count how many contractors are mentioned
    contractors_found = sum(1 for inv in EXPECTED_INVOICES
                           if inv["contractor"].lower().split()[0] in output)

    print(f"\n📊 Found references to {contractors_found}/3 contractors in summary")

    if contractors_found >= 2:
        print(f"✅ SUCCESS (found {contractors_found}/3 contractors)")
        return True
    else:
        print(f"⚠️ PARTIAL SUCCESS (only found {contractors_found}/3 contractors)")
        return False


def test_markdown_format():
    """Test that markdown files work correctly."""
    print(f"\n{'='*70}")
    print(f"Testing: MARKDOWN Format")
    print(f"{'='*70}")

    # Test markdown
    md_cmd = [
        "python3", "-m", "clawlite.__main__",
        "Summarize invoice_2026_01_contractor_a.md",
        "--model", "llama3.1:8b"
    ]

    md_result = subprocess.run(
        md_cmd,
        cwd="tests/fixtures/invoices",
        capture_output=True,
        text=True,
        timeout=60
    )

    print("Markdown Result:")
    print(md_result.stdout)

    if md_result.returncode == 0:
        print("\n✅ Markdown format works!")
        return True
    else:
        print("\n❌ Markdown format failed")
        return False


def run_all_tests(model="llama3.1:8b"):
    """Run all test cases."""
    print(f"\n{'#'*70}")
    print(f"# ClawLite Invoice Summarization Test Suite")
    print(f"# Model: {model}")
    print(f"# Using fictional test data (TechCorp GmbH)")
    print(f"{'#'*70}")

    results = {
        "individual": [],
        "combined": None,
        "markdown_test": None
    }

    # Test markdown format works
    print(f"\n\n## PART 1: Markdown Format Test")
    print(f"{'='*70}")
    results["markdown_test"] = test_markdown_format()

    # Test each invoice individually
    print(f"\n\n## PART 2: Individual Invoice Tests (Markdown)")
    print(f"{'='*70}")

    for invoice_data in EXPECTED_INVOICES:
        success = test_single_invoice(invoice_data["file"], model)
        results["individual"].append({
            "file": invoice_data["file"],
            "success": success
        })

    # Test all invoices together
    print(f"\n\n## PART 3: Combined Invoice Test (Markdown)")
    print(f"{'='*70}")

    results["combined"] = test_all_invoices(model)

    # Summary
    print(f"\n\n{'#'*70}")
    print(f"# Test Summary")
    print(f"{'#'*70}")

    markdown_test = "✅ PASSED" if results["markdown_test"] else "❌ FAILED"
    individual_success = sum(1 for r in results["individual"] if r["success"])
    combined_test = "✅ PASSED" if results["combined"] else "❌ FAILED"

    print(f"\nMarkdown Format Test: {markdown_test}")
    print(f"Individual Tests: {individual_success}/5 passed")
    print(f"Combined Test: {combined_test}")

    print(f"\n\nExpected Total: €{TOTAL_EXPECTED:.2f}")
    print(f"Invoices: {len(EXPECTED_INVOICES)}")
    print(f"Contractors: 3 (Alice Smith, Bob Johnson, Carol Martinez)")
    print(f"Client: TechCorp GmbH")
    print(f"Period: November 2025 - January 2026")
    print(f"\n✅ All test data is completely fictional")

    return results


if __name__ == "__main__":
    import sys

    model = sys.argv[1] if len(sys.argv) > 1 else "llama3.1:8b"

    print(f"Starting tests with model: {model}")
    print(f"Using fictional test data")
    print(f"Make sure you're in the project root directory!")

    results = run_all_tests(model)

    # Exit code based on results
    all_passed = (
        results["markdown_test"] and
        all(r["success"] for r in results["individual"]) and
        results["combined"]
    )

    sys.exit(0 if all_passed else 1)
