"""Tests for protocol parser."""

import pytest

from clawlite.protocol import ActionBlock, FinalBlock, ProtocolParser, get_repair_prompt


class TestProtocolParser:
    """Test cases for the protocol parser."""
    
    def setup_method(self):
        """Set up parser for each test."""
        self.parser = ProtocolParser()
    
    def test_parse_valid_action(self):
        """Test parsing a valid ACTION block."""
        text = """ACTION
tool: doc_open
args: {"path": "./test.pdf", "max_chars": 5000}
END_ACTION"""
        
        result = self.parser.parse(text)
        
        assert result.success is True
        assert result.action is not None
        assert result.action.tool == "doc_open"
        assert result.action.args == {"path": "./test.pdf", "max_chars": 5000}
        assert result.final is None
        assert result.error is None
    
    def test_parse_valid_final(self):
        """Test parsing a valid FINAL block."""
        text = """FINAL
Here is your summary:

- Point 1
- Point 2
END_FINAL"""
        
        result = self.parser.parse(text)
        
        assert result.success is True
        assert result.final is not None
        assert "Here is your summary" in result.final.content
        assert "Point 1" in result.final.content
        assert result.action is None
        assert result.error is None
    
    def test_parse_empty(self):
        """Test parsing empty text."""
        result = self.parser.parse("")
        
        assert result.success is False
        assert "Empty" in result.error
    
    def test_parse_no_block(self):
        """Test parsing text with no ACTION or FINAL."""
        text = "This is just regular text"
        result = self.parser.parse(text)
        
        assert result.success is False
        assert "No ACTION or FINAL" in result.error
    
    def test_parse_multiple_blocks(self):
        """Test parsing text with multiple blocks."""
        text = """ACTION
tool: doc_open
args: {"path": "test.pdf"}
END_ACTION

FINAL
Some answer
END_FINAL"""
        
        result = self.parser.parse(text)
        
        assert result.success is False
        assert "Only one block" in result.error
    
    def test_parse_text_before_action(self):
        """Test parsing with text before ACTION."""
        text = """Here is the action:
ACTION
tool: doc_open
args: {"path": "test.pdf"}
END_ACTION"""
        
        result = self.parser.parse(text)
        
        assert result.success is False
        assert "before ACTION" in result.error
    
    def test_parse_text_after_action(self):
        """Test parsing with text after END_ACTION."""
        text = """ACTION
tool: doc_open
args: {"path": "test.pdf"}
END_ACTION

Thanks!"""
        
        result = self.parser.parse(text)
        
        assert result.success is False
        assert "after END_ACTION" in result.error
    
    def test_parse_invalid_json(self):
        """Test parsing with invalid JSON in args."""
        text = """ACTION
tool: doc_open
args: {invalid json here}
END_ACTION"""
        
        result = self.parser.parse(text)
        
        assert result.success is False
        assert "Invalid JSON" in result.error
    
    def test_parse_missing_tool(self):
        """Test parsing ACTION without tool field."""
        text = """ACTION
args: {"path": "test.pdf"}
END_ACTION"""
        
        result = self.parser.parse(text)
        
        assert result.success is False
        assert "Missing 'tool:'" in result.error
    
    def test_parse_missing_args(self):
        """Test parsing ACTION without args field."""
        text = """ACTION
tool: doc_open
END_ACTION"""
        
        result = self.parser.parse(text)
        
        assert result.success is False
        assert "Missing 'args:'" in result.error
    
    def test_parse_args_not_object(self):
        """Test parsing with args that are not a dict."""
        text = """ACTION
tool: doc_open
args: ["list", "not", "object"]
END_ACTION"""
        
        result = self.parser.parse(text)
        
        assert result.success is False
        assert "JSON object" in result.error
    
    def test_parse_multiline_args(self):
        """Test parsing ACTION with multiline JSON args."""
        text = """ACTION
tool: doc_open
args: {
  "path": "./test.pdf",
  "max_chars": 5000,
  "format_hint": "auto"
}
END_ACTION"""
        
        result = self.parser.parse(text)
        
        assert result.success is True
        assert result.action.args["path"] == "./test.pdf"
        assert result.action.args["max_chars"] == 5000
    
    def test_parse_missing_end_action(self):
        """Test parsing ACTION without END_ACTION."""
        text = """ACTION
tool: doc_open
args: {"path": "test.pdf"}"""
        
        result = self.parser.parse(text)
        
        assert result.success is False
        assert "Missing END_ACTION" in result.error
    
    def test_parse_missing_end_final(self):
        """Test parsing FINAL without END_FINAL."""
        text = """FINAL
Some answer"""
        
        result = self.parser.parse(text)
        
        assert result.success is False
        assert "Missing END_FINAL" in result.error


class TestRepairPrompt:
    """Test cases for repair prompt generation."""
    
    def test_repair_prompt_contains_error(self):
        """Test that repair prompt includes the error."""
        prompt = get_repair_prompt("Invalid JSON", "bad output")
        
        assert "Invalid JSON" in prompt
        assert "bad output" in prompt
    
    def test_repair_prompt_includes_format(self):
        """Test that repair prompt includes format examples."""
        prompt = get_repair_prompt("error", "output")
        
        assert "ACTION" in prompt
        assert "FINAL" in prompt
        assert "END_ACTION" in prompt
        assert "END_FINAL" in prompt
