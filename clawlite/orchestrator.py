"""Orchestrator for clawlite agent loop."""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel

from clawlite.ollama_client import ChatMessage, OllamaClient
from clawlite.protocol import ActionBlock, FinalBlock, ParseResult, ProtocolParser, get_repair_prompt
from clawlite.schemas import RISKY_TOOLS, TOOL_SCHEMAS, validate_tool_args
from clawlite.tools import (
    action_items_tool,
    doc_compare_tool,
    doc_open_tool,
    email_draft_tool,
    meeting_minutes_tool,
    summarize_tool,
    web_search_tool,
    write_file_tool,
)


@dataclass
class StepLog:
    """Log entry for a single step."""
    timestamp: str
    step_num: int
    user_input: str = ""
    model_raw_output: str = ""
    parse_success: bool = False
    parse_error: str = ""
    tool_name: str = ""
    tool_args: dict = field(default_factory=dict)
    tool_result: dict = field(default_factory=dict)
    validation_error: str = ""
    repair_count: int = 0


@dataclass
class SessionState:
    """Session state."""
    documents: dict[str, dict] = field(default_factory=dict)
    artifacts: list[dict] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    step_logs: list[StepLog] = field(default_factory=list)
    
    def add_document(self, doc_data: dict) -> None:
        """Add a document to the session."""
        if doc_data.get("success") and doc_data.get("doc_id"):
            self.documents[doc_data["doc_id"]] = doc_data
    
    def get_state_summary(self) -> str:
        """Get a compact state summary for the LLM."""
        lines = ["## Session State"]
        
        # Documents
        if self.documents:
            lines.append(f"\n### Open Documents ({len(self.documents)})")
            for doc_id, doc in self.documents.items():
                title = doc.get("title", "Unknown")
                excerpt = doc.get("text", "")[:200].replace('\n', ' ')
                lines.append(f"- {doc_id}: {title} | {excerpt}...")
        
        # Artifacts
        if self.artifacts:
            lines.append(f"\n### Created Artifacts ({len(self.artifacts)})")
            for art in self.artifacts[-3:]:  # Last 3
                lines.append(f"- {art.get('path', 'Unknown')}")
        
        return '\n'.join(lines)


class Orchestrator:
    """Orchestrates the agent loop: Propose → Validate → Execute → Observe."""
    
    def __init__(
        self,
        model: str = "llama3.1:8b-instruct",
        workspace: str = "",
        approve: bool = True,
        dry_run: bool = False,
        max_steps: int = 20,
        web_enabled: bool = True,
        log_path: str = "",
        console: Optional[Console] = None,
    ):
        self.model = model
        self.workspace = workspace or os.getcwd()
        self.approve = approve
        self.dry_run = dry_run
        self.max_steps = max_steps
        self.web_enabled = web_enabled
        self.log_path = log_path
        
        self.console = console or Console()
        self.parser = ProtocolParser()
        self.client = OllamaClient(model=model)
        self.state = SessionState()
        
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with instructions and examples."""
        return """You are clawlite, a helpful terminal agent that helps users with document processing, web searches, and office tasks.

CRITICAL RULES:
1. You MUST output EXACTLY ONE block per turn - either ACTION or FINAL
2. No text before or after the block
3. ACTION blocks must contain: tool: <tool_name> and args: {<json>}
4. Use the FINAL block when you have completed the task

AVAILABLE TOOLS:
- doc_open: Open PDF/TXT/MD files. Args: {path, format_hint?, max_chars?}
- doc_compare: Compare two docs. Args: {a: {doc_id}, b: {doc_id}, mode?, max_output_chars?}
- web_search: Search the web. Args: {query, num_results?, recency_days?, extract?, max_chars_per_result?}
- summarize: Summarize a doc. Args: {input: {doc_id}, style?, audience?, max_words?}
- write_file: Write output files. Args: {path, content, mode?, create_dirs?}
- action_items: Extract action items. Args: {input: {doc_id}, format?, max_items?}
- meeting_minutes: Generate meeting minutes. Args: {input: {doc_id}, template?, include_decisions?, include_risks?}
- email_draft: Draft emails. Args: {to_role, tone?, goal, context?, length?}

EXAMPLES:

Example 1 - Open document:
ACTION
tool: doc_open
args: {"path": "./report.pdf", "format_hint": "auto", "max_chars": 50000}
END_ACTION

Example 2 - Summarize:
ACTION
tool: summarize
args: {"input": {"doc_id": "abc123"}, "style": "exec", "audience": "internal", "max_words": 200}
END_ACTION

Example 3 - Web search:
ACTION
tool: web_search
args: {"query": "Python best practices", "num_results": 5}
END_ACTION

Example 4 - Write file:
ACTION
tool: write_file
args: {"path": "./summary.md", "content": "# Summary\n\nHere is the summary...", "mode": "overwrite"}
END_ACTION

Example 5 - Final answer:
FINAL
Here is your summary:

- Point 1
- Point 2

