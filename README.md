# Todo Agent

A natural language interface for [todo.sh](https://github.com/todotxt/todo.txt-cli) task management powered by LLM function calling.

## What it does

Transform natural language into todo.sh commands:

```bash
# Use interactively
todo-agent
# Instead of: todo.sh add "Buy groceries +shopping"
todo-agent "add buy groceries to shopping list"
# Instead of: todo.sh list +work
todo-agent "show my work tasks"
```

## Quick Start

### 1. Install

#### Prerequisites

**Install todo.sh (required)**

todo.sh is the underlying task management system that todo-agent interfaces with.

**macOS:**
```bash
# Using Homebrew
brew install todo-txt
# Or using MacPorts
sudo port install todo-txt
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get install todo-txt-cli
# CentOS/RHEL/Fedora
sudo yum install todo-txt-cli
# or
sudo dnf install todo-txt-cli
# Arch Linux
sudo pacman -S todo-txt-cli
```

**Windows:**
```bash
# Using Chocolatey
choco install todo-txt-cli
# Using Scoop
scoop install todo-txt-cli
```

**From source:**
```bash
git clone https://github.com/todotxt/todo.txt-cli.git
cd todo.txt-cli
make
sudo make install
```

#### Configure todo.sh

After installing todo.sh, you need to set up your todo.txt repository:

```bash
# Create a directory for your todo files
mkdir ~/todo
cd ~/todo

# Initialize todo.sh (this creates the initial todo.txt file)
todo.sh init

# Verify installation
todo.sh version
```

**Important:** Set the `TODO_DIR` environment variable to point to your todo.txt repository:

```bash
export TODO_DIR="$HOME/todo"
```

You can add this to your shell profile (`.bashrc`, `.zshrc`, etc.) to make it permanent.

#### Install todo-agent

```bash
# Clone and install from source
git clone https://github.com/codeprimate/todo-agent.git
cd todo_agent
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

### 2. Set up your LLM provider

**Option A: OpenRouter (recommended)**
```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

**Option B: Ollama (local)**
```bash
# Install and start Ollama
ollama pull mistral-small3.1

# Configure environment
export LLM_PROVIDER=ollama
export OLLAMA_MODEL=mistral-small3.1
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

## Configuration


### Configuration Variables

| Variable              | Description                               | Default                | Required                      |
|-----------------------|-------------------------------------------|------------------------|-------------------------------|
| `LLM_PROVIDER`        | LLM provider: `openrouter` or `ollama`    | `openrouter`           | No (defaults to `openrouter`) |
| `TODO_DIR`            | Path to your todo.txt repository          | —                      | **Yes**                       |
| `OPENROUTER_API_KEY`  | Your OpenRouter API key                   | —                      | Yes (if using OpenRouter)     |
| `OLLAMA_MODEL`        | Model name for Ollama                     | `mistral-small3.1`     | No                            |
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
pip install -e ".[dev]"

# Run tests via Makefile
make test

# Run tests
pytest

# Format code
make format

# Run linting only
make lint
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
