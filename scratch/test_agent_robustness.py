import os
import sys
import json
import subprocess

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pulse_brain.brain import extract_json_decision, start_cli_agent_loop
from pulse_tools.general_tools import write_file, read_file
from pulse_brain.llm_interface import load_openai_model, query_llm
from pulse_ear.speech_handler import set_tts_enabled

def test_json_extractor_resilience():
    print("[1] Testing extract_json_decision resilience...")
    
    # Case A: Standard JSON
    res_a = '{"thought": "test", "action": "finish", "arguments": {}}'
    parsed_a = extract_json_decision(res_a)
    assert parsed_a["action"] == "finish", f"Case A failed: {parsed_a}"
    
    # Case B: Markdown code fences
    res_b = '```json\n{"thought": "in markdown", "action": "write_file", "arguments": {"filepath": "test.py"}}\n```'
    parsed_b = extract_json_decision(res_b)
    assert parsed_b["action"] == "write_file", f"Case B failed: {parsed_b}"
    
    # Case C: Conversational preamble before JSON
    res_c = 'We need to check file content. {\n  "thought": "check",\n  "action": "read_file",\n  "arguments": {"filepath": "fib.py"}\n}'
    parsed_c = extract_json_decision(res_c)
    assert parsed_c["action"] == "read_file", f"Case C failed: {parsed_c}"
    
    # Case D: Concatenated JSON objects (multiple steps emitted at once)
    res_d = '{"thought": "Step 1", "action": "write_file", "arguments": {"filepath": "f.py"}}{"thought": "Step 2", "action": "finish", "arguments": {}}'
    parsed_d = extract_json_decision(res_d)
    assert parsed_d["action"] == "write_file", f"Case D failed: {parsed_d}"
    
    print("    PASSED: All JSON extraction edge cases parsed cleanly.")

def test_file_tools():
    print("[2] Testing write_file and read_file tools...")
    test_path = "scratch/_tmp_test_file.txt"
    sample_content = "def test_func():\n    return 'Hello from Pulse! 🚀'\n"
    
    write_res = write_file(test_path, sample_content)
    assert "written successfully" in write_res, f"write_file failed: {write_res}"
    assert os.path.exists(test_path), "File was not created on disk"
    
    read_res = read_file(test_path)
    assert read_res == sample_content, f"Content mismatch: {read_res}"
    
    # Clean up
    if os.path.exists(test_path):
        os.remove(test_path)
    print("    PASSED: write_file and read_file work with UTF-8 support.")

def test_live_agent_loop_with_verification():
    print("[3] Testing live CLI Agent loop on Fibonacci task with mandatory verification...")
    set_tts_enabled(False)  # Disable audio playback for tests
    client, model_type = load_openai_model()
    query_func = lambda hist: query_llm(client, hist, model_type)
    
    target_script = "scratch/fibonacci_agent_test.py"
    if os.path.exists(target_script):
        os.remove(target_script)
        
    task_desc = f"create a python script named {target_script} that prints the first 10 numbers of the fibonacci sequence and verify that it executes properly"
    
    result = start_cli_agent_loop(task_desc, query_func, model_type)
    print(f"    Loop finished with result: '{result}'")
    
    assert result == "CLI task finished.", f"Expected successful finish, got: {result}"
    assert os.path.exists(target_script), f"Expected script {target_script} was not created"
    
    # Verify the generated file is actually valid python and prints the expected sequence
    py_run = subprocess.run([sys.executable, target_script], capture_output=True, text=True)
    assert py_run.returncode == 0, f"Generated script crashed: {py_run.stderr}"
    output = py_run.stdout.strip()
    print(f"    Script Output:\n{output}")
    assert "55" in output or "34" in output, f"Output did not contain expected Fibonacci numbers: {output}"
    
    # Clean up test script
    if os.path.exists(target_script):
        os.remove(target_script)
    print("    PASSED: Live CLI agent successfully created, verified, and concluded task.")

if __name__ == "__main__":
    print("--- Starting CLI Agent Robustness Test Suite ---")
    test_json_extractor_resilience()
    test_file_tools()
    test_live_agent_loop_with_verification()
    print("\nALL AGENT ROBUSTNESS TESTS COMPLETED SUCCESSFULLY!")
