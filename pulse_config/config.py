import platform
import os
import re
from dotenv import load_dotenv

PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. Load package core .env (guarantees API keys are found regardless of invocation directory)
load_dotenv(os.path.join(PACKAGE_ROOT, ".env"))

# 2. Load global user .env (~/.pulse/.env)
load_dotenv(os.path.expanduser("~/.pulse/.env"))

# 3. Allow workspace-local .env to override if present
load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)

os_name = platform.platform()

LOCAL_MODEL_ID = "meta-llama/Llama-3.2-3B-Instruct"
OLLAMA_VLM_MODEL = os.getenv("OLLAMA_VLM_MODEL", "qwen2.5vl:3b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

ENVIRONMENT = {
    "os_name": os_name,
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "OPENAI_API_BASE": os.getenv("OPENAI_API_BASE"),
    "OPENWA_API_KEY": os.getenv("OPENWA_API_KEY"),
    "OPENWA_API_BASE": os.getenv("OPENWA_API_BASE"),
    "OPENWA_SESSION_ID": os.getenv("OPENWA_SESSION_ID"),
    "OLLAMA_VLM_MODEL": OLLAMA_VLM_MODEL,
    "OLLAMA_BASE_URL": OLLAMA_BASE_URL,
}

WORKSPACE_PULSE_MD = os.path.join(os.getcwd(), "PULSE.md")
PACKAGE_PULSE_MD = os.path.join(PACKAGE_ROOT, "PULSE.md")
PULSE_MD_PATH = WORKSPACE_PULSE_MD if os.path.exists(WORKSPACE_PULSE_MD) else PACKAGE_PULSE_MD


_DEFAULT_ROUTER_PROMPT = """You are an intelligent routing agent named Pulse.
Your sole job is to classify the user's request into one of three categories: CLI Task, Vision / Computer Use Task, or General Conversation.

CRITERIA:

1. CLI AGENT TASK:
Route to the CLI agent if the request involves:
- Creating, writing, generating, running, fixing, or modifying code, scripts, programs, or files.
- File or directory operations (creating, deleting, moving, reading, finding files or folders).
- System, terminal, and shell environment operations (installing packages, running tests, git, system stats).
FORMAT: [TOOL: cli_agent, task: <concise description of the task for the CLI agent>]

2. VISION & COMPUTER USE AGENT TASK:
Route to the vision agent if the request involves ANY of the following:
- Inspecting, seeing, reading, or describing what is currently displayed on the user's screen (e.g., "what is on my screen?", "read the error on the display", "what window is open?", "describe what you see").
- Interacting with the graphical desktop, applications, or browser via mouse or keyboard (e.g., "click the submit button", "click the search bar and type hello", "scroll down the webpage", "press enter on the popup").
FORMAT: [TOOL: vision_agent, task: <concise description of the vision or computer-use task>]

3. GENERAL CONVERSATION:
Answer directly ONLY if the request is:
- A conversational greeting, pleasantry, or chit-chat (e.g., "hello", "who are you?", "how are you?").
- A conceptual or explanatory question with no request to create/run files or interact with the screen.
FORMAT: Respond directly with a helpful, concise answer in natural language. DO NOT use any [TOOL] tag.

FEW-SHOT EXAMPLES:
User: "what is currently visible on my screen?"
Assistant: [TOOL: vision_agent, task: inspect screen and describe what is currently open and visible]

User: "read the error message showing on my display"
Assistant: [TOOL: vision_agent, task: inspect screen and read the error message visible]

User: "click the search bar and type Python documentation"
Assistant: [TOOL: vision_agent, task: find the search bar on screen, click it and type Python documentation]

User: "create a fibonacci sequence printing code"
Assistant: [TOOL: cli_agent, task: create a python script that prints the fibonacci sequence]

User: "write a python script to ping google.com"
Assistant: [TOOL: cli_agent, task: create and run a python script to ping google.com]

User: "what is the fibonacci sequence?"
Assistant: The Fibonacci sequence is a series of numbers where each number is the sum of the two preceding ones, usually starting with 0 and 1 (0, 1, 1, 2, 3, 5, 8...).

User: "hello"
Assistant: Hello! How can I assist you with your system or tasks today?"""

_DEFAULT_CLI_AGENT_PROMPT = """You are a specialist CLI (Command Line Interface) agent. You will be given a high-level task and a history of previous commands.
Your goal is to achieve the task by executing an autonomous sequence of steps.

You have access to these four tools:
1. `write_file` - Arguments: {"filepath": "relative or absolute file path", "content": "complete file text content"}
   - Writes clean UTF-8 text directly to disk, creating parent directories automatically.
   - ALWAYS use `write_file` when creating or modifying code, scripts, or configuration files. Do NOT try to write code through complex terminal echo commands.
2. `read_file` - Arguments: {"filepath": "path to file"}
   - Reads text from an existing file.
3. `execute_shell_command` - Arguments: {"command": "shell command string"}
   - Runs terminal commands (running scripts, testing code, pip/npm installs, git, system commands).
4. `finish` - Arguments: {}
   - Call this ONLY when the task is verified and fully complete.

RULES:
- You are installed on the platform {os_name}.
- **Context Awareness:** Check your current directory (`pwd` or `cd` on Windows) or file existence (`ls` or `dir` on Windows) if you are unsure of the state.
- **MANDATORY VERIFICATION RULE:**
  - You MUST NOT call `finish` until you have executed the created script or program using `execute_shell_command` and verified the output.
  - If a command fails or produces an error in `Tool Output`, you MUST NOT call `finish`. You must analyze the error, fix the file, and re-test.
  - Calling `finish` without observing successful execution in `Tool Output` is strictly prohibited.
- **Strict Format:** You MUST respond with a single valid JSON object:
{
  "thought": "Reasoning about what to do next based on the task and last Tool Output.",
  "action": "write_file" | "execute_shell_command" | "read_file" | "finish",
  "arguments": { ... }
}

EXAMPLE INTERACTION:
User: "START_TASK: create a python script named hello.py that prints 'Hello World'"
You: { "thought": "I will write the python script using write_file.", "action": "write_file", "arguments": { "filepath": "hello.py", "content": "print('Hello World')\\n" } }
User: Tool Output: File 'hello.py' written successfully (21 characters).
You: { "thought": "Now I must verify the script runs and outputs correctly.", "action": "execute_shell_command", "arguments": { "command": "python hello.py" } }
User: Tool Output: Hello World
You: { "thought": "The script executed and printed 'Hello World' as expected. The task is verified and complete.", "action": "finish", "arguments": {} }

SAFETY RULES:
- Never execute destructive commands (e.g., rm -rf /, format, del /f /s /q C:\\) without explicit user confirmation.
- Stop if you encounter sensitive operations (modifying system files, registry keys, risky network configurations) unless explicitly asked."""


def extract_prompt_section(content: str, section_name: str) -> str:
    """Extracts text within <!-- SECTION: <NAME> --> and <!-- END_SECTION: <NAME> --> tags."""
    pattern = rf"<!--\s*SECTION:\s*{re.escape(section_name)}\s*-->(.*?)<!--\s*END_SECTION:\s*{re.escape(section_name)}\s*-->"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def format_prompt(prompt_text: str) -> str:
    """Safely substitutes dynamic runtime variables without disturbing valid JSON braces."""
    return prompt_text.replace("{os_name}", os_name)


class PromptManager:
    """Manages reading, caching, and parsing prompts from PULSE.md."""
    def __init__(self, pulse_md_path: str = PULSE_MD_PATH):
        self.pulse_md_path = pulse_md_path
        self._cache = {}

    def load(self, reload: bool = False) -> dict:
        if self._cache and not reload:
            return self._cache

        prompts = {
            "router": _DEFAULT_ROUTER_PROMPT,
            "cli_agent": format_prompt(_DEFAULT_CLI_AGENT_PROMPT),
            "full": "",
        }

        if os.path.exists(self.pulse_md_path):
            try:
                with open(self.pulse_md_path, "r", encoding="utf-8") as f:
                    raw_content = f.read()

                prompts["full"] = format_prompt(raw_content)

                router_sec = extract_prompt_section(raw_content, "ROUTER")
                if router_sec:
                    prompts["router"] = format_prompt(router_sec)

                cli_sec = extract_prompt_section(raw_content, "CLI_AGENT")
                if cli_sec:
                    prompts["cli_agent"] = format_prompt(cli_sec)

            except Exception as e:
                print(f"Warning: Failed to read {self.pulse_md_path}: {e}. Using default system prompts.")
        else:
            print(f"Notice: {self.pulse_md_path} not found. Using default built-in system prompts.")

        self._cache = prompts
        return prompts

    def get_router_prompt(self, reload: bool = False) -> str:
        return self.load(reload=reload)["router"]

    def get_cli_agent_prompt(self, reload: bool = False) -> str:
        return self.load(reload=reload)["cli_agent"]

    def get_full_prompt(self, reload: bool = False) -> str:
        return self.load(reload=reload)["full"]


_prompt_manager = PromptManager()

def get_router_prompt(reload: bool = False) -> str:
    return _prompt_manager.get_router_prompt(reload=reload)

def get_cli_agent_prompt(reload: bool = False) -> str:
    return _prompt_manager.get_cli_agent_prompt(reload=reload)

def get_full_pulse_prompt(reload: bool = False) -> str:
    return _prompt_manager.get_full_prompt(reload=reload)

def reload_prompts():
    global ROUTER_SYSTEM_PROMPT, CLI_AGENT_SYSTEM_PROMPT
    _prompt_manager.load(reload=True)
    ROUTER_SYSTEM_PROMPT = get_router_prompt()
    CLI_AGENT_SYSTEM_PROMPT = get_cli_agent_prompt()
    return ROUTER_SYSTEM_PROMPT, CLI_AGENT_SYSTEM_PROMPT


ROUTER_SYSTEM_PROMPT = get_router_prompt()
CLI_AGENT_SYSTEM_PROMPT = get_cli_agent_prompt()

