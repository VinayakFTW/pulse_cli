from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import torch
import google.generativeai as genai
from pulse_brain.brain import start_cli_agent_loop
from pulse_config.config import GEMINI_API_KEY
import re

def load_gemini_model(api_key):
    """Configures and returns the Gemini model."""
    if not api_key:
        raise ValueError("Gemini API Key not found in environment variables.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-pro')
    return model, "gemini"

def load_model(model_name, cache_directory=None):
    """Loads Local LLM, returns pipeline and terminators."""
    llm_pipeline = pipeline(
        "text-generation",
        model=model_name,
        model_kwargs={"dtype": torch.bfloat16},
        device_map="auto",
    )
    terminators = [
        llm_pipeline.tokenizer.eos_token_id,
        llm_pipeline.tokenizer.convert_tokens_to_ids("<|eot_id|>")
    ]
    return llm_pipeline, terminators

def query_llm(model_obj, history, model_type="local", terminators=None):
    """
    Unified function to query either Local LLM or Gemini.
    Returns the string response.
    """
    # gemini locgi
    if model_type == "gemini":
        try:
            system_instruction = None
            chat_history = []
            
            for msg in history:
                if msg['role'] == 'system':
                    system_instruction = msg['content']
                elif msg['role'] == 'user':
                    chat_history.append({'role': 'user', 'parts': [msg['content']]})
                elif msg['role'] == 'assistant':
                    chat_history.append({'role': 'model', 'parts': [msg['content']]})
            
            if system_instruction:
                active_model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=system_instruction)
            else:
                active_model = model_obj

            chat = active_model.start_chat(history=chat_history[:-1])
            last_msg = chat_history[-1]['parts'][0]
            response = chat.send_message(last_msg)
            return response.text
            
        except Exception as e:
            print(f"Gemini Error: {e}")
            return "I encountered an error reaching the Gemini API."

    else:
        # local LLM Logic
        outputs = model_obj(
            history,
            max_new_tokens=256,
            eos_token_id=terminators,
            do_sample=True,
            temperature=0.6,
            top_p=0.9,
        )
        return outputs[0]["generated_text"][-1]["content"]

def generate_response(_query, history, model_obj, terminators=None, model_type="local", is_tool_check=False):
    """
    Generates a response using the Unified query function.
    """
    try:
        if not is_tool_check:
            history.append({"role": "user", "content": _query})
        
        response = query_llm(model_obj, history, model_type, terminators)
        
        if not is_tool_check:
            history.append({"role": "assistant", "content": response})

        return response, history
    
    except Exception as e:
        print(f"Error generating response: {e}")
        return "I seem to be having some trouble with my thoughts right now.", history

def parse_tool_call(response):
    try:
        if not response.strip().startswith("[TOOL:") or not response.strip().endswith("]"):
            return None, None

        print(f"Tool command received: {response}")
        command_str = response.strip()[6:-1]

        match = re.match(r"^\s*([a-zA-Z0-9_]+)\s*,?(.*)", command_str, re.S)
        if not match:
            return None, None
            
        tool_name = match.group(1).strip()
        params_str = match.group(2).strip()
        params = {}
    
        if tool_name in ["cli_agent"]:
            if ':' in params_str:
                key, value = params_str.split(':', 1)
                params[key.strip()] = value.strip()
            return tool_name, params

        return tool_name, params
    except Exception as e:
        print(f"Error parsing tool command: {e}. Full response: {response}")
        return None, None

def tool_dispatcher(response, model_obj, terminators=None, model_type="local"):
    """
    Parses the LLM's tool command and calls the appropriate function.
    """
    tool_name, params = parse_tool_call(response)

    if not tool_name:
        if response != "[CHAT]":
            print(f"Unknown tool format: {response}")
        return None, None
    elif tool_name == "cli_agent":
        task_description = params.get('task')
        
        query_func = lambda hist: query_llm(model_obj, hist, model_type, terminators)
        
        result_message = start_cli_agent_loop(task_description, query_func)
        return tool_name, result_message
        
    return None, "Unknown tool."