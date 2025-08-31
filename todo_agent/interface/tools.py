"""
Tool definitions and schemas for LLM function calling.

AVAILABLE TOOLS:

Discovery Tools (Call FIRST):
- list_projects() - Get all available projects from todo.txt
- list_contexts() - Get all available contexts from todo.txt
- list_tasks(filter?) - List current tasks with optional filtering
- list_completed_tasks(filter?, project?, context?, text_search?, date_from?, date_to?) - List completed tasks with optional filtering

Task Management Tools:
- add_task(description, priority?, project?, context?, due?, recurring?) - Add new task to todo.txt
- complete_task(task_number) - Mark task as complete by line number
- replace_task(task_number, new_description) - Replace entire task content
- append_to_task(task_number, text) - Add text to end of existing task
- prepend_to_task(task_number, text) - Add text to beginning of existing task
- delete_task(task_number, term?) - Delete entire task or remove specific term

Priority Management Tools:
- set_priority(task_number, priority) - Set or change task priority (A-Z)
- remove_priority(task_number) - Remove priority from task
- set_due_date(task_number, due_date) - Set or update due date for a task by intelligently rewriting it (use empty string to remove due date)
- set_context(task_number, context) - Set or update context for a task by intelligently rewriting it (use empty string to remove context)
- set_project(task_number, projects) - Set or update projects for a task by intelligently rewriting it (handles array of projects with add/remove operations)

Utility Tools:
- get_overview() - Show task statistics and summary
- move_task(task_number, destination, source?) - Move task between files
- archive_tasks() - Archive completed tasks from todo.txt to done.txt
- get_calendar(month, year) - Get calendar for specific month and year
- parse_date(date_expression) - Convert natural language date expressions to YYYY-MM-DD format
"""

