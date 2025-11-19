# Pulse CLI Agent

## Overview

**Pulse CLI** is a specialized command-line agent extracted from the larger **PulseAI** assistant project. While the full PulseAI system includes voice interaction, general conversation capabilities, and multi-modal features, Pulse CLI focuses specifically on executing terminal commands and performing system-level tasks through natural language instructions.

Pulse CLI acts as an intelligent shell command executor that can:
- Understand high-level task descriptions in natural language
- Break down complex tasks into sequential shell commands
- Execute commands autonomously with verification and error handling
- Adapt its approach based on command outputs and errors

## Architecture

The system operates in two primary modes:

### 1. **Router Mode**
The initial layer that determines whether a user query requires CLI operations or is a general conversation. The router analyzes the intent and dispatches to the appropriate handler.

### 2. **CLI Agent Mode**
A specialized agentic loop that:
- Receives a high-level task description
- Plans and executes shell commands step-by-step
- Verifies command success before proceeding
- Handles errors and adapts its strategy
- Continues until the task is complete (up to 10 steps)

## Key Features

### 🧠 **Dual Model Support**
- **Local Inference**: Uses Meta's Llama 3.2 3B Instruct model for offline operation
- **Cloud Fallback**: Automatically switches to Google's Gemini 2.5 Pro API if local model fails
- Seamless transition between models without user intervention

### 🎤 **Flexible Input Modes**
- **Voice Mode**: Natural voice commands using Google Speech Recognition
- **Text Mode**: Traditional text-based CLI interaction
- User selects preferred mode at startup

### 🔄 **Agentic Task Execution**
The CLI agent follows a Think-Act-Observe loop:
1. **Think**: Analyzes the task and command history to plan the next step
2. **Act**: Executes a shell command using the available tool
3. **Observe**: Processes command output and adjusts strategy
4. **Repeat**: Continues until task completion or step limit

### 🛡️ **Safety Features**
- Rate limiting to prevent API quota exhaustion (32-second delay between requests)
- Context awareness (checks current directory, verifies file existence)
- Error handling with adaptive retry mechanisms
- Conversation history persistence (maintains last 20 exchanges)

### 📝 **Conversation History**
- Automatically saves conversation history to `conversation_history.json`
- Maintains context across sessions
- Limits history to prevent token overflow (system prompt + last 20 messages)

## System Requirements

### Hardware
- **For Local Model**:
  - GPU with CUDA support (recommended)
  - Minimum 8GB VRAM
  - 16GB+ system RAM
- **For Gemini API Only**:
  - Any modern CPU
  - Stable internet connection

### Software
- Python 3.8 or higher
- CUDA Toolkit (for GPU acceleration with local model)
- Operating System: Windows, Linux, or macOS

## Installation & Setup

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd pulse-cli
```

### Step 2: Create Virtual Environment

```bash
python -m venv .venv

# On Windows
.venv\Scripts\activate

# On Linux/Mac
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**For GPU support with PyTorch:**
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

**To obtain a Gemini API key:**
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key to your `.env` file

### Step 5: Hugging Face Configuration (For Local Model)

Meta's Llama 3.2 3B Instruct is a **gated repository** on Hugging Face, requiring explicit access approval.

#### 5.1: Request Access
1. Visit [meta-llama/Llama-3.2-3B-Instruct](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct)
2. Click "Request Access" and accept Meta's license agreement
3. Wait for approval (usually within minutes to hours)

#### 5.2: Install Hugging Face CLI
```bash
pip install huggingface_hub
```

#### 5.3: Login to Hugging Face
```bash
huggingface-cli login
```

