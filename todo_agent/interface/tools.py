"""
Tool definitions and schemas for LLM function calling.
"""

from typing import Any, Callable, Dict, List, Optional

try:
    from todo_agent.core.todo_manager import TodoManager
    from todo_agent.infrastructure.logger import Logger
except ImportError:
    from core.todo_manager import TodoManager  # type: ignore[no-redef]
    from infrastructure.logger import Logger  # type: ignore[no-redef]


class ToolCallHandler:
    """Handles tool execution and orchestration."""

    def __init__(self, todo_manager: TodoManager, logger: Optional[Logger] = None):
        self.todo_manager = todo_manager
        self.logger = logger
        self.tools = self._define_tools()

    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define available tools for LLM function calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_projects",
                    "description": (
                        "Get all available projects from todo.txt. Use this when: "
                        "1) User mentions 'project' but doesn't specify which one, "
                        "2) User uses a generic term like 'work' that could match multiple projects, "
                        "3) You need to understand what projects exist before making decisions. "
                        "STRATEGIC CONTEXT: This is a discovery tool - call this FIRST when project ambiguity exists "
                        "to avoid asking the user for clarification when you can find the answer yourself."
                    ),
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_contexts",
                    "description": (
                        "Get all available contexts from todo.txt. Use this when: "
                        "1) User mentions 'context' but doesn't specify which one, "
                        "2) User uses a generic term like 'office' that could match multiple contexts, "
                        "3) You need to understand what contexts exist before making decisions. "
                        "STRATEGIC CONTEXT: This is a discovery tool - call this FIRST when context ambiguity exists "
                        "to avoid asking the user for clarification when you can find the answer yourself."
                    ),
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_tasks",
                    "description": (
                        "List current tasks with optional filtering. Use this when: "
                        "1) User wants to see their tasks, "
                        "2) You need to find a specific task by description, "
                        "3) You need to check for potential duplicates before adding new tasks, "
                        "4) You need to understand the current state before making changes. "
                        "CRITICAL: ALWAYS use this before add_task() to check for similar existing tasks. "
                        "IMPORTANT: When presenting the results to the user, convert the raw todo.txt format "
                        "into conversational language. Do not show the raw format like '(A) task +project @context'. "
                        "STRATEGIC CONTEXT: This is the primary discovery tool - call this FIRST when you need to "
                        "understand existing tasks before making any modifications."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filter": {
                                "type": "string",
                                "description": (
                                    "Optional filter string (e.g., '+work', '@office', '(A)') - "
                                    "use when you want to see only specific tasks"
                                ),
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_completed_tasks",
                    "description": (
                        "List completed tasks from done.txt with optional filtering. Use this when: "
                        "1) User tries to complete a task that might already be done, "
                        "2) User asks about completed tasks, "
                        "3) You need to verify task status before taking action, "
                        "4) User wants to search for specific completed tasks by project, context, text, or date. "
                        "STRATEGIC CONTEXT: Call this BEFORE complete_task() to verify the task hasn't already "
                        "been completed, preventing duplicate completion attempts. "
                        "FILTERING: Use the filtering parameters to help users find specific completed tasks "
                        "when they ask about work tasks, home tasks, tasks from a specific date, etc. "
                        "DATE FILTERING LIMITATIONS: Due to todo.sh constraints, date filtering has specific behavior: "
                        "• When both date_from and date_to are provided, filtering uses the year-month pattern (YYYY-MM) "
                        "from date_from, matching all tasks in that month. "
                        "• When only date_from is provided, filtering uses the exact date pattern (YYYY-MM-DD). "
                        "• When only date_to is provided, filtering uses the year-month pattern (YYYY-MM) from date_to. "
                        "• Complex date ranges (e.g., spanning multiple months) are not supported by todo.sh."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filter": {
                                "type": "string",
                                "description": (
                                    "Optional raw filter string (e.g., '+work', '@office') - "
                                    "use for advanced filtering when other parameters aren't sufficient"
                                ),
                            },
                            "project": {
                                "type": "string",
                                "description": (
                                    "Optional project name to filter by (without the + symbol) - "
                                    "e.g., 'work', 'home', 'bills'"
                                ),
                            },
                            "context": {
                                "type": "string",
                                "description": (
                                    "Optional context name to filter by (without the @ symbol) - "
                                    "e.g., 'office', 'home', 'phone'"
                                ),
                            },
                            "text_search": {
                                "type": "string",
                                "description": (
                                    "Optional text to search for in task descriptions - "
                                    "e.g., 'review', 'call', 'email'"
                                ),
                            },
                            "date_from": {
                                "type": "string",
                                "description": (
                                    "Optional start date for filtering (YYYY-MM-DD format) - "
                                    "e.g., '2025-08-01'. When used alone, matches exact date. "
                                    "When used with date_to, uses year-month pattern (YYYY-MM) for month-based filtering."
                                ),
                            },
                            "date_to": {
                                "type": "string",
                                "description": (
                                    "Optional end date for filtering (YYYY-MM-DD format) - "
                                    "e.g., '2025-08-31'. When used alone, uses year-month pattern (YYYY-MM) "
                                    "for month-based filtering. When used with date_from, uses date_from's year-month pattern."
                                ),
                            },
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "add_task",
                    "description": (
                        "Add a new task to todo.txt. CRITICAL: Before adding ANY task, you MUST "
                        "use list_tasks() and list_completed_tasks() to check for potential duplicates. Look for tasks with "
                        "similar descriptions, keywords, or intent. If you find similar tasks, "
                        "ask the user if they want to add a new task or modify an existing one. "
                        "If project or context is ambiguous, use discovery tools first. "
                        "Always provide a complete, natural response to the user. "
                        "STRATEGIC CONTEXT: This is a modification tool - call this LAST after using "
                        "discovery tools (list_tasks, list_projects, list_contexts list_completed_tasks) "
                        "to gather all necessary context and verify no duplicates exist."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "The task description (required)",
                            },
                            "priority": {
                                "type": "string",
                                "description": "Optional priority level (A-Z, where A is highest)",
                            },
                            "project": {
                                "type": "string",
                                "description": "Optional project name (without the + symbol)",
                            },
                            "context": {
                                "type": "string",
                                "description": "Optional context name (without the @ symbol)",
                            },
                            "due": {
                                "type": "string",
                                "description": "Optional due date in YYYY-MM-DD format",
                            },
                        },
                        "required": ["description"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "complete_task",
                    "description": (
                        "Mark a specific task as complete by its line number. IMPORTANT: "
                        "Before completing, use list_completed_tasks() to check if it's already done. "
                        "If multiple tasks match the description, ask the user to clarify which one. "
                        "STRATEGIC CONTEXT: This is a modification tool - call this LAST after using "
                        "discovery tools (list_tasks, list_completed_tasks) "
                        "to verify the task exists and hasn't already been completed."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_number": {
                                "type": "integer",
                                "description": "The line number of the task to complete (required)",
                            }
                        },
                        "required": ["task_number"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "replace_task",
                    "description": (
                        "Replace the entire content of a task. IMPORTANT: Use list_tasks() first "
                        "to find the correct task number if user doesn't specify it. "
                        "If multiple tasks match the description, ask for clarification."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_number": {
                                "type": "integer",
                                "description": "The line number of the task to replace (required)",
                            },
                            "new_description": {
                                "type": "string",
                                "description": "The new task description (required)",
                            },
                        },
                        "required": ["task_number", "new_description"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "append_to_task",
                    "description": (
                        "Add text to the end of an existing task. Use this when user wants "
                        "to add additional information to a task without replacing it entirely."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_number": {
                                "type": "integer",
                                "description": "The line number of the task to modify (required)",
                            },
                            "text": {
                                "type": "string",
                                "description": "The text to append to the task (required)",
                            },
                        },
                        "required": ["task_number", "text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "prepend_to_task",
                    "description": (
                        "Add text to the beginning of an existing task. Use this when user "
                        "wants to add a prefix or modifier to a task."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_number": {
                                "type": "integer",
                                "description": "The line number of the task to modify (required)",
                            },
                            "text": {
                                "type": "string",
                                "description": "The text to prepend to the task (required)",
                            },
                        },
                        "required": ["task_number", "text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_task",
                    "description": (
                        "Delete an entire task or remove a specific term from a task. "
                        "IMPORTANT: Use list_tasks() first to find the correct task number "
                        "if user doesn't specify it."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_number": {
                                "type": "integer",
                                "description": "The line number of the task to delete (required)",
                            },
                            "term": {
                                "type": "string",
                                "description": (
                                    "Optional specific term to remove from the task "
                                    "(if not provided, deletes entire task)"
                                ),
                            },
                        },
                        "required": ["task_number"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "set_priority",
                    "description": (
                        "Set or change the priority of a task (A-Z, where A is highest). "
                        "IMPORTANT: Use list_tasks() first to find the correct task number "
                        "if user doesn't specify it."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_number": {
                                "type": "integer",
                                "description": "The line number of the task to prioritize (required)",
                            },
                            "priority": {
                                "type": "string",
                                "description": "Priority level (A-Z, where A is highest) (required)",
                            },
                        },
                        "required": ["task_number", "priority"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "remove_priority",
                    "description": (
                        "Remove the priority from a task. IMPORTANT: Use list_tasks() first "
                        "to find the correct task number if user doesn't specify it."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_number": {
                                "type": "integer",
                                "description": "The line number of the task to deprioritize (required)",
                            }
                        },
                        "required": ["task_number"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_overview",
                    "description": (
                        "Show task statistics and summary. Use this when user asks for "
                        "an overview, summary, or statistics about their tasks."
                    ),
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "move_task",
                    "description": (
                        "Move a task from one file to another (e.g., from todo.txt to done.txt). "
                        "IMPORTANT: Use list_tasks() first to find the correct task number "
                        "if user doesn't specify it."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_number": {
                                "type": "integer",
                                "description": "The line number of the task to move (required)",
                            },
                            "destination": {
                                "type": "string",
                                "description": "The destination file name (e.g., 'done.txt') (required)",
                            },
                            "source": {
                                "type": "string",
                                "description": "Optional source file name (defaults to todo.txt)",
                            },
                        },
                        "required": ["task_number", "destination"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "archive_tasks",
                    "description": (
                        "Archive completed tasks by moving them from todo.txt to done.txt "
                        "and removing blank lines. Use this when user wants to clean up "
                        "their todo list or archive completed tasks."
                    ),
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "deduplicate_tasks",
                    "description": (
                        "Remove duplicate tasks from todo.txt. Use this when user wants "
                        "to clean up duplicate entries or when you notice duplicate tasks "
                        "in the list."
                    ),
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
        ]

    def _format_tool_signature(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Format tool signature with parameters for logging."""
        if not arguments:
            return f"{tool_name}()"

        # Format parameters as key=value pairs
        param_parts = []
        for key, value in arguments.items():
            if isinstance(value, str):
                # Quote string values
                param_parts.append(f"{key}='{value}'")
            else:
                param_parts.append(f"{key}={value}")

        return f"{tool_name}({', '.join(param_parts)})"

    def execute_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call and return the result."""
        tool_name = tool_call["function"]["name"]
        arguments = tool_call["function"]["arguments"]
        tool_call_id = tool_call.get("id", "unknown")

        # Handle arguments that might be a string (JSON) or already a dict
        if isinstance(arguments, str):
            import json

            try:
                arguments = json.loads(arguments)
                if self.logger:
                    self.logger.debug(f"Parsed JSON arguments: {arguments}")
            except json.JSONDecodeError as e:
                if self.logger:
                    self.logger.warning(f"Failed to parse JSON arguments: {e}")
                arguments = {}

        # Format tool signature with parameters
        tool_signature = self._format_tool_signature(tool_name, arguments)

        # Log function name with signature at INFO level
        if self.logger:
            self.logger.info(f"Executing tool: {tool_signature} (ID: {tool_call_id})")

        # Log detailed command information at DEBUG level
        if self.logger:
            self.logger.debug(f"=== TOOL EXECUTION START ===")
            self.logger.debug(f"Tool: {tool_name}")
            self.logger.debug(f"Tool Call ID: {tool_call_id}")
            self.logger.debug(f"Arguments: {tool_call['function']['arguments']}")

        # Map tool names to todo_manager methods
        method_map: Dict[str, Callable[..., Any]] = {
            "list_projects": self.todo_manager.list_projects,
            "list_contexts": self.todo_manager.list_contexts,
            "list_tasks": self.todo_manager.list_tasks,
            "list_completed_tasks": self.todo_manager.list_completed_tasks,
            "add_task": self.todo_manager.add_task,
            "complete_task": self.todo_manager.complete_task,
            "replace_task": self.todo_manager.replace_task,
            "append_to_task": self.todo_manager.append_to_task,
            "prepend_to_task": self.todo_manager.prepend_to_task,
            "delete_task": self.todo_manager.delete_task,
            "set_priority": self.todo_manager.set_priority,
            "remove_priority": self.todo_manager.remove_priority,
            "get_overview": self.todo_manager.get_overview,
            "move_task": self.todo_manager.move_task,
            "archive_tasks": self.todo_manager.archive_tasks,
            "deduplicate_tasks": self.todo_manager.deduplicate_tasks,
        }

        if tool_name not in method_map:
            error_msg = f"Unknown tool: {tool_name}"
            if self.logger:
                self.logger.error(error_msg)
            return {
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "output": f"ERROR: {error_msg}",
                "error": True,
                "error_type": "unknown_tool",
                "error_details": error_msg,
            }

        method = method_map[tool_name]

        # Log method call details
        if self.logger:
            self.logger.debug(f"Calling method: {tool_name}")

        try:
            result = method(**arguments)

            # Log successful output at DEBUG level
            if self.logger:
                self.logger.debug(f"=== TOOL EXECUTION SUCCESS ===")
                self.logger.debug(f"Tool: {tool_name}")
                self.logger.debug(f"Raw result: ====\n{result}\n====")

                # For list results, log the count
                if isinstance(result, list):
                    self.logger.debug(f"Result count: {len(result)}")
                # For string results, log the length
                elif isinstance(result, str):
                    self.logger.debug(f"Result length: {len(result)}")

            return {
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "output": result,
                "error": False,
            }

        except Exception as e:
            # Log error details
            if self.logger:
                self.logger.error(f"=== TOOL EXECUTION FAILED ===")
                self.logger.error(f"Tool: {tool_name}")
                self.logger.error(f"Error type: {type(e).__name__}")
                self.logger.error(f"Error message: {e!s}")
                self.logger.exception(f"Exception details for {tool_name}")

            # Return structured error information instead of raising
            error_type = type(e).__name__
            error_message = str(e)

            # Provide user-friendly error messages based on error type
            if "FileNotFoundError" in error_type or "todo.sh" in error_message.lower():
                user_message = f"Todo.sh command failed: {error_message}. Please ensure todo.sh is properly installed and configured."
            elif "IndexError" in error_type or (
                "task" in error_message.lower() and "not found" in error_message.lower()
            ):
                user_message = f"Task not found: {error_message}. The task may have been completed or deleted."
            elif "ValueError" in error_type:
                user_message = f"Invalid input: {error_message}. Please check the task format or parameters."
            elif "PermissionError" in error_type:
                user_message = f"Permission denied: {error_message}. Please check file permissions for todo.txt files."
            else:
                user_message = f"Operation failed: {error_message}"

            return {
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "output": f"ERROR: {user_message}",
                "error": True,
                "error_type": error_type,
                "error_details": error_message,
                "user_message": user_message,
            }
