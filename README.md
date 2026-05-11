# M.A.V.E.R.I.C.K

Modular AI agent framework with natural language intent parsing, multi-provider support, document generation, file operations, code editing, multi-agent orchestration, and MCP server integration.

## Providers

| Provider | Type |
|----------|------|
| Ollama | Local (free) |
| LM Studio | Local |
| NVIDIA NIM | Cloud API |
| Groq | Cloud API |
| OpenAI | Cloud API |

## Usage

```bash
# Interactive mode
python -m maverickbot --interactive

# Single prompt
python -m maverickbot --prompt "your message"

# With specific provider
python -m maverickbot --provider ollama --model llama3.2 --interactive
```

## Natural Language UX

Make PDFs, read documents, convert data, and more through plain English:

```bash
# Generate a PDF
make a PDF on types of pollution with 500 words

# Read a document
read myfile.pdf

# Convert data
convert data.csv to json

# Universal file read
read myfile.json
read config.yaml
```

## Tools

| Category | Tools |
|----------|-------|
| **File Operations** | read, write, append, delete, list, copy, move, mkdir, exists, info |
| **Document Create** | create_pdf, create_docx, create_xlsx, create_pptx, create_image |
| **Document Read** | read_pdf, read_docx, read_xlsx, read_csv, read_image |
| **Universal Data** | universal_read, convert_data, create_data_file (auto-detects JSON, YAML, TOML, XML, CSV, HTML) |
| **Code Editing** | grep, glob, edit_file, replace_all, plan, todo |
| **Git** | git_status, git_log, git_diff, git_branch |
| **MCP** | add_mcp_server, list_mcp, remove_mcp, call_mcp_tool |
| **System** | shell, search, execute_code, clipboard, notify, text_to_speech |

## Multi-Agent

Supervisor-worker architecture for complex task decomposition:

```bash
python -m maverickbot --multi-agent --interactive
```

## Architecture

```
maverickbot/
├── agent/           # Core agent loop, tools, workflow, sessions
├── cli/             # CLI entry point and commands
├── config/          # Configuration schema
├── core/            # Plugin and skill management
├── multiagent/      # Multi-agent orchestration
├── plugins/         # Plugin templates
├── providers/       # LLM provider implementations
├── skills/          # Skill templates
├── mcp/             # MCP client
└── ux/              # Natural language intent parsing layer
```
