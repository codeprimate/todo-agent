# Todo Agent

A natural language interface for [todo.sh](https://github.com/todotxt/todo.txt-cli) task management powered by LLM function calling.

## What it does

Transform natural language into todo.sh commands with intelligent task management:

```bash
# Use interactively
todo-agent
# Instead of: todo.sh add "Buy groceries +shopping"
todo-agent "add buy groceries to shopping list"
# Instead of: todo.sh list +work
todo-agent "show my work tasks"
```

## Why Todo Agent?

**Speak naturally** instead of memorizing commands. Todo Agent understands "add dentist appointment next Monday" and automatically sets the right date, project, and context.

**Get intelligent insights** beyond basic task lists. It organizes tasks strategically, suggests priorities, and recommends optimal timing based on your patterns.

**Work smarter** with automatic duplicate detection and calendar-aware scheduling.

**Choose your privacy** - use cloud AI (OpenRouter) or run locally (Ollama).

## Quick Start

### 1. Install

#### Install todo.sh (required)

**macOS:** `brew install todo-txt`  
**Linux:** `sudo apt-get install todo-txt-cli` (Ubuntu/Debian) or `sudo pacman -S todo-txt-cli` (Arch)  
**Windows:** `choco install todo-txt-cli` (Chocolatey) or `scoop install todo-txt-cli` (Scoop)

#### Set up todo.sh

```bash
# Create and initialize your todo directory
mkdir ~/todo && cd ~/todo
todo.sh init

# Add to your shell profile (.bashrc, .zshrc, etc.)
export TODO_DIR="$HOME/todo"
```

#### Create your todo.sh configuration

```bash
# Copy the example configuration to your todo directory
# If you cloned the repository:
cp todo-agent/config.example $TODO_DIR/config
# Or if you installed via pip, the config.example is in the package directory

# Edit the configuration file to customize your setup
# The config.example includes enhanced colors, priorities, and workflow settings
nano $TODO_DIR/config  # or use your preferred editor
```

**Configuration highlights:**
- Enhanced priority system with emojis and clear meanings
- Color-coded output for better visual organization  
- Automatic archiving of old completed tasks
- Customizable sorting and filtering options

#### Install todo-agent

```bash
git clone https://github.com/codeprimate/todo-agent.git
cd todo_agent
make install
```

### 2. Set up your LLM provider

**Option A: OpenRouter (recommended)**
```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

**Option B: Ollama (local)**
```bash
# Install and start Ollama
ollama pull gpt-oss:20b

# Configure environment
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=gpt-oss:20b
```

### 3. Use it

```bash
# Interactive mode
todo-agent

# Single command
todo-agent "add urgent meeting with team +work @office"
```

## Examples

### Task Management
```bash
todo-agent "add buy groceries to shopping list"
todo-agent "list my work tasks"
todo-agent "complete the shopping task"
todo-agent "delete task 5"
```

### Task Modification
```bash
todo-agent "change task 2 to buy organic milk"
todo-agent "add urgent to task 1"
todo-agent "set task 3 as high priority"
```

### Discovery
```bash
todo-agent "what projects do I have?"
todo-agent "show completed tasks"
todo-agent "list my contexts"
```

### Strategic Planning
```bash
todo-agent "what should I do next?"
todo-agent "organize my tasks by priority"
todo-agent "show me everything due this week"
todo-agent "what tasks are blocking other work?"
```

### Natural Language Intelligence
```bash
todo-agent "add dentist appointment next Monday"

todo-agent "move all completed tasks to archive"
todo-agent "show me tasks I can do from home"
```

## Configuration


### Configuration Variables

| Variable              | Description                               | Default                | Required                      |
|-----------------------|-------------------------------------------|------------------------|-------------------------------|
| `LLM_PROVIDER`        | LLM provider: `openrouter` or `ollama`    | `openrouter`           | No (defaults to `openrouter`) |
| `TODO_DIR`            | Path to your todo.txt repository          | —                      | **Yes**                       |
| `OPENROUTER_API_KEY`  | Your OpenRouter API key                   | —                      | Yes (if using OpenRouter)     |
| `OLLAMA_MODEL`        | Model name for Ollama                     | `gpt-oss:20b`     | No                            |
| `LOG_LEVEL`           | Logging verbosity (`INFO`, `DEBUG`, etc.) | `INFO`                 | No                            |

**Note:**  
- `TODO_DIR` is required for all configurations.  
- `OPENROUTER_API_KEY` is only required if you use the OpenRouter provider.  
- The `TODO_FILE`, `DONE_FILE`, and `REPORT_FILE` are automatically inferred from `TODO_DIR`.

The `TODO_FILE`, `DONE_FILE`, and `REPORT_FILE` are automatically inferred from `TODO_DIR`.

## Development

```bash
# Clone and install
git clone https://github.com/codeprimate/todo-agent.git
cd todo_agent

# Install options:
# - Built package (like production install)
make install
# - Development mode with dev dependencies (recommended for development)
make install-dev
# - Basic development mode
pip install -e .

# Available Makefile tasks:
make test      # Run tests with coverage
make format    # Format and lint code
make lint      # Run linting only
make build     # Build package distribution
make clean     # Clean build artifacts
make install   # Build and install package locally
make install-dev # Install in development mode with dev dependencies
```

## Code Quality and Linting

This project uses comprehensive linting to maintain code quality:

### Linting Tools
- **Ruff**: Fast Python linter and formatter (replaces Black, isort, and Flake8)
- **MyPy**: Static type checking
- **Bandit**: Security vulnerability scanning

**Note**: Ruff is configured to be compatible with Black's formatting style and provides 10-100x faster performance than traditional tools.

### Pre-commit Hooks
Install pre-commit hooks for automatic linting on commits:
```bash
pre-commit install
```

### Linting in Test Suite
Linting checks are integrated into the test suite via `tests/test_linting.py`. The `make test` command runs all tests including linting checks. You can also run linting tests separately:
```bash
# Run linting tests only
pytest -m lint
```

### Configuration Files
- `pyproject.toml`: Ruff, MyPy, and pytest configuration
- `.pre-commit-config.yaml`: Pre-commit hooks configuration
```

## Architecture

The todo-agent follows a clean, layered architecture with clear separation of concerns:

### **Interface Layer** (`todo_agent/interface/`)
- **CLI**: User interaction, input/output handling, and application loop
- **Tools**: Function schemas and execution logic for LLM function calling
- **Formatters**: Output formatting and presentation

### **Core Layer** (`todo_agent/core/`)
- **TodoManager**: Business logic orchestrator that translates high-level operations into todo.sh commands
- **ConversationManager**: Manages conversation state, memory, and context for multi-turn interactions
- **TaskParser**: Parses and validates task-related operations
- **Exceptions**: Custom exception classes for error handling

### **Infrastructure Layer** (`todo_agent/infrastructure/`)
- **Inference Engine**: Orchestrates LLM interactions, tool calling, and conversation flow
- **LLM Clients**: Provider-specific implementations (OpenRouter, Ollama) with factory pattern
- **TodoShell**: Subprocess wrapper for executing todo.sh commands
- **Configuration**: Environment and settings management
- **Logging**: Structured logging throughout the application
- **Token Counter**: Manages conversation token limits and costs

### **How It Works**

1. **User Input** → Natural language request (e.g., "add buy groceries to shopping list")
2. **CLI** → Captures input and passes to inference engine
3. **Inference Engine** → Sends request to LLM with available tools
4. **LLM** → Analyzes request and decides which tools to call
5. **Tool Execution** → TodoManager → TodoShell → todo.sh
6. **Response** → Results returned through conversation manager to user

### **Key Features**
- **Function Calling**: LLM intelligently selects and executes appropriate tools
- **Conversation Memory**: Maintains context across interactions
- **Multi-Provider Support**: Works with cloud (OpenRouter) and local (Ollama) LLMs
- **Error Handling**: Robust error management with detailed logging
- **Performance Monitoring**: Tracks thinking time and conversation metrics

## License

GNU General Public License v3.0

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
