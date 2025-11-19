import platform
import json
import os

os_name = platform.platform()

LOCAL_MODEL_ID = "meta-llama/Llama-3.2-3B-Instruct"
HISTORY_FILE = "conversation_history.json"

def save_history(history):
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=4)
    except Exception as e:
        print(f"Error saving history: {e}")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
                
                if not history or history[0]['role'] != 'system':
                    return [{"role": "system", "content": CLI_AGENT_SYSTEM_PROMPT}]
                
                history[0]['content'] = CLI_AGENT_SYSTEM_PROMPT
                return history
        except (json.JSONDecodeError, IndexError):
            return [{"role": "system", "content": CLI_AGENT_SYSTEM_PROMPT}]
    else:
        return [{"role": "system", "content": CLI_AGENT_SYSTEM_PROMPT}]

CLI_AGENT_SYSTEM_PROMPT = """
You are a specialist CLI (Command Line Interface) agent. You will be given a high-level task and a history of previous commands.
Your goal is to achieve the task by executing a chain of shell commands.

You have access to these three tools:
1. [execute_shell_command, command: shell command string] - Executes a terminal command and returns its output.
2. [finish] - Call this *only* when the high-level task is fully complete.

RULES:
- You are installed on the platform {os_name}
- You must reason step-by-step.
- You must examine the "Tool Output" from the previous step to decide your next command.
- If a command fails, you must try to correct it or stop.
- You MUST respond in this exact JSON format:
{{
  "thought": "My reasoning for the next step. I will check the output of the last command and decide what to do next to achieve the task.",
  "action": "function_name",
  "arguments": {{"command": "command_to_run"}}
}}
- Or, if the task is done:
{{
  "thought": "I have successfully completed the task.",
  "action": "finish",
  "arguments": {{}}
}}

SAFETY RULES:
- Never execute destructive commands (rm -rf, dd, format) without explicit user confirmation
- Avoid commands requiring elevated privileges unless specifically requested
- Stop if you encounter sensitive operations (modifying system files, network operations)
""".format(os_name=os_name)