"""
Todo.sh operations orchestration and business logic.
"""

from datetime import datetime
from typing import Any, Optional


class TodoManager:
    """Orchestrates todo.sh operations with business logic."""

    def __init__(self, todo_shell: Any) -> None:
        self.todo_shell = todo_shell

    def add_task(
        self,
        description: str,
        priority: Optional[str] = None,
        project: Optional[str] = None,
        context: Optional[str] = None,
        due: Optional[str] = None,
    ) -> str:
        """Add new task with explicit project/context parameters."""
        # Validate and sanitize inputs
        if priority and not (
            len(priority) == 1 and priority.isalpha() and priority.isupper()
        ):
            raise ValueError(
                f"Invalid priority '{priority}'. Must be a single uppercase letter (A-Z)."
            )

        if project:
            # Remove any existing + symbols to prevent duplication
            project = project.strip().lstrip("+")
            if not project:
                raise ValueError(
                    "Project name cannot be empty after removing + symbol."
                )

        if context:
            # Remove any existing @ symbols to prevent duplication
            context = context.strip().lstrip("@")
            if not context:
                raise ValueError(
                    "Context name cannot be empty after removing @ symbol."
                )

        if due:
            # Basic date format validation
            try:
                datetime.strptime(due, "%Y-%m-%d")
            except ValueError:
                raise ValueError(
                    f"Invalid due date format '{due}'. Must be YYYY-MM-DD."
                )

        # Build the full task description with priority, project, and context
        full_description = description

        if priority:
            full_description = f"({priority}) {full_description}"

        if project:
            full_description = f"{full_description} +{project}"

        if context:
            full_description = f"{full_description} @{context}"

        if due:
            full_description = f"{full_description} due:{due}"

        self.todo_shell.add(full_description)
        return f"Added task: {full_description}"

    def list_tasks(self, filter: Optional[str] = None) -> str:
        """List tasks with optional filtering."""
        result = self.todo_shell.list_tasks(filter)
        if not result.strip():
            return "No tasks found."

        # Return the raw todo.txt format for the LLM to format conversationally
        # The LLM will convert this into natural language in its response
        return result

    def complete_task(self, task_number: int) -> str:
        """Mark task complete by line number."""
        result = self.todo_shell.complete(task_number)
        return f"Completed task {task_number}: {result}"

    def get_overview(self, **kwargs: Any) -> str:
        """Show current task statistics."""
        tasks = self.todo_shell.list_tasks()
        completed = self.todo_shell.list_completed()

        task_count = (
            len([line for line in tasks.split("\n") if line.strip()])
            if tasks.strip()
            else 0
        )
        completed_count = (
            len([line for line in completed.split("\n") if line.strip()])
            if completed.strip()
            else 0
        )

        return f"Task Overview:\n- Active tasks: {task_count}\n- Completed tasks: {completed_count}"

    def replace_task(self, task_number: int, new_description: str) -> str:
        """Replace entire task content."""
        result = self.todo_shell.replace(task_number, new_description)
        return f"Replaced task {task_number}: {result}"

    def append_to_task(self, task_number: int, text: str) -> str:
        """Add text to end of existing task."""
        result = self.todo_shell.append(task_number, text)
        return f"Appended to task {task_number}: {result}"

    def prepend_to_task(self, task_number: int, text: str) -> str:
        """Add text to beginning of existing task."""
        result = self.todo_shell.prepend(task_number, text)
        return f"Prepended to task {task_number}: {result}"

    def delete_task(self, task_number: int, term: Optional[str] = None) -> str:
        """Delete entire task or specific term from task."""
        result = self.todo_shell.delete(task_number, term)
        if term:
            return f"Removed '{term}' from task {task_number}: {result}"
        else:
            return f"Deleted task {task_number}: {result}"

    def set_priority(self, task_number: int, priority: str) -> str:
        """Set or change task priority (A-Z)."""
        result = self.todo_shell.set_priority(task_number, priority)
        return f"Set priority {priority} for task {task_number}: {result}"

    def remove_priority(self, task_number: int) -> str:
        """Remove priority from task."""
        result = self.todo_shell.remove_priority(task_number)
        return f"Removed priority from task {task_number}: {result}"

    def list_projects(self, **kwargs: Any) -> str:
        """List all available projects in todo.txt."""
        result = self.todo_shell.list_projects()
        if not result.strip():
            return "No projects found."
        return result

    def list_contexts(self, **kwargs: Any) -> str:
        """List all available contexts in todo.txt."""
        result = self.todo_shell.list_contexts()
        if not result.strip():
            return "No contexts found."
        return result

    def list_completed_tasks(
        self,
        filter: Optional[str] = None,
        project: Optional[str] = None,
        context: Optional[str] = None,
        text_search: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """List completed tasks with optional filtering.

        Args:
            filter: Raw filter string (e.g., '+work', '@office')
            project: Filter by project (without + symbol)
            context: Filter by context (without @ symbol)
            text_search: Search for text in task descriptions
            date_from: Filter tasks completed from this date (YYYY-MM-DD)
            date_to: Filter tasks completed until this date (YYYY-MM-DD)
        """
        # Build filter string from individual parameters
        filter_parts = []

        if filter:
            filter_parts.append(filter)

        if project:
            filter_parts.append(f"+{project}")

        if context:
            filter_parts.append(f"@{context}")

        if text_search:
            filter_parts.append(text_search)

        # Handle date filtering - todo.sh supports direct date pattern matching
        # LIMITATIONS: Due to todo.sh constraints, complex date ranges are not supported.
        # The filtering behavior is:
        # - date_from + date_to: Uses year-month pattern (YYYY-MM) from date_from for month-based filtering
        # - date_from only: Uses exact date pattern (YYYY-MM-DD) for precise date matching
        # - date_to only: Uses year-month pattern (YYYY-MM) from date_to for month-based filtering
        # - Complex ranges spanning multiple months are not supported by todo.sh
        if date_from and date_to:
            # For a date range, we'll use the year-month pattern from date_from
            # This will match all tasks in that month
            filter_parts.append(date_from[:7])  # YYYY-MM format
        elif date_from:
            # For single date, use the full date pattern
            filter_parts.append(date_from)
        elif date_to:
            # For end date only, we'll use the year-month pattern
            # This will match all tasks in that month
            filter_parts.append(date_to[:7])  # YYYY-MM format

        # Combine all filters
        combined_filter = " ".join(filter_parts) if filter_parts else None

        result = self.todo_shell.list_completed(combined_filter)
        if not result.strip():
            return "No completed tasks found matching the criteria."
        return result

    def move_task(
        self, task_number: int, destination: str, source: Optional[str] = None
    ) -> str:
        """Move task from source to destination file."""
        result = self.todo_shell.move(task_number, destination, source)
        return f"Moved task {task_number} to {destination}: {result}"

    def archive_tasks(self, **kwargs: Any) -> str:
        """Archive completed tasks."""
        result = self.todo_shell.archive()
        return f"Archived tasks: {result}"

    def deduplicate_tasks(self, **kwargs: Any) -> str:
        """Remove duplicate tasks."""
        result = self.todo_shell.deduplicate()
        return f"Deduplicated tasks: {result}"

    def get_current_datetime(self, **kwargs: Any) -> str:
        """Get the current date and time."""
        now = datetime.now()
        return f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')} ({now.strftime('%A, %B %d, %Y at %I:%M %p')})"
