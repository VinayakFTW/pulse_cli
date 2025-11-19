from dotenv import load_dotenv
load_dotenv()
import time
import sys
from pulse_ear.speech_handler import command, speak
from pulse_config.config import *
from pulse_brain.llm_interface import tool_dispatcher, load_model, load_gemini_model, generate_response

def get_user_input(mode="voice"):
    if mode == "text":
        try:
            return input("\nVinayak (Text): ").strip().lower()
        except EOFError:
            return "0"
    else:
        return command()

if __name__ == '__main__':
    
    llm_pipeline = None
    terminators = None
    model_type = "local"
    
    print("Initializing PulseAI...")
    try:
        print(f"Attempting to load local model: {LOCAL_MODEL_ID}...")
        llm_pipeline, terminators = load_model(LOCAL_MODEL_ID)
        print("Local model loaded successfully.")
        model_type = "local"
    except Exception as e:
        print(f"\n[WARNING] System incapable of running local model ({e}).")
        print("Switching to Gemini API...")
        try:
            llm_pipeline, model_type = load_gemini_model(GEMINI_API_KEY)
            print("Gemini API loaded successfully.")
        except Exception as gemini_e:
            print(f"CRITICAL: Failed to load Gemini API as well: {gemini_e}")
            sys.exit(1)

    print("\nSelect Input Mode:")
    print("1. Voice Mode (Default)")
    print("2. Text Mode")
    mode_choice = input("Choice (1/2): ").strip()
    
    input_mode = "text" if mode_choice == "2" else "voice"
    print(f"Starting in {input_mode.upper()} mode.")

    
    conversation_history = load_history()
    
    listening = True

    while True:
        if listening:
    
            query = get_user_input(input_mode)
            
    
            if not query or query == "0":
                if input_mode == "text":
                    print("Exiting...")
                    break
                listening = False
                continue

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
                if input_mode == "voice":
                    speak(tool_result)
                else:
                    print(f"Result: {tool_result}")
                    
                time.sleep(1)
                
                conversation_history.append({"role": "user", "content": query})
                conversation_history.append({"role": "assistant", "content": f"Executed tool: {tool_name}"})
                save_history(conversation_history)
                listening = False
            
            else:
                print(f"PulseAI ({model_type}): {initial_response}")
                if input_mode == "voice":
                    speak("I'm not sure how to handle that.")
                listening = False
                conversation_history.append({"role": "user", "content": query})
                conversation_history.append({"role": "assistant", "content": initial_response})
                save_history(conversation_history)
                
        else:
    
            if input_mode == "text":
                listening = True
            else:
                if 'cli' in str(tool_name):
                    listening = True
                else:
                    listening = True