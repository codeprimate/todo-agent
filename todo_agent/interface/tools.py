"""
Tool definitions and schemas for LLM function calling.

AVAILABLE TOOLS:

Discovery Tools (Call FIRST):
- list_projects() - Get all available projects from todo.txt
- list_contexts() - Get all available contexts from todo.txt
- list_tasks() - List all current tasks from todo.txt
- list_completed_tasks() - List all completed tasks from done.txt

Task Management Tools:
- add_task(description, priority?, project?, context?, due?, duration?) - Add new task to todo.txt
- complete_task(task_number) - Mark task as complete by line number
- replace_task(task_number, new_description) - Replace entire task content
- append_to_task(task_number, text) - Add text to end of existing task
- prepend_to_task(task_number, text) - Add text to beginning of existing task
- delete_task(task_number, term?) - Delete entire task or remove specific term
- create_completed_task(description, completion_date?, project?, context?) - Create task and immediately mark as completed

Priority Management Tools:
- set_priority(task_number, priority) - Set or change task priority (A-Z)
- remove_priority(task_number) - Remove priority from task

Task Modification Tools:
- set_due_date(task_number, due_date) - Set or update due date for a task by intelligently rewriting it (use empty string to remove due date)
- set_context(task_number, context) - Set or update context for a task by intelligently rewriting it (use empty string to remove context)
- set_project(task_number, projects) - Set or update projects for a task by intelligently rewriting it (handles array of projects with add/remove operations)

Utility Tools:
- move_task(task_number, destination, source?) - Move task between files
- archive_tasks() - Archive completed tasks from todo.txt to done.txt
- get_calendar(month, year) - Get calendar for specific month and year
- parse_date(date_expression) - Convert natural language date expressions to YYYY-MM-DD format

Mathematical Reasoning Tools:
- solve_math(expression, operation?) - Perform mathematical calculations and symbolic reasoning using SymPy
"""

import subprocess
from typing import Any, Callable, Dict, List, Optional

try:
    from todo_agent.core.todo_manager import TodoManager
    from todo_agent.infrastructure.logger import Logger
    from todo_agent.infrastructure.math_solver import MathSolver
except ImportError:
    from core.todo_manager import TodoManager  # type: ignore[no-redef]
    from infrastructure.logger import Logger  # type: ignore[no-redef]
    from infrastructure.math_solver import MathSolver  # type: ignore[no-redef]


