import subprocess
import os
from pulse_tools.permission_manager import PermissionManager

_permission_manager = PermissionManager()

def get_permission_manager() -> PermissionManager:
    """Returns the active PermissionManager instance."""
    return _permission_manager

def set_workspace_root(path: str) -> None:
    """Updates the active workspace root for tool execution and permission checks."""
    global _permission_manager
    _permission_manager = PermissionManager(workspace_root=path)

def execute_shell_command(command):
    """
    Executes a given shell command in the terminal within active workspace.
    Requires HITL permission if external paths are detected.
    """
    if not command:
        return "No command provided to execute."

    allowed, msg = _permission_manager.check_command_access(command)
    if not allowed:
        return f"Error: {msg}"

    try:
        print(f"Executing CLI command: {command}")
        result = subprocess.run(
            command,
            shell=True,
            cwd=_permission_manager.workspace_root,
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout.strip()
        if not output:
            return "Command executed successfully with no output."
        return output

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        print(f"Command failed: {error_msg}")
        return f"Command failed with error: {error_msg}"
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return f"An error occurred while executing command: {str(e)}"

def write_file(filepath, content):
    """
    Writes text content to a file with UTF-8 encoding.
    Requires HITL permission if filepath is outside the active workspace.
    """
    if not filepath:
        return "Error: No filepath provided to write."

    target = os.path.join(_permission_manager.workspace_root, filepath) if not os.path.isabs(filepath) else filepath
    allowed, msg = _permission_manager.check_path_access(target, is_write=True)
    if not allowed:
        return f"Error: {msg}"

    try:
        dirname = os.path.dirname(target)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"File '{filepath}' written successfully ({len(content)} characters).")
        return f"File '{filepath}' written successfully ({len(content)} characters)."
    except Exception as e:
        print(f"Error writing file '{filepath}': {e}")
        return f"Error writing file '{filepath}': {str(e)}"

def read_file(filepath):
    """
    Reads text content from a file with UTF-8 encoding.
    Requires HITL permission if filepath is outside the active workspace.
    """
    if not filepath:
        return "Error: No filepath provided to read."

    target = os.path.join(_permission_manager.workspace_root, filepath) if not os.path.isabs(filepath) else filepath
    allowed, msg = _permission_manager.check_path_access(target, is_write=False)
    if not allowed:
        return f"Error: {msg}"

    try:
        if not os.path.exists(target):
            return f"Error: File '{filepath}' does not exist."
        with open(target, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"Error reading file '{filepath}': {e}")
        return f"Error reading file '{filepath}': {str(e)}"