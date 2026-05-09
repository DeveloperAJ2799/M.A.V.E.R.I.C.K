# M.A.V.E.R.I.C.K - AI Agent Framework

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Version-1.0.0-orange.svg" alt="Version">
</p>

**M.A.V.E.R.I.C.K** (Modular Architecture for Versatile and Efficient Reasoning via Intelligent Creative Knowledge) is an AI agent framework with coding capabilities, multi-agent coordination, and dynamic MCP server integration.

## Features

### AI Agents
- **Coding Agent Tools**: grep, glob, edit_file, replace_all, plan, todo for code editing workflows
- **Multi-Agent System**: Supervisor-worker architecture for complex task decomposition
- **Dynamic Tool Loading**: Auto-discovers tools from the tools directory

### Providers
- **Ollama** (local, free) - Run models locally
- **LM Studio** (local) - Local model server
- **NVIDIA API** (cloud) - NVIDIA NIM endpoints
- **Groq** (cloud) - Fast inference
- **OpenAI** (cloud) - GPT models

### Tools
| Category | Tools |
|----------|-------|
| **File Operations** | read_file, write_file, append_file, delete, copy, move, mkdir |
| **Document Creation** | create_pptx, create_pdf, create_docx, create_xlsx |
| **Document Reading** | read_pdf, read_docx, read_xlsx, read_csv |
| **Coding Agent** | grep, glob, edit_file, replace_all, plan, todo |
| **Git Operations** | git_status, git_log, git_diff, git_branch |
| **MCP Integration** | add_mcp_server, list_mcp_servers, remove_mcp_server, call_mcp_tool |
| **System** | shell, search, execute_code, clipboard, notify |

### MCP Server Support
- Connect to MCP servers via HTTP/SSE or stdio
- Add servers dynamically from URLs
- Built-in support for filesystem, git, and memory servers

### Skill System
- Activateable skill modules for specialized tasks
- Create custom skills via chat: `create skill <name> <description>`
- Skills directory with available and custom skills

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/airllm.git
cd airllm

# Install dependencies
pip install -r requirements.txt

# Run setup (first-time users)
python Run_Maverick.py chat

# Or use maverickbot
python -m maverickbot --interactive
```

## Usage

### Interactive Mode
```bash
python -m maverickbot --interactive
```

### Single Prompt
```bash
python -m maverickbot --prompt "Your message"
```

### Using Run_Maverick.py
```bash
python Run_Maverick.py chat "Hello, how are you?"
```

## Configuration

Create a `.env` file with your API keys:

```env
NVIDIA_API_KEY=your_nvidia_api_key
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=your_openai_api_key
```

## Command-Line Options

| Option | Description |
|--------|-------------|
| `-p, --provider` | LLM provider (ollama, lmstudio, nvidia, openai, groq) |
| `-m, --model` | Model name |
| `-i, --interactive` | Start interactive chat mode |
| `-c, --prompt` | Single prompt to execute |
| `-l, --list-models` | List available models |
| `--list-plugins` | List available plugins |
| `--list-skills` | List available skills |
| `--multi-agent` | Enable multi-agent system |
| `-t, --temperature` | Generation temperature (default: 0.7) |
| `--max-tokens` | Max tokens to generate (default: 4096) |

## Interactive Commands

- `help` - Show help message
- `models` - List available LLM models
- `plugins` - List available plugins
- `skills` - List available skills
- `agents` - List multi-agent workers
- `clear` - Clear screen
- `reset` - Reset conversation
- `exit` - Exit interactive mode
- `/skill <name>` - Activate a skill
- `run <command>` - Execute shell command
- `write <path> <content>` - Write to file
- `read <path>` - Read file

## Project Structure

```
maverickbot/
├── agent/           # Agent core and loop
├── cli/             # Command-line interface
├── config/          # Configuration schema
├── core/            # Plugin and skill management
├── multiagent/      # Multi-agent orchestration
├── plugins/         # Plugin templates
├── providers/       # LLM provider implementations
├── skills/          # Skill templates
└── mcp/             # MCP client support
```

