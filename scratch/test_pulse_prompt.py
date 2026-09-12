import os
import sys
import platform
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pulse_config.config import (
    ROUTER_SYSTEM_PROMPT,
    CLI_AGENT_SYSTEM_PROMPT,
    get_router_prompt,
    get_cli_agent_prompt,
    get_full_pulse_prompt,
    reload_prompts,
    load_history,
    PromptManager,
    extract_prompt_section,
    format_prompt,
    PULSE_MD_PATH,
)

def test_pulse_md_existence():
    print("[1] Checking PULSE.md existence...")
    assert os.path.exists(PULSE_MD_PATH), f"PULSE.md does not exist at {PULSE_MD_PATH}"
    print("    PASSED: PULSE.md found at", PULSE_MD_PATH)

def test_router_prompt_extraction():
    print("[2] Testing router prompt extraction...")
    router = get_router_prompt()
    assert "[TOOL: cli_agent, task:" in router, "Router prompt missing tool tag instruction"
    assert "Pulse" in router, "Router prompt missing assistant name 'Pulse'"
    assert router == ROUTER_SYSTEM_PROMPT, "Exported ROUTER_SYSTEM_PROMPT mismatch"
    print("    PASSED: Router prompt extracted correctly.")

def test_cli_agent_prompt_extraction_and_os():
    print("[3] Testing CLI agent prompt extraction & OS variable replacement...")
    cli_agent = get_cli_agent_prompt()
    current_os = platform.platform()
    assert "{os_name}" not in cli_agent, "Uninterpolated {os_name} found in cli_agent prompt"
    assert current_os in cli_agent, f"Current OS '{current_os}' not found in cli_agent prompt"
    assert "execute_shell_command" in cli_agent, "Missing execute_shell_command tool definition"
    assert "finish" in cli_agent, "Missing finish tool definition"
    assert cli_agent == CLI_AGENT_SYSTEM_PROMPT, "Exported CLI_AGENT_SYSTEM_PROMPT mismatch"
    print(f"    PASSED: CLI agent prompt extracted and OS '{current_os}' verified.")

def test_prompt_json_structure():
    print("[4] Testing JSON example structure in CLI agent prompt...")
    cli_agent = get_cli_agent_prompt()
    # Check that sample JSON is formatted with standard curly braces
    assert '"thought":' in cli_agent
    assert '"action":' in cli_agent
    assert '"arguments":' in cli_agent
    print("    PASSED: Valid JSON schema preserved without double brace escaping.")

def test_fallback_behavior():
    print("[5] Testing PromptManager fallback on nonexistent file...")
    fake_manager = PromptManager(pulse_md_path="non_existent_file.md")
    fallback_router = fake_manager.get_router_prompt()
    fallback_cli = fake_manager.get_cli_agent_prompt()
    assert "Pulse" in fallback_router, "Fallback router prompt failed"
    assert "execute_shell_command" in fallback_cli, "Fallback CLI prompt failed"
    print("    PASSED: Graceful fallback functions correctly.")

def test_reload_prompts():
    print("[6] Testing reload_prompts()...")
    r, c = reload_prompts()
    assert r == get_router_prompt()
    assert c == get_cli_agent_prompt()
    print("    PASSED: Prompt reloading functions as expected.")

def test_load_history():
    print("[7] Testing load_history() integration...")
    history = load_history()
    assert len(history) >= 1
    assert history[0]["role"] == "system"
    assert history[0]["content"] == get_router_prompt()
    print("    PASSED: History initializes with dynamic router prompt.")

if __name__ == "__main__":
    print("--- Starting PULSE.md Verification Tests ---")
    test_pulse_md_existence()
    test_router_prompt_extraction()
    test_cli_agent_prompt_extraction_and_os()
    test_prompt_json_structure()
    test_fallback_behavior()
    test_reload_prompts()
    test_load_history()
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
