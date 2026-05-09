# M.A.V.E.R.I.C.K

M.A.V.E.R.I.C.K is an AI agent framework with plugin architecture, skill system, and multi-agent coordination capabilities. It provides an interactive CLI for working with large language models and executing various tools.

## Features

- **Multiple LLM Providers**: Support for Ollama, LM Studio, NVIDIA, OpenAI, and Groq
- **Tool System**: File operations, shell command execution, search, and more
- **Plugin Architecture**: Extensible plugin system for adding custom tools and providers
- **Skill System**: Activateable skill modules for specialized tasks
- **Multi-Agent System**: Supervisor-worker architecture for complex task decomposition
- **Interactive CLI**: Rich command-line interface with tab completion and history

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file with your API keys:

```env
NVIDIA_API_KEY=your_nvidia_api_key
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=your_openai_api_key
```

## Usage

### Interactive Mode

```bash
python -m maverickbot --interactive
```

### Single Prompt

```bash
python -m maverickbot --prompt "Your message here"
```

### Specify Provider and Model

```bash
python -m maverickbot -p nvidia -m meta/llama-3.1-70b-instruct --interactive
```

### Enable Multi-Agent System

```bash
python -m maverickbot --multi-agent --interactive
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


