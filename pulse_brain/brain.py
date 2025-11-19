import json
import time
from pulse_config.config import CLI_AGENT_SYSTEM_PROMPT
from pulse_tools.general_tools import execute_shell_command
from pulse_ear.speech_handler import speak

def clean_json_response(response_str):
    """Helper to strip Markdown code blocks if present."""
    if "```json" in response_str:
        response_str = response_str.split("```json")[1].split("```")[0].strip()
    elif "```" in response_str:
        response_str = response_str.split("```")[0].strip()
    return response_str

def start_cli_agent_loop(task_description, query_func,model_type):
    print(f"CLI Agent Activated. Task: {task_description}")
    speak(f"Starting CLI task: {task_description}")

    history = [
        {"role": "system", "content": CLI_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": f"START_TASK: {task_description}"}
    ]

    # RATE LIMIT CONFIG
    RATE_LIMIT_DELAY = 32 
    last_request_time = 0 

    for step in range(10):
        try:
            # --- 1. RATE LIMIT CHECK ---
            if model_type == "gemini":
                time_since_last = time.time() - last_request_time
                
                if time_since_last < RATE_LIMIT_DELAY and last_request_time != 0:
                    wait_time = RATE_LIMIT_DELAY - time_since_last
                    print(f"Rate limit safety: Waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)

            # --- 2. THINK ---
            print(f"Thinking (Step {step+1})...")
            response_str = query_func(history)
            response_str = clean_json_response(response_str)
            last_request_time = time.time()
            
            history.append({"role": "assistant", "content": response_str})

            ai_decision = json.loads(response_str)
            thought = ai_decision.get("thought", "...")
            action = ai_decision.get("action")
            args = ai_decision.get("arguments", {})

            print(f"CLI Agent Thought: {thought}")

            # --- 3. ACT ---
            if action == "finish":
                print("CLI Task Complete.")
                speak("CLI task complete.")
                return "CLI task finished."

            if action == "execute_shell_command":
                command = args.get("command")
                speak(f"Running command: {command}") 
                
                tool_output = execute_shell_command(command)
                print(f"CLI Agent Observation: {tool_output}")
                
                # --- 4. OBSERVE ---
                history.append({"role": "user", "content": f"Tool Output: {tool_output}"})
            
            else:
                history.append({"role": "user", "content": f"Error: Unknown tool '{action}'."})

        except json.JSONDecodeError:
            print(f"Error: LLM did not return valid JSON. Response: {response_str}")
            history.append({"role": "user", "content": "Error: You must respond in valid JSON."})
        except Exception as e:
            print(f"Error in CLI agent loop: {e}")
            speak("I ran into an error. Stopping.")
            return f"Error: {e}"

    speak("Task step limit reached.")
    return "CLI task step limit reached."