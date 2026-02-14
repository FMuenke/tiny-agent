"""Protocol parser for ACTION and FINAL blocks."""

import json
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ActionBlock:
    """Represents an ACTION block."""
    tool: str
    args: dict


@dataclass
class FinalBlock:
    """Represents a FINAL block."""
    content: str


@dataclass
class ParseResult:
    """Result of parsing LLM output."""
    success: bool
    action: Optional[ActionBlock] = None
    final: Optional[FinalBlock] = None
    error: Optional[str] = None
    raw: str = ""


class ProtocolParser:
    """Parser for LLM output protocol.
    
    The LLM MUST output exactly one of:
    - An ACTION block
    - A FINAL block
    
    ACTION block grammar:
    ACTION
    tool: <tool_name>
    args: <json_object>
    END_ACTION
    
    FINAL block grammar:
    FINAL
    <final answer text in markdown>
    END_FINAL
    """
    
    ACTION_START = "ACTION"
    ACTION_END = "END_ACTION"
    FINAL_START = "FINAL"
    FINAL_END = "END_FINAL"
    
    def parse(self, text: str) -> ParseResult:
        """Parse LLM output into ActionBlock or FinalBlock.
        
        Strict parsing rules:
        - Reject if any text before ACTION/FINAL or after END_ACTION/END_FINAL
        - Reject if multiple blocks exist
        - Reject if JSON parse fails
        """
        text = text.strip()
        
        if not text:
            return ParseResult(
                success=False,
                error="Empty output",
                raw=text
            )
        
        # Count blocks
        action_starts = text.count(self.ACTION_START)
        final_starts = text.count(self.FINAL_START)
        
        if action_starts + final_starts == 0:
            return ParseResult(
                success=False,
                error="No ACTION or FINAL block found. Output must contain exactly one block.",
                raw=text
            )
        
        if action_starts + final_starts > 1:
            return ParseResult(
                success=False,
                error=f"Found {action_starts + final_starts} blocks. Only one block allowed per turn.",
                raw=text
            )
        
        # Parse ACTION block
        if action_starts == 1:
            return self._parse_action(text)
        
        # Parse FINAL block
        return self._parse_final(text)
    
    def _parse_action(self, text: str) -> ParseResult:
        """Parse ACTION block."""
        # Check for extra text before ACTION
        action_idx = text.find(self.ACTION_START)
        if action_idx > 0:
            before = text[:action_idx].strip()
            if before:
                return ParseResult(
                    success=False,
                    error=f"Text before ACTION block: '{before[:50]}...'",
                    raw=text
                )
        
        # Check for END_ACTION
        if self.ACTION_END not in text:
            return ParseResult(
                success=False,
                error="Missing END_ACTION marker",
                raw=text
            )
        
        # Extract content between ACTION and END_ACTION
        start_idx = text.find(self.ACTION_START) + len(self.ACTION_START)
        end_idx = text.find(self.ACTION_END)
        content = text[start_idx:end_idx].strip()
        
        # Check for extra text after END_ACTION
        after_end = text[end_idx + len(self.ACTION_END):].strip()
        if after_end:
            return ParseResult(
                success=False,
                error=f"Text after END_ACTION: '{after_end[:50]}...'",
                raw=text
            )
        
        # Parse tool and args
        return self._extract_action_fields(content, text)
    
    def _extract_action_fields(self, content: str, raw: str) -> ParseResult:
        """Extract tool name and args from ACTION content."""
        lines = content.split('\n')
        tool: Optional[str] = None
        args_str: Optional[str] = None
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith('tool:'):
                tool = line[5:].strip()
            elif line.startswith('args:'):
                # Args may span multiple lines
                args_parts = [line[5:].strip()]
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    if next_line.strip().startswith('tool:'):
                        i -= 1
                        break
                    args_parts.append(next_line)
                    i += 1
                args_str = '\n'.join(args_parts)
            
            i += 1
        
        if tool is None:
            return ParseResult(
                success=False,
                error="Missing 'tool:' field in ACTION block",
                raw=raw
            )
        
        if args_str is None:
            return ParseResult(
                success=False,
                error="Missing 'args:' field in ACTION block",
                raw=raw
            )
        
        # Parse JSON args
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError as e:
            return ParseResult(
                success=False,
                error=f"Invalid JSON in args: {e}",
                raw=raw
            )
        
        if not isinstance(args, dict):
            return ParseResult(
                success=False,
                error="Args must be a JSON object (dictionary)",
                raw=raw
            )
        
        return ParseResult(
            success=True,
            action=ActionBlock(tool=tool, args=args),
            raw=raw
        )
    
    def _parse_final(self, text: str) -> ParseResult:
        """Parse FINAL block."""
        # Check for extra text before FINAL
        final_idx = text.find(self.FINAL_START)
        if final_idx > 0:
            before = text[:final_idx].strip()
            if before:
                return ParseResult(
                    success=False,
                    error=f"Text before FINAL block: '{before[:50]}...'",
                    raw=text
                )
        
        # Check for END_FINAL
        if self.FINAL_END not in text:
            return ParseResult(
                success=False,
                error="Missing END_FINAL marker",
                raw=text
            )
        
        # Extract content between FINAL and END_FINAL
        start_idx = text.find(self.FINAL_START) + len(self.FINAL_START)
        end_idx = text.find(self.FINAL_END)
        content = text[start_idx:end_idx].strip()
        
        # Check for extra text after END_FINAL
        after_end = text[end_idx + len(self.FINAL_END):].strip()
        if after_end:
            return ParseResult(
                success=False,
                error=f"Text after END_FINAL: '{after_end[:50]}...'",
                raw=text
            )
        
        return ParseResult(
            success=True,
            final=FinalBlock(content=content),
            raw=text
        )


def format_action(tool: str, args: dict) -> str:
    """Format an ACTION block."""
    return f"""ACTION
tool: {tool}
args: {json.dumps(args, indent=2)}
END_ACTION"""


def format_final(content: str) -> str:
    """Format a FINAL block."""
    return f"""FINAL
{content}
END_FINAL"""


def get_repair_prompt(error: str, raw_output: str) -> str:
    """Generate a repair prompt for the LLM.
    
    Returns a prompt asking the LLM to correct its output.
    """
    return f"""Your previous output had an error:

Error: {error}

Your output was:
```
{raw_output}
```

Please output EXACTLY ONE block using this format:

For actions:
ACTION
tool: <tool_name>
args: {{"key": "value"}}
END_ACTION

For final answers:
FINAL
<your answer here>
END_FINAL

Rules:
- No text before or after the block
- Only one block per turn
- Args must be valid JSON
- No markdown code fences around the block"""
