from dotenv import load_dotenv
load_dotenv()
import time
from pulse_ear.speech_handler import command,speak
from pulse_config.config import *
from pulse_brain.llm_interface import tool_dispatcher,load_model,generate_response
from pulse_tools.general_tools import greet

if __name__ == '__main__':
    
    llm_pipeline, terminators = load_model(LOCAL_MODEL_ID)
    greet("Vinayak")
    
    conversation_history = load_history()
    print("Conversation history loaded.")
    
    listening = True

    while True:
        if listening:
            query = command().lower().strip()
            
            if not query or query == "0":
                listening = False
                continue

            tool_check_history = [{"role": "system", "content": CLI_AGENT_SYSTEM_PROMPT}, {"role": "user", "content": query}]
            initial_response, _ = generate_response(query, tool_check_history, llm_pipeline, terminators, is_tool_check=True)

            tool_name, tool_result = tool_dispatcher(initial_response, llm_pipeline, terminators)

            if tool_name:
                print(f"Executed tool: {tool_name}")
                speak(tool_result)
                time.sleep(1)
                
                conversation_history.append({"role": "user", "content": query})
                conversation_history.append({"role": "assistant", "content": f"Executed tool: {tool_name}"})
                save_history(conversation_history)
                listening = False
            
            else:
                print(f"PulseAI (Fallback): {initial_response}")
                speak("I'm not sure how to handle that.")
                listening = False
                
        else:
            if 'cli' in tool_name:
                    listening = True
            