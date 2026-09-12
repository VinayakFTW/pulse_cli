import os
import sys
import io

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pulse_config.config import get_router_prompt, reload_prompts
from pulse_brain.llm_interface import parse_tool_call, tool_dispatcher, load_openai_model, query_llm

def test_parse_tool_call_and_dispatcher():
    print("[1] Testing parse_tool_call and tool_dispatcher unit behavior...")
    
    # 1. Valid tool call
    valid_call = "[TOOL: cli_agent, task: create a fibonacci script]"
    name, params = parse_tool_call(valid_call)
    assert name == "cli_agent", f"Expected 'cli_agent', got {name}"
    assert params.get("task") == "create a fibonacci script", f"Params mismatch: {params}"
    
    # 2. Conversational response (should return None, None and NOT log 'Unknown tool format')
    chat_text = "Sure! Here is the python script for fibonacci:\n```python\nprint('fib')\n```"
    name, params = parse_tool_call(chat_text)
    assert name is None and params is None, "Expected None for chat response"
    
    # Capture stdout during tool_dispatcher on chat_text
    old_stdout = sys.stdout
    sys.stdout = captured = io.StringIO()
    try:
        d_name, d_res = tool_dispatcher(chat_text, None, model_type="mock")
    finally:
        sys.stdout = old_stdout
    
    output = captured.getvalue()
    assert "Unknown tool format" not in output, f"Unexpected error logging found in output: {output}"
    assert d_name is None and d_res is None, "Dispatcher should return None, None for chat"
    print("    PASSED: Tool parser and dispatcher handled chat & tool formats cleanly.")

def test_live_router_classification():
    print("[2] Testing live LLM router classification...")
    reload_prompts()
    router_prompt = get_router_prompt()
    client, model_type = load_openai_model()
    
    test_cases = [
        ("create a fibbonacci secquence printing code", True, "Code creation should route to cli_agent"),
        ("write a python script to ping google.com", True, "Script creation should route to cli_agent"),
        ("what is the fibonacci sequence?", False, "Conceptual explanation should route to chat"),
        ("hello, how are you today?", False, "Greeting should route to chat"),
    ]
    
    for query, expect_tool, reason in test_cases:
        print(f"    Testing: '{query}'...")
        history = [
            {"role": "system", "content": router_prompt},
            {"role": "user", "content": query}
        ]
        response = query_llm(client, history, model_type=model_type)
        tool_name, params = parse_tool_call(response)
        
        if expect_tool:
            assert tool_name == "cli_agent", f"FAILED: '{query}' was not routed to cli_agent! Got response: {response}"
            assert "task" in params, f"FAILED: 'task' parameter missing from params: {params}"
            print(f"      -> SUCCESS: Routed to cli_agent with task: '{params['task']}'")
        else:
            assert tool_name is None, f"FAILED: '{query}' should be chat, but got tool: {tool_name}"
            print(f"      -> SUCCESS: Routed to Chat (Response length: {len(response)} chars)")

if __name__ == "__main__":
    print("--- Starting Router & Dispatcher Test Suite ---")
    test_parse_tool_call_and_dispatcher()
    test_live_router_classification()
    print("\nALL ROUTER TESTS COMPLETED SUCCESSFULLY!")
