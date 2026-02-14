"""Tests for schemas validation."""

import pytest

from clawlite.schemas import (
    DocCompareArgs,
    DocOpenArgs,
    SummarizeArgs,
    WebSearchArgs,
    WriteFileArgs,
    validate_tool_args,
)


class TestDocOpenSchema:
    """Test doc_open schema."""
    
    def test_valid_doc_open(self):
        """Test valid doc_open args."""
        args = DocOpenArgs(path="./test.pdf", format_hint="pdf", max_chars=50000)
        
        assert args.path == "./test.pdf"
        assert args.format_hint == "pdf"
        assert args.max_chars == 50000
    
    def test_doc_open_defaults(self):
        """Test doc_open with defaults."""
        args = DocOpenArgs(path="./test.txt")
        
        assert args.format_hint == "auto"
        assert args.max_chars == 50000
    
    def test_doc_open_max_chars_bounds(self):
        """Test max_chars bounds."""
        # Too low
        with pytest.raises(Exception):
            DocOpenArgs(path="./test.pdf", max_chars=500)
        
        # Too high
        with pytest.raises(Exception):
            DocOpenArgs(path="./test.pdf", max_chars=300000)


class TestWebSearchSchema:
    """Test web_search schema."""
    
    def test_valid_web_search(self):
        """Test valid web_search args."""
        args = WebSearchArgs(
            query="Python best practices",
            num_results=5,
            recency_days=30,
            extract="snippets",
            max_chars_per_result=3000,
        )
        
        assert args.query == "Python best practices"
        assert args.num_results == 5
    
    def test_web_search_query_required(self):
        """Test that query is required."""
        with pytest.raises(Exception):
            WebSearchArgs()
    
    def test_web_search_bounds(self):
        """Test bounds validation."""
        # num_results too high
        with pytest.raises(Exception):
            WebSearchArgs(query="test", num_results=20)
        
        # recency_days too high
        with pytest.raises(Exception):
            WebSearchArgs(query="test", recency_days=500)


class TestSummarizeSchema:
    """Test summarize schema."""
    
    def test_valid_summarize(self):
        """Test valid summarize args."""
        args = SummarizeArgs(
            input={"doc_id": "abc123"},
            style="exec",
            audience="internal",
            max_words=250,
        )
        
        assert args.input.doc_id == "abc123"
        assert args.style.value == "exec"
    
    def test_summarize_enum_values(self):
        """Test enum values."""
        from clawlite.schemas import SummarizeStyle, SummarizeAudience
        
        args = SummarizeArgs(
            input={"doc_id": "test"},
            style=SummarizeStyle.BULLETS,
            audience=SummarizeAudience.CLIENT,
        )
        
        assert args.style.value == "bullets"
        assert args.audience.value == "client"


class TestDocCompareSchema:
    """Test doc_compare schema."""
    
    def test_valid_doc_compare(self):
        """Test valid doc_compare args."""
        args = DocCompareArgs(
            a={"doc_id": "doc1"},
            b={"doc_id": "doc2"},
            mode="summary",
            max_output_chars=12000,
        )
        
        assert args.a.doc_id == "doc1"
        assert args.b.doc_id == "doc2"


class TestWriteFileSchema:
    """Test write_file schema."""
    
    def test_valid_write_file(self):
        """Test valid write_file args."""
        args = WriteFileArgs(
            path="./output.md",
            content="# Summary\n\nThis is the summary.",
            mode="overwrite",
            create_dirs=True,
        )
        
        assert args.path == "./output.md"
        assert args.content.startswith("# Summary")


class TestValidateToolArgs:
    """Test tool argument validation."""
    
    def test_valid_doc_open(self):
        """Test valid doc_open validation."""
        success, error = validate_tool_args("doc_open", {
            "path": "./test.pdf",
            "max_chars": 50000,
        })
        
        assert success is True
        assert error == ""
    
    def test_invalid_tool(self):
        """Test unknown tool."""
        success, error = validate_tool_args("unknown_tool", {})
        
        assert success is False
        assert "Unknown tool" in error
    
    def test_missing_required_field(self):
        """Test missing required field."""
        success, error = validate_tool_args("doc_open", {
            "max_chars": 50000,
            # missing path
        })
        
        assert success is False
        assert "path" in error.lower() or "required" in error.lower()
    
    def test_bounds_violation(self):
        """Test field out of bounds."""
        success, error = validate_tool_args("doc_open", {
            "path": "./test.pdf",
            "max_chars": 999999,  # Too high
        })
        
        assert success is False
