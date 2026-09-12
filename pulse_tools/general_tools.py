import subprocess
import os

def execute_shell_command(command):
    """
    Executes a given shell command in the terminal and returns its output or error.
    """
    if not command:
        return "No command provided to execute."
        
    try:
        print(f"Executing CLI command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        
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
    Creates parent directories automatically if needed.
    """
    if not filepath:
        return "Error: No filepath provided to write."
    try:
        dirname = os.path.dirname(filepath)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"File '{filepath}' written successfully ({len(content)} characters).")
        return f"File '{filepath}' written successfully ({len(content)} characters)."
    except Exception as e:
        print(f"Error writing file '{filepath}': {e}")
        return f"Error writing file '{filepath}': {str(e)}"

def read_file(filepath):
    """
    Reads text content from a file with UTF-8 encoding.
    """
    if not filepath:
        return "Error: No filepath provided to read."
    try:
        if not os.path.exists(filepath):
            return f"Error: File '{filepath}' does not exist."
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"Error reading file '{filepath}': {e}")
        return f"Error reading file '{filepath}': {str(e)}"