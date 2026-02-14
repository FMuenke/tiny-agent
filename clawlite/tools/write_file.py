"""File writing tool for clawlite."""

import os
from pathlib import Path
from typing import Any

from clawlite.schemas import WriteFileMode


def write_file_tool(
    path: str,
    content: str,
    mode: str = "overwrite",
    create_dirs: bool = True,
    workspace: str = "",
) -> dict[str, Any]:
    """Write content to a file.
    
    Args:
        path: Path to write
        content: Content to write
        mode: Write mode (overwrite|append)
        create_dirs: Create directories if needed
        workspace: Restricted workspace path
        
    Returns:
        Write result
    """
    # Resolve path
    file_path = Path(path).expanduser().resolve()
    
    # Check workspace constraint
    if workspace:
        workspace_path = Path(workspace).expanduser().resolve()
        try:
            file_path.relative_to(workspace_path)
        except ValueError:
            return {
                "success": False,
                "error": f"Path {path} is outside workspace {workspace}",
            }
    
    # Create parent directories if needed
    if create_dirs:
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create directories: {e}",
            }
    
    # Write file
    try:
        mode_enum = WriteFileMode(mode)
        
        if mode_enum == WriteFileMode.APPEND:
            # Append mode
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(content)
            action = "appended"
        else:
            # Overwrite mode (default)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            action = "written"
        
        return {
            "success": True,
            "path": str(file_path),
            "action": action,
            "chars_written": len(content),
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to write file: {e}",
        }