import subprocess
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
                        "4) You need to understand the current state before making changes, "
                        "5) User says they finished/completed a task and you need to find the matching task. "
                        "CRITICAL: ALWAYS use this before add_task() to check for similar existing tasks. "
                        "CRITICAL: ALWAYS use this when user mentions task completion to find the correct task number. "
                        "COMPLETION INTELLIGENCE: When searching for completion matches, if exactly one task clearly "
                        "matches the user's description, proceed to complete it immediately without asking for confirmation. "
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
                                    "use when you want to see only specific tasks or when searching for completion matches"
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
                        "AUTOMATIC INFERENCE: When project, context, or due date is not specified, automatically infer appropriate tags "
                        "and due dates based on the task content, natural language expressions, task nature, calendar context, and existing patterns. "
                        "DUE DATE INFERENCE: Use parse_date() tool to convert any temporal expressions to YYYY-MM-DD format. "
                        "Extract temporal expressions and use common sense to infer appropriate due dates based on task type, "
                        "work patterns, personal schedules, and existing task due date patterns. Only ask for clarification when genuinely ambiguous. "
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
                                "description": "Optional due date in YYYY-MM-DD format. Use parse_date() tool to convert natural language expressions like 'tomorrow', 'next week', 'by Friday' to YYYY-MM-DD format",
                            },
                            "recurring": {
                                "type": "string",
                                "description": "Optional recurring pattern in rec:frequency[:interval] format (e.g., 'rec:daily', 'rec:weekly:2', 'rec:monthly'). Use for tasks that repeat automatically.",
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
                        "When user says they finished/completed a task, FIRST use list_tasks() to find matching tasks, "
                        "then list_completed_tasks() to verify it's not already done. "
                        "COMPLETION LOGIC: If user's statement clearly matches exactly one task, complete it immediately. "
                        "If multiple tasks match, show numbered options and ask for clarification. "
                        "If the match is ambiguous, ask for confirmation. "
                        "STRATEGIC CONTEXT: This is a modification tool - call this LAST after using "
                        "discovery tools (list_tasks, list_completed_tasks) to verify the task exists and status."
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
                        "to add additional information to a task without replacing it entirely. "
                        "CRITICAL: DO NOT use this for adding project tags (+project) or context tags (@context) - "
                        "use set_project() or set_context() instead. "
                        "DO NOT use this for adding due dates - use set_due_date() instead. "
                        "This tool is for adding descriptive text, notes, or comments to tasks."
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
                    "name": "set_due_date",
                    "description": (
                        "Set or update the due date for a task by intelligently rewriting it. "
                        "This preserves all existing task components (priority, projects, contexts, etc.) "
                        "while updating or adding the due date. Use empty string to remove the due date. "
                        "IMPORTANT: Use list_tasks() first "
                        "to find the correct task number if user doesn't specify it. "
                        "Use parse_date() tool to convert natural language expressions like 'tomorrow', "
                        "'next week', 'by Friday' to YYYY-MM-DD format."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_number": {
                                "type": "integer",
                                "description": "The line number of the task to modify (required)",
                            },
                            "due_date": {
                                "type": "string",
                                "description": "Due date in YYYY-MM-DD format, or empty string to remove due date (required). Use parse_date() tool to convert natural language expressions.",
                            },
                        },
                        "required": ["task_number", "due_date"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "set_context",
                    "description": (
                        "Set or update the context for a task by intelligently rewriting it. "
                        "This preserves all existing task components (priority, projects, due date, etc.) "
                        "while updating or adding the context. Use empty string to remove the context. "
                        "PREFERRED METHOD: Use this instead of append_to_task() when adding context tags (@context). "
                        "This tool properly manages context organization and prevents formatting issues. "
                        "IMPORTANT: Use list_tasks() first "
                        "to find the correct task number if user doesn't specify it."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_number": {
                                "type": "integer",
                                "description": "The line number of the task to modify (required)",
                            },
                            "context": {
                                "type": "string",
                                "description": "Context to set for the task (required). Use empty string to remove context.",
                            },
                        },
                        "required": ["task_number", "context"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "set_project",
                    "description": (
                        "Set or update projects for a task by intelligently rewriting it. "
                        "This preserves all existing task components and manages projects intelligently. "
                        "Supports multiple projects, prevents duplicates, and groups them together. "
                        "Empty array or empty strings are NOOPs (no changes). "
                        "Use '-project' syntax to remove specific projects. "
                        "PREFERRED METHOD: Use this instead of append_to_task() when adding project tags (+project). "
                        "This tool properly manages project organization and prevents formatting issues. "
                        "IMPORTANT: Use list_tasks() first "
                        "to find the correct task number if user doesn't specify it. "
                        "Project names should be provided without the + symbol (e.g., 'work' not '+work')."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_number": {
                                "type": "integer",
                                "description": "The line number of the task to modify (required)",
                            },
                            "projects": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Array of project operations. Each item can be: project name (add), '-project' (remove), or empty string (remove all) (required).",
                            },
                        },
                        "required": ["task_number", "projects"],
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
                    "name": "parse_date",
                    "description": (
                        "Convert natural language date expressions to YYYY-MM-DD format. "
                        "Use this when: "
                        "1) User mentions weekdays like 'due on Monday', 'by Friday', 'next Tuesday', "
                        "2) User uses relative dates like 'tomorrow', 'next week', 'in 3 days', "
                        "3) User says 'this Monday' vs 'next Monday' and you need the exact date, "
                        "4) You need to convert any temporal expression to a specific calendar date. "
                        "This tool handles all date parsing to ensure accuracy and consistency. "
                        "CRITICAL: Use this tool whenever you need to convert any date expression to YYYY-MM-DD format."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date_expression": {
                                "type": "string",
                                "description": "The natural language date expression to parse (e.g., 'next Monday', 'tomorrow', 'by Friday', 'in 3 days')",
                            },
                        },
                        "required": ["date_expression"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_calendar",
                    "description": (
                        "Get a calendar for a specific month and year using the system 'cal' command. "
                        "Use this when: "
                        "1) User asks to see a calendar for a specific month/year, "
                        "2) User wants to plan tasks around specific dates, "
                        "3) User needs to see what day of the week a date falls on, "
                        "4) User wants to visualize the current month or upcoming months. "
                        "The calendar will show the month in a traditional calendar format with days of the week. "
                        "IMPORTANT: When displaying the calendar output, present it directly without wrapping in backticks or code blocks. "
                        "The calendar should be displayed as plain text in the conversation."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "month": {
                                "type": "integer",
                                "description": "Month number (1-12, where 1=January, 12=December)",
                                "minimum": 1,
                                "maximum": 12,
                            },
                            "year": {
                                "type": "integer",
                                "description": "Year (4-digit format, e.g., 2025)",
                                "minimum": 1900,
                                "maximum": 2100,
                            },
                        },
                        "required": ["month", "year"],
                    },
                },
            },
        ]

    def _get_calendar(self, month: int, year: int) -> str:
        """
        Get a calendar for the specified month and year using the system 'cal' command.

        Args:
            month: Month number (1-12)
            year: Year (4-digit format)

        Returns:
            Calendar output as a string
        """
        try:
            # Use the cal command with specific month and year
            result = subprocess.run(
                ["cal", str(month), str(year)],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            # Fallback to Python calendar module
            import calendar

            return calendar.month(year, month).strip()

    def _parse_date(self, date_expression: str) -> str:
        """
        Parse natural language date expressions to YYYY-MM-DD format.

        Args:
            date_expression: Natural language date expression

        Returns:
            Date in YYYY-MM-DD format
        """
        try:
            # Use the date command to parse natural language expressions
            result = subprocess.run(
                ["date", "-d", date_expression, "+%Y-%m-%d"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            # Fallback to Python date parsing
            import re
            from datetime import datetime, timedelta

            today = datetime.now()
            date_expr = date_expression.lower().strip()

            # Handle "next [weekday]" patterns
            next_match = re.match(
                r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
                date_expr,
            )
            if next_match:
                weekday_name = next_match.group(1)
                weekday_map = {
                    "monday": 0,
                    "tuesday": 1,
                    "wednesday": 2,
                    "thursday": 3,
                    "friday": 4,
                    "saturday": 5,
                    "sunday": 6,
                }
                target_weekday = weekday_map[weekday_name]
                days_ahead = target_weekday - today.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
                return target_date.strftime("%Y-%m-%d")

            # Handle "this [weekday]" patterns
            this_match = re.match(
                r"this\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
                date_expr,
            )
            if this_match:
                weekday_name = this_match.group(1)
                weekday_map = {
                    "monday": 0,
                    "tuesday": 1,
                    "wednesday": 2,
                    "thursday": 3,
                    "friday": 4,
                    "saturday": 5,
                    "sunday": 6,
                }
                target_weekday = weekday_map[weekday_name]
                days_ahead = target_weekday - today.weekday()
                if days_ahead < 0:  # Target day already happened this week
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
                return target_date.strftime("%Y-%m-%d")

            # Handle "tomorrow"
            if date_expr == "tomorrow":
                return (today + timedelta(days=1)).strftime("%Y-%m-%d")

            # Handle "in X days"
            days_match = re.match(r"in\s+(\d+)\s+days?", date_expr)
            if days_match:
                days = int(days_match.group(1))
                return (today + timedelta(days=days)).strftime("%Y-%m-%d")

            # Handle "by [weekday]" - same as "next [weekday]"
            by_match = re.match(
                r"by\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
                date_expr,
            )
            if by_match:
                weekday_name = by_match.group(1)
                weekday_map = {
                    "monday": 0,
                    "tuesday": 1,
                    "wednesday": 2,
                    "thursday": 3,
                    "friday": 4,
                    "saturday": 5,
                    "sunday": 6,
                }
                target_weekday = weekday_map[weekday_name]
                days_ahead = target_weekday - today.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
                return target_date.strftime("%Y-%m-%d")

            # If we can't parse it, return today's date as fallback
            return today.strftime("%Y-%m-%d")

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
            "set_due_date": self.todo_manager.set_due_date,
            "set_context": self.todo_manager.set_context,
            "set_project": self.todo_manager.set_project,
            "get_overview": self.todo_manager.get_overview,
            "move_task": self.todo_manager.move_task,
            "archive_tasks": self.todo_manager.archive_tasks,
            "parse_date": self._parse_date,
            "get_calendar": self._get_calendar,
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
