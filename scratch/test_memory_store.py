import os
import sys

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pulse_brain.memory_base.memory import Memory
from pulse_brain.llm_interface import Agent


def test_memory_store_unit():
    print("[1] Testing Memory initialization and namespaces...")
    mem = Memory(session_id="test_session")
    assert mem.session_id == "test_session"
    assert mem.conversation_namespace == ("conversations", "test_session")
    assert mem.default_data_namespace == ("data", "test_session")
    print("    PASSED: Namespaces configured properly.")

    print("[2] Testing sequential message storage and chronological order...")
    mem.add_message("user", "Hello assistant!")
    mem.add_message("assistant", "Hello user, how can I help?")
    mem.add_message("user", "What is the capital of France?")
    mem.add_message("assistant", "The capital of France is Paris.")

    history = mem.get_history(limit=10)
    assert len(history) == 4, f"Expected 4 messages, got {len(history)}"
    assert history[0]["role"] == "user" and history[0]["content"] == "Hello assistant!"
    assert history[1]["role"] == "assistant"
    assert history[2]["role"] == "user" and history[2]["content"] == "What is the capital of France?"
    assert history[3]["role"] == "assistant" and history[3]["content"] == "The capital of France is Paris."
    print("    PASSED: Messages stored and retrieved in chronological order.")

    print("[3] Testing context window limit in get_history...")
    limited_history = mem.get_history(limit=1)
    assert len(limited_history) == 2, f"Expected 2 messages (1 turn), got {len(limited_history)}"
    assert limited_history[0]["content"] == "What is the capital of France?"
    assert limited_history[1]["content"] == "The capital of France is Paris."
    print("    PASSED: Context window slicing works as expected.")

    print("[4] Testing arbitrary key-value storage (save and get)...")
    mem.save("user_profile", {"name": "Vinayak", "preferred_mode": "text"})
    profile = mem.get("user_profile")
    assert profile is not None, "Failed to retrieve stored profile"
    assert profile["name"] == "Vinayak"
    assert profile["preferred_mode"] == "text"
    assert mem.get("non_existent_key") is None
    print("    PASSED: Structured key-value storage functions cleanly.")

    print("[5] Testing search functionality...")
    search_results = mem.search(query="France")
    assert len(search_results) > 0, "Expected search results"
    print(f"    PASSED: Search returned {len(search_results)} items.")

    print("[6] Testing memory clearing...")
    mem.clear()
    cleared_history = mem.get_history()
    assert len(cleared_history) == 0, f"Expected empty history after clear, got {len(cleared_history)}"
    print("    PASSED: Session conversation memory cleared cleanly.")


def test_agent_memory_integration():
    print("[7] Testing Agent integration with Memory and sliding context...")
    agent = Agent(name="PulseTest", session_id="agent_test_session", context_window=2)
    assert agent.name == "PulseTest"
    assert agent.context_window == 2
    assert isinstance(agent.memory, Memory)

    agent.remember("user", "Message 1")
    agent.remember("assistant", "Response 1")
    agent.remember("user", "Message 2")
    agent.remember("assistant", "Response 2")
    agent.remember("user", "Message 3")
    agent.remember("assistant", "Response 3")

    # context window is 2 turns = 4 messages
    ctx = agent.get_context()
    assert len(ctx) == 4, f"Expected 4 messages for context window of 2, got {len(ctx)}"
    assert ctx[0]["content"] == "Message 2"
    assert ctx[3]["content"] == "Response 3"
    print("    PASSED: Agent sliding context window works correctly.")


def test_persistence_lifecycle():
    print("[8] Testing cross-session SQLite persistence and restore lifecycle...")
    test_db = "scratch/temp_lifecycle_test.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    # Session 1: Create, add messages, persist
    m1 = Memory(session_id="user_session_1", db_path=test_db)
    m1.add_message("user", "My name is Vinayak and I am an AIML engineer.")
    m1.add_message("assistant", "Hello Vinayak! Nice to meet an AIML engineer.")
    saved_count = m1.persist_to_db()
    assert saved_count == 2, f"Expected 2 messages saved, got {saved_count}"
    print("    PASSED: Session 1 persisted 2 messages to SQLite.")

    # Session 2: Fresh instance (simulating CLI restart), auto-load from SQLite
    m2 = Memory(session_id="user_session_1", db_path=test_db, auto_load=True)
    history = m2.get_history()
    assert len(history) == 2, f"Expected 2 restored messages, got {len(history)}"
    assert history[0]["content"] == "My name is Vinayak and I am an AIML engineer."
    assert history[1]["content"] == "Hello Vinayak! Nice to meet an AIML engineer."
    print("    PASSED: Session 2 restored previous conversation into InMemoryStore.")

    # Test clear removes from both
    m2.clear()
    assert len(m2.get_history()) == 0
    m3 = Memory(session_id="user_session_1", db_path=test_db, auto_load=True)
    assert len(m3.get_history()) == 0
    print("    PASSED: Memory clear flushed both RAM and persistent SQLite.")

    if os.path.exists(test_db):
        os.remove(test_db)


if __name__ == "__main__":
    print("--- Starting In-Memory Store Test Suite ---")
    test_memory_store_unit()
    test_agent_memory_integration()
    test_persistence_lifecycle()
    print("\nALL IN-MEMORY STORE TESTS PASSED SUCCESSFULLY!")

