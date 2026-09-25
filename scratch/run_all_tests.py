from scratch.test_agent_robustness import *
from scratch.test_history_awareness import *
from scratch.test_pulse_prompt import *
from scratch.test_router_classification import *
from scratch.test_whisper_asr_and_response import *

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

    print("--- Starting CLI Agent Robustness Test Suite ---")
    test_json_extractor_resilience()
    test_file_tools()
    test_live_agent_loop_with_verification()
    print("\nALL AGENT ROBUSTNESS TESTS COMPLETED SUCCESSFULLY!")

    print("\n--- Starting History Awareness Test Suite ---")
    test_history_awareness()

    print("--- Starting Router & Dispatcher Test Suite ---")
    test_parse_tool_call_and_dispatcher()
    test_live_router_classification()
    print("\nALL ROUTER TESTS COMPLETED SUCCESSFULLY!")

    
    asr_stt_tests()