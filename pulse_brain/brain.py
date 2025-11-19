import json
from pulse_config.config import CLI_AGENT_SYSTEM_PROMPT
from pulse_tools.general_tools import execute_shell_command
from pulse_ear.speech_handler import speak


def start_cli_agent_loop(task_description, llm_pipeline, terminators):
    """
    This is the "Observe-Think-Act" loop for the CLI.
    It uses the LOCAL LLM (llm_pipeline) to reason and execute commands.
    """
    print(f"CLI Agent Activated. Task: {task_description}")
    speak(f"Starting CLI task: {task_description}")

    history = [
        {"role": "system", "content": CLI_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": f"START_TASK: {task_description}"}
    ]

    for _ in range(7):
        try:
            # 1. THINK
            outputs = llm_pipeline(
                history,
                max_new_tokens=256,
                eos_token_id=terminators,
                do_sample=True,
                temperature=0.6,
                top_p=0.9,
            )
            
            response_str = outputs[0]["generated_text"][-1]["content"]
            history.append({"role": "assistant", "content": response_str})

            ai_decision = json.loads(response_str)
            thought = ai_decision.get("thought", "...")
            action = ai_decision.get("action")
            args = ai_decision.get("arguments", {})

            print(f"CLI Agent Thought: {thought}")

            # 2. ACT
            if action == "finish":
                print("CLI Task Complete.")
                speak("CLI task complete.")
                return "CLI task finished."

            if action == "execute_shell_command":
                command = args.get("command")
                tool_output = execute_shell_command(command)
                print(f"CLI Agent Observation: {tool_output}")
                
                # 3. OBSERVE
                history.append({"role": "user", "content": f"Tool Output: {tool_output}"})
            
            else:
                # LLM hallucinated
                history.append({"role": "user", "content": f"Error: Unknown tool '{action}'."})

        except json.JSONDecodeError:
            print(f"Error: Local LLM did not return valid JSON. Response: {response_str}")
            history.append({"role": "user", "content": "Error: You must respond in valid JSON."})
        except Exception as e:
            print(f"Error in CLI agent loop: {e}")
            speak("I ran into an error with the CLI task. Stopping.")
            return f"Error in CLI agent loop: {e}"

    speak("Task step limit reached. Stopping.")
    return "CLI task step limit reached."
