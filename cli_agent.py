import os
import sys
import time

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)

from dotenv import load_dotenv
load_dotenv()

from pulse_ear.speech_handler import speak, set_tts_enabled, get_user_input
from pulse_config.config import ROUTER_SYSTEM_PROMPT
from pulse_brain.llm_interface import Agent, tool_dispatcher, generate_response
from pulse_tools.general_tools import set_workspace_root
from pulse_ui.voice_server import broadcast_state
from pulse_ui.window_manager import launch_voice_ui, close_voice_ui


def main():
    workspace = os.path.realpath(os.path.abspath(os.getcwd()))
    set_workspace_root(workspace)

    print("=" * 65)
    print("                PULSE AI CLI ACTIVATED")
    print(f"  Active Workspace: {workspace}")
    print("  [Security] Workspace: FULL ACCESS | External Paths: PROTECTED")
    print("=" * 65)

    try:
        agent = Agent(name="Pulse", context_window=10)
    except Exception as e:
        raise RuntimeError(f"CRITICAL: Failed to initialize agent: {e}")

    # Display restored context notification if existing session records were loaded
    history_count = len(agent.memory.get_history(limit=0))
    if history_count > 0:
        print(f"[Memory] Restored previous session context ({history_count} messages loaded from {agent.memory.db_path}).")

    print("\nSelect Input Mode:")
    print("1. Voice Mode (Default)")
    print("2. Text Mode")
    mode_choice = input("Choice (1/2): ").strip()
    
    input_mode = "text" if mode_choice == "2" else "voice"
    print(f"Starting in {input_mode.upper()} mode.")

    if input_mode == "text":
        tts_choice = input("Enable spoken responses with Soprano TTS? (Y/n): ").strip().lower()
        enable_tts = tts_choice not in ["n", "no"]
        set_tts_enabled(enable_tts)
        print(f"Spoken responses: {'ENABLED' if enable_tts else 'DISABLED'}")
    else:
        set_tts_enabled(True)
        try:
            launch_voice_ui()
        except Exception as e:
            print(f"[Voice UI] Warning: Could not launch Voice UI window ({e}). Continuing in CLI mode.")

    last_sigint_time = 0.0

    while True:
        try:
            broadcast_state("listening" if input_mode == "voice" else "idle")
            query = get_user_input(input_mode)
            last_sigint_time = 0.0

            if not query:
                continue

            if query == "0" and input_mode == "text":
                print("Exiting...")
                close_voice_ui()
                break

            broadcast_state("thinking")

            conversation_context = agent.get_context()
            tool_check_history = [
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                *conversation_context,
                {"role": "user", "content": query}
            ]       

            initial_response, _ = generate_response(
                query, 
                tool_check_history, 
                agent.client, 
                model_type=agent.model_type, 
                is_tool_check=True
            )

            tool_name, tool_result = tool_dispatcher(
                initial_response, 
                agent.client, 
                model_type=agent.model_type
            )

            if tool_name:
                print(f"Executed tool: {tool_name}")
                broadcast_state("speaking")
                speak(f"Executed tool: {tool_name}")
                print(f"Result: {tool_result}")

                time.sleep(1)
                agent.remember("user", query)
                agent.remember("assistant", f"Executed tool: {tool_name}")
            else:
                print(f"PulseAI ({agent.model_type}): {initial_response}")
                broadcast_state("speaking")
                speak(initial_response)
                agent.remember("user", query)
                agent.remember("assistant", initial_response)

            broadcast_state("listening" if input_mode == "voice" else "idle")

        except KeyboardInterrupt:
            current_time = time.time()
            if current_time - last_sigint_time <= 3.0:
                print("\n\n[System] Exiting and saving session memory...")
                close_voice_ui()
                count = agent.persist_session()
                print(f"[System] Session safely saved ({count} messages persisted to {agent.memory.db_path}). Goodbye!\n")
                break
            else:
                last_sigint_time = current_time
                print("\n[System] Press Ctrl+C again to save session and exit.")
                continue


if __name__ == '__main__':
    main()
