import json
import re
import time
from pulse_config.config import get_cli_agent_prompt
from pulse_tools.general_tools import execute_shell_command, write_file, read_file
from pulse_ear.speech_handler import speak

def extract_json_decision(response_str):
    """
    Robustly extracts and parses the primary JSON decision object from LLM output.
    Handles markdown code blocks, conversational preambles, and concatenated JSON objects.
    """
    cleaned = response_str.strip()
    
    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1].split("```")[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        pass

    start_idx = cleaned.find("{")
    if start_idx != -1:
        decoder = json.JSONDecoder()
        try:
            obj, _ = decoder.raw_decode(cleaned[start_idx:])
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    raise json.JSONDecodeError("Could not extract a valid JSON decision object", response_str, 0)


def start_cli_agent_loop(task_description, query_func, model_type):
    print(f"CLI Agent Activated. Task: {task_description}")
    speak(f"Starting CLI task: {task_description}")

    cli_prompt = get_cli_agent_prompt()
    history = [
        {"role": "system", "content": cli_prompt},
        {"role": "user", "content": f"START_TASK: {task_description}"}
    ]

    files_written = set()
    commands_executed = []
    last_action_failed = False

    for step in range(10):
        try:
            print(f"Thinking (Step {step+1})...")
            response_str = query_func(history)
            
            history.append({"role": "assistant", "content": response_str})

            ai_decision = extract_json_decision(response_str)
            thought = ai_decision.get("thought", "...")
            action = ai_decision.get("action")
            args = ai_decision.get("arguments", {})

            print(f"CLI Agent Thought: {thought}")

            if action == "finish":
                if last_action_failed:
                    guardrail_msg = (
                        "Error: You cannot finish yet because your last action failed with an error. "
                        "You must inspect the error, fix the issue, and verify that the command succeeds before calling finish."
                    )
                    print(f"Guardrail Triggered: {guardrail_msg}")
                    history.append({"role": "user", "content": guardrail_msg})
                    continue

                if files_written and not commands_executed:
                    files_list = ", ".join(files_written)
                    guardrail_msg = (
                        f"Error: You created file(s) [{files_list}] but have not executed and verified them. "
                        "You MUST run a verification command using execute_shell_command (e.g. running the script) "
                        "and observe the expected output in Tool Output before calling finish."
                    )
                    print(f"Guardrail Triggered: {guardrail_msg}")
                    history.append({"role": "user", "content": guardrail_msg})
                    continue

                print("CLI Task Complete.")
                speak("CLI task complete.")
                return "CLI task finished."

            elif action == "write_file":
                filepath = args.get("filepath", "")
                content = args.get("content", "")
                tool_output = write_file(filepath, content)
                print(f"CLI Agent Observation: {tool_output}")
                
                if tool_output.startswith("Error"):
                    last_action_failed = True
                else:
                    files_written.add(filepath)
                    last_action_failed = False

                history.append({"role": "user", "content": f"Tool Output: {tool_output}"})

            elif action == "read_file":
                filepath = args.get("filepath", "")
                tool_output = read_file(filepath)
                preview = tool_output[:300] + ("..." if len(tool_output) > 300 else "")
                print(f"CLI Agent Observation: (read {len(tool_output)} chars) {preview}")
                
                if tool_output.startswith("Error"):
                    last_action_failed = True
                else:
                    last_action_failed = False

                history.append({"role": "user", "content": f"Tool Output: {tool_output}"})

            elif action == "execute_shell_command":
                command = args.get("command", "")
                if command:
                    print(f"Running command: {command}")
                
                tool_output = execute_shell_command(command)
                print(f"CLI Agent Observation: {tool_output}")
                commands_executed.append(command)

                if "Command failed" in tool_output or "Error:" in tool_output:
                    last_action_failed = True
                else:
                    last_action_failed = False

                history.append({"role": "user", "content": f"Tool Output: {tool_output}"})

            else:
                last_action_failed = True
                unknown_msg = f"Error: Unknown tool '{action}'. Available tools: execute_shell_command, write_file, read_file, finish."
                print(unknown_msg)
                history.append({"role": "user", "content": unknown_msg})

        except json.JSONDecodeError:
            last_action_failed = True
            print(f"Error: LLM did not return valid JSON. Response: {response_str[:200]}")
            history.append({
                "role": "user", 
                "content": (
                    "Error: Your response must be a single valid JSON object in the exact format: "
                    '{"thought": "...", "action": "write_file|execute_shell_command|read_file|finish", "arguments": {...}}'
                )
            })
        except Exception as e:
            print(f"Error in CLI agent loop: {e}")
            speak("I ran into an error. Stopping.")
            return f"Error: {e}"

    speak("Task step limit reached.")
    return "CLI task step limit reached."