class ToolCallHandler:
    """Handles tool execution and orchestration."""

    def __init__(self, todo_manager: TodoManager, logger: Optional[Logger] = None):
        self.todo_manager = todo_manager
        self.logger = logger
        self.math_solver = MathSolver()
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
                "progress_description": "📁 Discovering available projects...",
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
                "progress_description": "📍 Finding available contexts...",
            },
            {
                "type": "function",
                "function": {
                    "name": "list_tasks",
                    "description": (
                        "List all current tasks from todo.txt. Use this when: "
                        "1) User wants to see their tasks, "
                        "2) You need to check for potential duplicates before adding new tasks, "
                        "3) You need to understand the current state before making changes, "
                        "4) User says they finished/completed a task and you need to find the matching task. "
                        "CRITICAL: ALWAYS use this before add_task() to check for similar existing tasks. "
                        "CRITICAL: ALWAYS use this when user mentions task completion to find the correct task number. "
                        "STRATEGIC CONTEXT: This is the primary discovery tool - call this FIRST when you need to "
                        "understand existing tasks before making any modifications. Always get the complete task list "
                        "for full context rather than trying to filter."
                    ),
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
                "progress_description": "📋 Scanning your task list...",
            },
            {
                "type": "function",
                "function": {
                    "name": "list_completed_tasks",
                    "description": (
                        "List all completed tasks from done.txt. Use this when: "
                        "1) User tries to complete a task that might already be done, "
                        "2) User asks about completed tasks, "
                        "3) You need to verify task status before taking action, "
                        "4) User wants to see their task completion history. "
                        "STRATEGIC CONTEXT: Call this BEFORE complete_task() to verify the task hasn't already "
                        "been completed, preventing duplicate completion attempts. "
                        "Always get the complete completed task list for full historical context rather than "
                        "trying to filter by specific criteria."
                    ),
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
                "progress_description": "✅ Checking completion history...",
            },
            {
                "type": "function",
                "function": {
                    "name": "add_task",
                    "description": (
                        "Add a NEW task to todo.txt with intelligent automatic inference capabilities. "
                        "USE CASE: Call this when user wants to create a NEW task, not when they want to complete, modify, or work with existing tasks. "
                        "CRITICAL: Before adding ANY task, you MUST use list_tasks() and list_completed_tasks() to check for potential duplicates. "
                        "Look for tasks with similar descriptions, keywords, or intent. If you find tasks that seem to be DUPLICATIVE, "
                        "ask the user if they want to add a new task or modify an existing one. "
                        "INTELLIGENT INFERENCE ENGINE: This tool automatically infers missing elements to create complete, actionable tasks: "
                        "PROJECT INFERENCE: Automatically detect and add appropriate +project tags based on task keywords, semantic patterns, and existing project usage. "
                        "CONTEXT INFERENCE: Automatically infer @context tags from task nature, location requirements, and historical context patterns. "
                        "DUE DATE INFERENCE: Use parse_date() tool to convert natural language expressions ('tomorrow', 'next week', 'by Friday') to YYYY-MM-DD format. "
                        "Apply strategic timing based on task type, work patterns, personal schedules, and existing due date patterns. "
                        "DURATION INFERENCE: Automatically estimate appropriate duration: tags based on task complexity, context, and historical patterns. "
                        "PRIORITY INFERENCE: Suggest appropriate priority levels (A-Z) based on urgency, importance, and existing priority patterns. "
                        "STRATEGIC CONTEXT: This is a CREATION tool - call this LAST after using "
                        "discovery tools (list_tasks, list_projects, list_contexts, list_completed_tasks) "
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
                            "duration": {
                                "type": "string",
                                "description": "Optional duration estimate in format: minutes (e.g., '30m'), hours (e.g., '2h'), or days (e.g., '1d'). Use for time planning and task prioritization.",
                            },
                        },
                        "required": ["description"],
                    },
                },
                "progress_description": "✨ Creating new task: {description}...",
            },
            {
                "type": "function",
                "function": {
                    "name": "complete_task",
                    "description": (
                        "Mark an existing task as complete by its line number. "
                        "USE CASE: Only call this when user explicitly states they have finished/completed a task. "
                        "WORKFLOW: 1) Use list_tasks() to find the task to complete, 2) Use list_completed_tasks() to verify it's not already done, 3) Call complete_task() with the task number. "
                        "NOT FOR: Adding new tasks, modifying task content, or any other task operations. "
                        "This tool ONLY marks existing tasks as complete."
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
                "progress_description": "🎯 Marking task #{task_number} as complete...",
            },
            {
                "type": "function",
                "function": {
                    "name": "replace_task",
                    "description": (
                        "Replace the entire content of an EXISTING task. "
                        "USE CASE: Call this when user wants to completely rewrite an existing task description. "
                        "NOT FOR: Creating new tasks, completing tasks, or adding to tasks. "
                        "Use list_tasks() first to find the correct task number if user doesn't specify it. "
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
                "progress_description": "✏️ Updating task #{task_number} with new description...",
            },
            {
                "type": "function",
                "function": {
                    "name": "append_to_task",
                    "description": (
                        "Add text to the end of an EXISTING task. "
                        "USE CASE: Call this when user wants to add additional descriptive text, notes, or comments to an existing task. "
                        "NOT FOR: Creating new tasks, completing tasks, or adding project/context/due date tags. "
                        "CRITICAL: DO NOT use this for adding project tags (+project) or context tags (@context) - "
                        "use set_project() or set_context() instead. "
                        "DO NOT use this for adding due dates - use set_due_date() instead. "
                        "This tool is ONLY for adding descriptive text, notes, or comments to existing tasks."
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
                                "description": "Text to add to the end of the task (required)",
                            },
                        },
                        "required": ["task_number", "text"],
                    },
                },
                "progress_description": "📝 Adding notes to task #{task_number}...",
            },
            {
                "type": "function",
                "function": {
                    "name": "prepend_to_task",
                    "description": (
                        "Add text to the beginning of an EXISTING task. "
                        "USE CASE: Call this when user wants to add a prefix or modifier to an existing task. "
                        "NOT FOR: Creating new tasks, completing tasks, or adding project/context/due date tags. "
                        "This tool is ONLY for modifying existing tasks by adding text at the beginning."
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
                "progress_description": "📝 Adding prefix to task #{task_number}...",
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_task",
                    "description": (
                        "Delete an entire EXISTING task or remove a specific term from an EXISTING task. "
                        "USE CASE: Call this when user wants to delete a task completely or remove specific text from an existing task. "
                        "NOT FOR: Creating new tasks, completing tasks, or any other task operations. "
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
                "progress_description": "🗑️ Deleting task #{task_number}...",
            },
            {
                "type": "function",
                "function": {
                    "name": "set_priority",
                    "description": (
                        "Set or change the priority of an EXISTING task (A-Z, where A is highest). "
                        "USE CASE: Call this when user wants to add, change, or remove priority on an existing task. "
                        "NOT FOR: Creating new tasks, completing tasks, or any other task operations. "
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
                "progress_description": "🏷️ Setting priority {priority} for task #{task_number}...",
            },
            {
                "type": "function",
                "function": {
                    "name": "remove_priority",
                    "description": (
                        "Remove the priority from an EXISTING task. "
                        "USE CASE: Call this when user wants to remove priority from an existing task. "
                        "NOT FOR: Creating new tasks, completing tasks, or any other task operations. "
                        "IMPORTANT: Use list_tasks() first "
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
                "progress_description": "🏷️ Removing priority from task #{task_number}...",
            },
            {
                "type": "function",
                "function": {
                    "name": "set_due_date",
                    "description": (
                        "Set or update the due date for an EXISTING task by intelligently rewriting it. "
                        "USE CASE: Call this when user wants to add, change, or remove a due date on an existing task. "
                        "NOT FOR: Creating new tasks, completing tasks, or any other task operations. "
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
                "progress_description": "📅 Setting due date {due_date} for task #{task_number}...",
            },
            {
                "type": "function",
                "function": {
                    "name": "set_context",
                    "description": (
                        "Set or update the context for an EXISTING task by intelligently rewriting it. "
                        "USE CASE: Call this when user wants to add, change, or remove a context tag on an existing task. "
                        "NOT FOR: Creating new tasks, completing tasks, or any other task operations. "
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
                "progress_description": "📍 Setting context {context} for task #{task_number}...",
            },
            {
                "type": "function",
                "function": {
                    "name": "set_project",
                    "description": (
                        "Set or update projects for an EXISTING task by intelligently rewriting it. "
                        "USE CASE: Call this when user wants to add, change, or remove project tags on an existing task. "
                        "NOT FOR: Creating new tasks, completing tasks, or any other task operations. "
                        "This preserves all existing task components and manages projects intelligently. "
                        "Empty array or empty strings are NOOPs (no changes). "
                        "Use '-project' syntax to remove specific projects. with `projects=['-projectname']`"
                        "PREFERRED METHOD: Use this instead of append_to_task() when adding project tags (+projectname). "
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
                "progress_description": "🏷️ Setting project tags for task #{task_number}...",
            },
            {
                "type": "function",
                "function": {
                    "name": "move_task",
                    "description": (
                        "Move an EXISTING task from one file to another (e.g., from todo.txt to done.txt). "
                        "USE CASE: Call this when user wants to move a task between different todo files. "
                        "NOT FOR: Creating new tasks, completing tasks, or any other task operations. "
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
                "progress_description": "📦 Moving task #{task_number} to {destination}...",
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
                "progress_description": "📦 Archiving completed tasks...",
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
                "progress_description": "📅 Converting date expression '{date_expression}'...",
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
                "progress_description": "📅 Generating calendar for {month}/{year}...",
            },
            {
                "type": "function",
                "function": {
                    "name": "create_completed_task",
                    "description": (
                        "Create a task and immediately mark it as completed. "
                        "USE CASE: WHEN NO MATCH IS FOUND! Call this when user says they completed something on a specific date (e.g., 'I did the laundry today', 'I finished the report yesterday', 'I cleaned the garage last week') "
                        "and you have already researched existing tasks to determine no match exists. "
                        "WORKFLOW: 1) Use list_tasks() to search for existing tasks, "
                        "2) Use list_completed_tasks() to verify it's not already done, "
                        "3) If a match is found, use complete_task() to mark it complete, "
                        "4) If no match found, call this tool to create and complete the task in one operation. "
                        "STRATEGIC CONTEXT: This is a convenience tool for the common pattern of 'I did X on [date]' - "
                        "when no task match is found, it creates a task with the specified completion date and immediately marks it complete. "
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "The task description of what was completed (required)",
                            },
                            "completion_date": {
                                "type": "string",
                                "description": "Optional completion date in YYYY-MM-DD format (defaults to today)",
                            },
                            "project": {
                                "type": "string",
                                "description": "Optional project name (without the + symbol) for new task creation",
                            },
                            "context": {
                                "type": "string",
                                "description": "Optional context name (without the @ symbol) for new task creation",
                            },
                        },
                        "required": ["description"],
                    },
                },
                "progress_description": "✅ Creating completed task: {description}...",
            },
            {
                "type": "function",
                "function": {
                    "name": "restore_completed_task",
                    "description": (
                        "Restore a completed task from done.txt back to todo.txt, making it active again. "
                        "USE CASE: Call this when user wants to reactivate a previously completed task. "
                        "WORKFLOW: 1) Use list_completed_tasks() to find the completed task to restore, "
                        "2) Call restore_completed_task() with the task number from done.txt. "
                        "NOT FOR: Creating new tasks, completing tasks, or any other task operations. "
                        "This tool ONLY restores existing completed tasks to active status. "
                        "IMPORTANT: Use list_completed_tasks() first to find the correct task number "
                        "if user doesn't specify it."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_number": {
                                "type": "integer",
                                "description": "The line number of the completed task in done.txt to restore (required)",
                            }
                        },
                        "required": ["task_number"],
                    },
                },
                "progress_description": "🔄 Restoring completed task #{task_number}...",
            },
            {
                "type": "function",
                "function": {
                    "name": "solve_math",
                    "description": (
                        "Perform mathematical calculations and symbolic reasoning using SymPy. "
                        "USE CASE: Call this when user asks for mathematical calculations, equation solving, "
                        "algebraic simplification, calculus operations, or any mathematical reasoning. "
                        "CAPABILITIES: "
                        "• Basic arithmetic: '2 + 3 * 4', 'sqrt(16)', '2^3' "
                        "• Algebraic simplification: 'x^2 + 2*x + 1', 'sin(x)^2 + cos(x)^2' "
                        "• Equation solving: 'x^2 - 4 = 0', '2*x + 3 = 7' "
                        "• Calculus: 'derivative of x^2', 'integral of sin(x)', 'limit of 1/x as x approaches 0' "
                        "• Statistics: 'normal distribution probability', 'mean of [1,2,3,4,5]' "
                        "• Units and constants: 'convert 100 km to miles', 'speed of light in m/s' "
                        "The tool automatically detects the type of mathematical operation needed. "
                        "For complex expressions, provide the mathematical expression as a string. "
                        "The operation parameter is optional and can specify: 'simplify', 'solve', 'integrate', 'differentiate', 'evaluate', 'stats'."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "The mathematical expression to evaluate or manipulate (required)",
                            },
                            "operation": {
                                "type": "string",
                                "description": "Optional operation type: 'simplify', 'solve', 'integrate', 'differentiate', 'evaluate', 'matrix', 'stats' (auto-detected if not specified)",
                            },
                        },
                        "required": ["expression"],
                    },
                },
                "progress_description": "🧮 Solving mathematical expression: {expression}...",
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

    def _solve_math(self, expression: str, operation: Optional[str] = None) -> str:
        """
        Perform mathematical calculations and symbolic reasoning using SymPy.

        Args:
            expression: The mathematical expression to evaluate or manipulate
            operation: Optional operation type (auto-detected if not specified)

        Returns:
            The result of the mathematical operation as a string
        """
        return self.math_solver.solve_math(expression, operation)

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
        # Validate tool call structure
        if not isinstance(tool_call, dict):
            return {  # type: ignore[unreachable]
                "tool_call_id": "unknown",
                "name": "unknown",
                "output": "ERROR: Invalid tool call format",
                "error": True,
                "error_type": "malformed_tool_call",
                "error_details": "Tool call is not a dictionary",
                "user_message": "I received a malformed request. Please try again, or type 'clear' to reset our conversation.",
            }

        if "function" not in tool_call:
            return {
                "tool_call_id": tool_call.get("id", "unknown"),
                "name": "unknown",
                "output": "ERROR: Tool call missing function definition",
                "error": True,
                "error_type": "malformed_tool_call",
                "error_details": "Tool call missing function field",
                "user_message": "I received a malformed request. Please try again, or type 'clear' to reset our conversation.",
            }

        function = tool_call["function"]
        if not isinstance(function, dict):
            return {
                "tool_call_id": tool_call.get("id", "unknown"),
                "name": "unknown",
                "output": "ERROR: Function definition is not a dictionary",
                "error": True,
                "error_type": "malformed_tool_call",
                "error_details": "Function field is not a dictionary",
                "user_message": "I received a malformed request. Please try again, or type 'clear' to reset our conversation.",
            }

        tool_name = function.get("name")
        if not tool_name:
            return {
                "tool_call_id": tool_call.get("id", "unknown"),
                "name": "unknown",
                "output": "ERROR: Tool call missing function name",
                "error": True,
                "error_type": "malformed_tool_call",
                "error_details": "Function missing name field",
                "user_message": "I received a malformed request. Please try again, or type 'clear' to reset our conversation.",
            }

        arguments = function.get("arguments", {})
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
            "move_task": self.todo_manager.move_task,
            "archive_tasks": self.todo_manager.archive_tasks,
            "parse_date": self._parse_date,
            "get_calendar": self._get_calendar,
            "create_completed_task": self.todo_manager.create_completed_task,
            "restore_completed_task": self.todo_manager.restore_completed_task,
            "solve_math": self._solve_math,
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

        # Filter arguments to only include those accepted by the method
        import inspect

        try:
            sig = inspect.signature(method)
            valid_params = set(sig.parameters.keys())
            filtered_arguments = {
                k: v for k, v in arguments.items() if k in valid_params
            }

            if self.logger and filtered_arguments != arguments:
                self.logger.debug(
                    f"Filtered arguments from {arguments} to {filtered_arguments}"
                )
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to filter arguments for {tool_name}: {e}")
            filtered_arguments = arguments

        # Log method call details
        if self.logger:
            self.logger.debug(f"Calling method: {tool_name}")

        try:
            result = method(**filtered_arguments)

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
