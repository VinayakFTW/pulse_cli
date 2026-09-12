import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pulse_brain.llm_interface import load_openai_model
client, _ = load_openai_model()

hist = [
    {"role": "user", "content": "START_TASK: create a file test.txt with text hello"},
    {"role": "assistant", "content": '{"thought": "I will run echo hello into test.txt", "action": "execute_shell_command", "arguments": {"command": "echo hello"}}'},
    {"role": "user", "content": "Tool Output: Command failed with error: Access denied. Permission denied to write test.txt."},
]

res = client.responses.create(
    model="gpt-5",
    instructions="You are a CLI agent. You must analyze the last Tool Output. If it failed, acknowledge the error in thought and try a different approach.",
    input=hist
)

print("RESPONSE TO FAILED TOOL OUTPUT:\n", res.output_text)
