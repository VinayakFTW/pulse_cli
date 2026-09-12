from dotenv import load_dotenv
load_dotenv()
import time
import sys

from pulse_ear.speech_handler import command, speak, set_tts_enabled
from pulse_config.config import *
from pulse_brain.llm_interface import tool_dispatcher, load_openai_model, generate_response

def get_user_input(mode="voice"):
    if mode == "text":
        try:
            return input("\nVinayak (Text): ").strip()
        except EOFError:
            return "0"
    else:
        return command()

if __name__ == '__main__':
    
    llm_pipeline = None
    terminators = None
    model_type = "local"
    
    print("Initializing PulseAI...")
    model_type = "local"
    try:
        llm_pipeline, model_type = load_openai_model()
        print("OpenAI API loaded successfully.")
    except Exception as gemini_e:
        print(f"CRITICAL: Failed to load OpenAI API as well: {gemini_e}")
        sys.exit(1)

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
    
    conversation_history = load_history()

    while True:
    
        query = get_user_input(input_mode)
        if (not query or query == "0") and input_mode == "text":
            print("Exiting...")
            break

        tool_check_history = [{"role": "system", "content": ROUTER_SYSTEM_PROMPT}, {"role": "user", "content": query}]       
    
        initial_response, _ = generate_response(
                query, 
                tool_check_history, 
                llm_pipeline, 
                terminators, 
                model_type=model_type, 
                is_tool_check=True
            )

    
        tool_name, tool_result = tool_dispatcher(
                initial_response, 
                llm_pipeline, 
                terminators, 
                model_type=model_type
            )

        if tool_name:
            print(f"Executed tool: {tool_name}")
            speak(f"Executed tool: {tool_name}")
            print(f"Result: {tool_result}")

            time.sleep(1)
                
            conversation_history.append({"role": "user", "content": query})
            conversation_history.append({"role": "assistant", "content": f"Executed tool: {tool_name}"})
            save_history(conversation_history)
            
        else:
            print(f"PulseAI ({model_type}): {initial_response}")
            speak(initial_response)
            conversation_history.append({"role": "user", "content": query})
            conversation_history.append({"role": "assistant", "content": initial_response})
            save_history(conversation_history)
