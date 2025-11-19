import subprocess

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
        print(f"Command failed: {e.stderr.strip()}")
        return f"Command failed with error: {e.stderr.strip()}"
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return f"An error occurred while executing command: {str(e)}"