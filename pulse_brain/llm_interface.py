from openai import OpenAI
import re

from pulse_brain.brain import start_cli_agent_loop
from pulse_config.config import ENVIRONMENT
from pulse_brain.memory_base.memory import Memory

def load_openai_model(api_key=ENVIRONMENT["OPENAI_API_KEY"], base_url=ENVIRONMENT["OPENAI_API_BASE"]):
    """Configures and returns the OpenAI client."""
    if not api_key or base_url is None:
        raise ValueError("OpenAI API key or Base URL not found in Environment variables. Please set OPENAI_API_KEY and OPENAI_API_BASE.")

    client = OpenAI(api_key=api_key, base_url=base_url)
    return client, "openai"


class Agent:
    def __init__(self, name: str = "Pulse", session_id: str = "default", context_window: int = 10):
        self.name = name
        self.context_window = context_window
        self.memory = Memory(session_id=session_id)
        self.client, self.model_type = load_openai_model()

    def remember(self, role: str, content: str) -> None:
        """Stores a message into the agent's in-memory store."""
        self.memory.add_message(role, content)

    def get_context(self, limit: int | None = None) -> list[dict[str, str]]:
        """Retrieves recent conversation turns for context."""
        return self.memory.get_history(limit=limit or self.context_window)

    def persist_session(self) -> int:
        """Flushes in-memory session to persistent SQLite storage."""
        return self.memory.persist_to_db()

    def restore_session(self) -> int:
        """Restores session records from persistent SQLite storage."""
        return self.memory.load_from_db()




def query_llm(model_obj, history, model_type="openai"):
    """
    Unified function to query either Local LLM or OpenAI.
    Returns the string response.
    """
    if model_type == "openai":
        try:
            system_instruction = None
            chat_history = []

            for msg in history:
                if msg["role"] == "system":
                    system_instruction = msg["content"]
                else:
                    chat_history.append(msg)

            response = model_obj.responses.create(
                model="auto",
                instructions=system_instruction,
                input=chat_history,
            )

            return response.output_text

        except Exception as e:
            print(f"OpenAI Error: {e}")
            return "I encountered an error reaching the OpenAI API."

def generate_response(_query, history, model_obj, model_type="openai", is_tool_check=False):
    """
    Generates a response using the Unified query function.
    """
    try:
        if not is_tool_check:
            history.append({"role": "user", "content": _query})
        
        response = query_llm(model_obj, history, model_type)
        
        if not is_tool_check:
            history.append({"role": "assistant", "content": response})

        return response, history
    
    except Exception as e:
        print(f"Error generating response: {e}")
        return "I seem to be having some trouble with my thoughts right now.", history

def parse_tool_call(response):
    try:
        stripped = response.strip()
        if not (stripped.startswith("[TOOL:") and stripped.endswith("]")):
            return None, None

        print(f"Tool command received: {stripped}")
        command_str = stripped[6:-1].strip()

        match = re.match(r"^\s*([a-zA-Z0-9_]+)\s*,?(.*)", command_str, re.S)
        if not match:
            print(f"Malformed tool syntax: {stripped}")
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

def tool_dispatcher(response, model_obj, model_type="openai"):
    """
    Parses the LLM's tool command and calls the appropriate function.
    Returns (tool_name, tool_result). If response is chat, returns (None, None).
    """
    tool_name, params = parse_tool_call(response)

    if not tool_name:
        return None, None
    elif tool_name == "cli_agent":
        task_description = params.get('task')
        if not task_description:
            task_description = "Execute requested CLI task"
        
        query_func = lambda hist: query_llm(model_obj, hist, model_type)
        
        result_message = start_cli_agent_loop(task_description, query_func, model_type)
        return tool_name, result_message
        
    print(f"Warning: Unhandled tool '{tool_name}'")
    return None, f"Unknown tool '{tool_name}'."