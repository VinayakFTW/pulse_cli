from transformers import AutoModelForCausalLM, AutoTokenizer,AutoModelForSeq2SeqLM,pipeline
import torch
from pulse_brain.brain import start_cli_agent_loop
import re


def load_model(model_name,cache_directory=None):
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
    # tokenizer = AutoTokenizer.from_pretrained(model_name,cache_dir=cache_directory)
    # model = AutoModelForCausalLM.from_pretrained(model_name,cache_dir=cache_directory,trust_remote_code=True)
    return llm_pipeline, terminators

def generate_response(_query, history, pipe, terminators, is_tool_check=False):
    """
    Generates a response using the Hugging Face text-generation pipeline.
    """
    try:
        if not is_tool_check:
            history.append({"role": "user", "content": _query})
        
        outputs = pipe(
            history,
            max_new_tokens=256,
            eos_token_id=terminators,
            do_sample=True,
            temperature=0.6,
            top_p=0.9,
        )
        
        response = outputs[0]["generated_text"][-1]["content"]
        
        if not is_tool_check:
            history.append({"role": "assistant", "content": response})

        return response, history
    
    except Exception as e:
        print(f"Error generating response: {e}")
        return "I seem to be having some trouble with my thoughts right now.", history

def parse_tool_call(response):
    """
    More robustly parses the [TOOL: ...] string, even with complex params.
    """
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

def tool_dispatcher(response,llm_pipeline, terminators):
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
        result_message = start_cli_agent_loop(task_description, llm_pipeline, terminators)
        return tool_name, result_message
        
    return None, "Unknown tool."