The task is complete.
END_FINAL

WORKFLOW:
1. Plan your approach (don't write this out)
2. Use ACTION blocks to invoke tools
3. Observe results from tools
4. Continue until task is complete
5. Use FINAL block to present the answer

Remember: Only ONE block per turn. No extra text."""
    
    def run(self, task: str) -> str:
        """Run the agent loop for a task.
        
        Returns the final answer.
        """
        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=self.system_prompt),
        ]
        
        # Add initial user message
        user_msg = self._build_user_message(task)
        messages.append(ChatMessage(role="user", content=user_msg))
        
        self.console.print(f"[bold blue]Task:[/bold blue] {task}")
        self.console.print(f"[dim]Model: {self.model} | Max steps: {self.max_steps}[/dim]\n")
        
        final_answer = ""
        
        for step in range(1, self.max_steps + 1):
            self.console.print(f"[bold cyan]Step {step}/{self.max_steps}[/bold cyan]")
            
            # Get LLM response
            try:
                response = self.client.chat(messages)
            except Exception as e:
                self.console.print(f"[red]Error calling LLM: {e}[/red]")
                return f"Error: Failed to get response from model - {e}"
            
            # Parse the output
            parse_result = self._process_response(response.content, step, task, messages)
            
            if parse_result.action:
                # Execute action
                tool_result = self._execute_action(parse_result.action, step)
                
                if tool_result.get("is_final"):
                    final_answer = tool_result.get("result", "")
                    break
                
                # Add observation to messages
                obs = self._build_observation(tool_result)
                messages.append(ChatMessage(role="user", content=obs))
                
            elif parse_result.final:
                final_answer = parse_result.final.content
                self.console.print(Panel(final_answer, title="[bold green]Final Answer[/bold green]", border_style="green"))
                break
            
            self.console.print()
        
        else:
            # Max steps reached
            final_answer = "Reached maximum number of steps. Task incomplete."
            self.console.print(f"[yellow]{final_answer}[/yellow]")
        
        # Save logs
        self._save_logs()
        
        return final_answer
    
    def _process_response(
        self,
        response: str,
        step: int,
        task: str,
        messages: list[ChatMessage],
    ) -> ParseResult:
        """Process LLM response with validation and repair loop."""
        repair_count = 0
        max_repairs = 2
        parse_result = self.parser.parse(response)
        
        while repair_count <= max_repairs:
            # parse_result already initialized before loop
            
            # Log the step
            log = StepLog(
                timestamp=datetime.now().isoformat(),
                step_num=step,
                user_input=task,
                model_raw_output=response,
                parse_success=parse_result.success,
                parse_error=parse_result.error or "",
                repair_count=repair_count,
            )
            self.state.step_logs.append(log)
            
            if parse_result.success:
                if parse_result.action:
                    log.tool_name = parse_result.action.tool
                    log.tool_args = parse_result.action.args
                return parse_result
            
            # Need repair
            repair_count += 1
            if repair_count > max_repairs:
                self.console.print(f"[red]Parse failed after {max_repairs} repairs: {parse_result.error}[/red]")
                # Return as-is, will be handled
                return parse_result
            
            # Request repair
            repair_prompt = get_repair_prompt(parse_result.error or "Unknown error", response)
            messages.append(ChatMessage(role="user", content=repair_prompt))
            
            self.console.print(f"[yellow]Parse error, requesting repair ({repair_count}/{max_repairs})...[/yellow]")
            
            try:
                response = self.client.chat(messages).content
            except Exception as e:
                self.console.print(f"[red]Error in repair: {e}[/red]")
                return parse_result
        
        return parse_result
    
    def _execute_action(self, action: ActionBlock, step: int) -> dict:
        """Execute an action after validation and approval."""
        # Validate schema
        success, error = validate_tool_args(action.tool, action.args)
        
        if not success:
            self.console.print(f"[red]Validation error: {error}[/red]")
            return {
                "success": False,
                "error": f"Schema validation failed: {error}",
            }
        
        # Check if tool is allowed
        if action.tool == "web_search" and not self.web_enabled:
            return {
                "success": False,
                "error": "Web search is disabled. Use --no-web to enable.",
            }
        
        # Check if tool exists
        if action.tool not in TOOL_SCHEMAS:
            return {
                "success": False,
                "error": f"Unknown tool: {action.tool}",
            }
        
        # Show proposed action
        self._show_action(action)
        
        # Check approval
        needs_approval = self.approve or action.tool in RISKY_TOOLS
        
        if needs_approval:
            approved = self._get_approval(action)
            if not approved:
                return {
                    "success": False,
                    "error": "Action cancelled by user.",
                    "user_cancelled": True,
                }
        
        if self.dry_run:
            self.console.print("[yellow][DRY RUN] Skipping execution[/yellow]")
            return {
                "success": True,
                "dry_run": True,
                "tool": action.tool,
                "args": action.args,
            }
        
        # Execute
        self.console.print(f"[dim]Executing {action.tool}...[/dim]")
        
        try:
            result = self._call_tool(action.tool, action.args)
            
            # Update state for doc_open
            if action.tool == "doc_open":
                self.state.add_document(result)
            
            # Update state for write_file
            if action.tool == "write_file" and result.get("success"):
                self.state.artifacts.append({
                    "path": result.get("path"),
                    "step": step,
                })
            
            # Show result
            if result.get("success"):
                self.console.print(f"[green]✓ {action.tool} succeeded[/green]")
            else:
                self.console.print(f"[red]✗ {action.tool} failed: {result.get('error', 'Unknown error')}[/red]")
            
            return result
            
        except Exception as e:
            self.console.print(f"[red]Tool execution error: {e}[/red]")
            return {
                "success": False,
                "error": str(e),
            }
    
    def _call_tool(self, tool_name: str, args: dict) -> dict:
        """Call a tool with given arguments."""
        # Inject workspace and documents context where needed
        if tool_name in ("doc_open", "write_file"):
            args = dict(args)
            args["workspace"] = self.workspace
        
        if tool_name in ("doc_compare", "summarize", "action_items", "meeting_minutes", "email_draft"):
            args = dict(args)
            args["documents"] = self.state.documents
        
        tools = {
            "doc_open": doc_open_tool,
            "doc_compare": doc_compare_tool,
            "web_search": web_search_tool,
            "summarize": summarize_tool,
            "write_file": write_file_tool,
            "action_items": action_items_tool,
            "meeting_minutes": meeting_minutes_tool,
            "email_draft": email_draft_tool,
        }
        
        tool_func = tools.get(tool_name)
        if not tool_func:
            return {"success": False, "error": f"Tool {tool_name} not implemented"}
        
        return tool_func(**args)
    
    def _show_action(self, action: ActionBlock) -> None:
        """Display proposed action in a panel."""
        content = f"[bold]{action.tool}[/bold]\n\n"
        content += json.dumps(action.args, indent=2)
        
        self.console.print(Panel(
            content,
            title="[bold yellow]Proposed Action[/bold yellow]",
            border_style="yellow",
        ))
    
    def _get_approval(self, action: ActionBlock) -> bool:
        """Get user approval for an action."""
        self.console.print("Execute? [y/n/edit]: ", end="")
        response = input().strip().lower()
        
        if response in ("y", "yes", ""):
            return True
        elif response in ("n", "no"):
            return False
        elif response == "edit":
            self.console.print("Editing not implemented. Proceed? [y/n]: ", end="")
            return input().strip().lower() in ("y", "yes", "")
        
        return False
    
    def _build_user_message(self, task: str) -> str:
        """Build the initial user message."""
        parts = [task]
        
        # Add state summary
        state_summary = self.state.get_state_summary()
        if self.state.documents:
            parts.append(f"\n{state_summary}")
        
        parts.append("\nWhat action should I take?")
        
        return '\n'.join(parts)
    
    def _build_observation(self, tool_result: dict) -> str:
        """Build observation message from tool result."""
        if not tool_result.get("success"):
            error = tool_result.get("error", "Unknown error")
            return f"Tool failed: {error}\n\nPlease try a different approach or correct the arguments."
        
        # Format successful result
        lines = ["Tool result:"]
        
        # Include relevant fields
        for key, value in tool_result.items():
            if key in ("success", "error", "note"):
                continue
            
            if key == "text":
                # Truncate text
                text = str(value)[:3000]
                if len(str(value)) > 3000:
                    text += "\n\n[...truncated...]"
                lines.append(f"\n{key}:\n{text}")
            elif isinstance(value, dict):
                lines.append(f"\n{key}:")
                for k, v in value.items():
                    lines.append(f"  {k}: {v}")
            elif isinstance(value, list):
                lines.append(f"\n{key}: {len(value)} items")
                for item in value[:5]:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {value}")
        
        lines.append("\nWhat action should I take next?")
        
        return '\n'.join(lines)
    
    def _save_logs(self) -> None:
        """Save session logs to JSONL file."""
        if not self.log_path:
            return
        
        try:
            with open(self.log_path, "w") as f:
                for log in self.state.step_logs:
                    entry = {
                        "timestamp": log.timestamp,
                        "step": log.step_num,
                        "user_input": log.user_input,
                        "model_output": log.model_raw_output,
                        "parse_success": log.parse_success,
                        "parse_error": log.parse_error,
                        "tool_name": log.tool_name,
                        "tool_args": log.tool_args,
                        "tool_result_success": log.tool_result.get("success") if log.tool_result else None,
                        "repair_count": log.repair_count,
                    }
                    f.write(json.dumps(entry) + "\n")
            
            self.console.print(f"[dim]Log saved to: {self.log_path}[/dim]")
        except Exception as e:
            self.console.print(f"[dim]Failed to save log: {e}[/dim]")
    
    def close(self):
        """Clean up resources."""
        self.client.close()
