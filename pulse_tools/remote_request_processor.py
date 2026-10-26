from types import SimpleNamespace
from dotenv import load_dotenv
from fastapi.exceptions import HTTPException
import os
import time
load_dotenv()

from pulse_ear.speech_handler import set_tts_enabled
from pulse_config.config import ROUTER_SYSTEM_PROMPT
from pulse_brain.llm_interface import Agent, tool_dispatcher, generate_response
from pulse_tools.general_tools import set_workspace_root
from pulse_brain.memory_base.schemas import RemoteRequest
from pulse_utils.server_response import server_response

STATIC_TEXT = SimpleNamespace(
    INVALID_SECRET_KEY="Invalid secret key",
    FAILED_AGENT_INIT="Failed to initialize agent",
)

RESULT = None

def process_remote_request(data : RemoteRequest) -> str:
    global RESULT
    if data.secret_key != os.environ.get("SECRET_KEY"):
        return HTTPException(status_code=401, detail=STATIC_TEXT.INVALID_SECRET_KEY)
    set_tts_enabled(False)
    if not os.path.isdir(data.directory):
        return server_response(status_code=400, message=f"Invalid directory: {data.directory}")
    set_workspace_root(data.directory)
    try:
        agent = Agent(name="Pulse", context_window=10)
    except Exception as e:
        return server_response(status_code=500, message=f"{STATIC_TEXT.FAILED_AGENT_INIT}: {str(e)}")
    conversation_context = agent.get_context()
    tool_check_history = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
        *conversation_context,
        {"role": "user", "content": data.query}]       
            
    initial_response, _ = generate_response(
                                data.query, 
                                tool_check_history, 
                                agent.client,
                                is_tool_check=True)
    
    tool_name, tool_result = tool_dispatcher(
                                    initial_response, 
                                    agent.client, 
                                )
    RESULT = tool_result if tool_result else None

    if tool_name:
        time.sleep(1)
        agent.remember("user", data.query)
        agent.remember("assistant", f"Executed tool: {tool_name}")
        return server_response(status_code=200, message=f"Executed tool: {tool_name}", data={"tool_result": tool_result})
    else:
        print(f"PulseAI ({agent.model_type}): {initial_response}")
        agent.remember("user", data.query)
        agent.remember("assistant", initial_response)
        return server_response(status_code=200, message=f"PulseAI ({agent.model_type}): {initial_response}")

def get_result():
    global RESULT
    if RESULT is not None:
        RESULT = dict(sorted(RESULT.items()))
        return server_response(status_code=200, message="Result retrieved successfully", data={"result": RESULT})
    else:
        return server_response(status_code=404, message="No result available")