When prompted, provide your Hugging Face token:
1. Go to [Hugging Face Tokens](https://huggingface.co/settings/tokens)
2. Create a new token with "Read" permissions
3. Copy and paste the token when prompted in the terminal

#### 5.4: Verify Access
```bash
huggingface-cli whoami
```

This should display your Hugging Face username, confirming successful authentication.

### Step 6: Verify Installation

Run the agent:
```bash
python cli_agent.py
```

You should see:
```
Initializing PulseAI...
Attempting to load local model: meta-llama/Llama-3.2-3B-Instruct...
```

If the local model loads successfully, you're ready to go. If it fails, the system will automatically fall back to Gemini API.

## Usage

### Starting the Agent

```bash
python cli_agent.py
```

### Selecting Input Mode

On startup, choose your preferred input mode:
```
Select Input Mode:
1. Voice Mode (Default)
2. Text Mode
Choice (1/2):
```

### Example Interactions

#### Voice Mode Example:
```
Listening... (Google Online)
Recognized: create a python script named test.py that prints hello world

CLI Agent Activated. Task: create a python script named test.py that prints hello world
Thinking (Step 1)...
CLI Agent Thought: I will create the file using echo command
Running command: echo "print('Hello World')" > test.py
CLI Agent Observation: Command executed successfully.
...
CLI Task Complete.
```

#### Text Mode Example:
```
Vinayak (Text): create a directory called projects and add a readme file

Executed tool: cli_agent
Result: CLI task finished.
```

### Sample Tasks

The CLI agent can handle tasks like:
- **File Operations**: `create a config.json file with default settings`
- **Git Operations**: `initialize a git repository and make first commit`
- **System Info**: `show me the current disk usage`
- **Script Creation**: `write a bash script that backs up my documents folder`
- **Development Setup**: `create a python virtual environment and install flask`

## Project Structure

```
pulse-cli/
├── cli_agent.py              # Main entry point
├── pulse_brain/
│   ├── brain.py              # CLI agent loop logic
│   └── llm_interface.py      # LLM interaction layer
├── pulse_config/
│   └── config.py             # System prompts and configuration
├── pulse_ear/
│   └── speech_handler.py     # Voice input/output handlers
├── pulse_tools/
│   └── general_tools.py      # Shell command execution
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (not in repo)
└── .gitignore
```

## How It Works

### 1. Query Processing Flow

```
User Input → Router (decides: CLI task or chat)
    ↓
    ├─→ [CHAT] → Direct response
    │
    └─→ [TOOL: cli_agent, task: ...] → CLI Agent Loop
            ↓
            Think → Act → Observe (repeat until done)
            ↓
            Task Complete
```

### 2. CLI Agent Decision Format

The agent uses structured JSON responses:
```json
{
  "thought": "Reasoning about the next step",
  "action": "execute_shell_command",
  "arguments": {
    "command": "ls -la"
  }
}
```

Or to finish:
```json
{
  "thought": "Task is complete",
  "action": "finish",
  "arguments": {}
}
```

### 3. Rate Limiting Strategy

To prevent API quota issues:
- Tracks timestamp of last API request
- Enforces 32-second minimum delay between consecutive requests
- Displays countdown when waiting
- Only applies to CLI agent loop (not initial router check)

## Troubleshooting

### Local Model Fails to Load

**Error**: `System incapable of running local model`

**Solutions**:
1. Verify GPU availability: `nvidia-smi` (for NVIDIA GPUs)
2. Check CUDA installation: `nvcc --version`
3. Ensure Hugging Face access is granted
4. Verify you're logged in: `huggingface-cli whoami`
5. System will automatically fall back to Gemini API

### Voice Recognition Issues

**Error**: `Sorry, I didn't understand that`

**Solutions**:
1. Check microphone permissions
2. Verify internet connection (required for Google Speech Recognition)
3. Speak clearly and reduce background noise
4. Switch to text mode as alternative

### Gemini API Errors

**Error**: `I encountered an error reaching the Gemini API`

**Solutions**:
1. Verify API key in `.env` file
2. Check API quota at [Google AI Studio](https://aistudio.google.com/)
3. Ensure stable internet connection
4. Wait for rate limit reset if exceeded

### Command Execution Failures

If CLI commands fail repeatedly:
1. Check command syntax for your OS (Windows vs. Linux/Mac)
2. Verify file permissions
3. Review command history in conversation logs
4. Try simpler commands to isolate the issue

## Limitations

- **Step Limit**: CLI agent has a maximum of 10 steps per task
- **No Interactive Commands**: Cannot handle commands requiring user input (use `yes` or heredocs)
- **Platform Differences**: Some commands differ between Windows and Unix systems
- **Network Dependency**: Voice mode requires internet for speech recognition
- **Context Window**: Limited to recent conversation history (20 messages)

## Future Enhancements (Full PulseAI)

The complete PulseAI system includes:
- Multi-modal capabilities (image, document processing)
- Persistent memory across sessions
- Additional tool integrations (web browsing, email, calendar)
- Enhanced voice synthesis with Piper TTS
- Offline speech recognition with Whisper
- Custom wake word detection
- Scheduled task execution

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License

Copyright (c) 2025 Vinayak Varshney

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Acknowledgments

- Meta AI for Llama 3.2 3B Instruct
- Google for Gemini 2.5 Pro API
- Hugging Face for model hosting and transformers library
- Open source community for supporting libraries

## Acknowledgments

- Meta AI for Llama 3.2 3B Instruct
- Google for Gemini 2.5 Pro API
- Hugging Face for model hosting and transformers library
- Open source community for supporting libraries

---

**Note**: This is a development tool that executes shell commands on your system. Always review the commands the agent plans to execute and use appropriate caution, especially with destructive operations.