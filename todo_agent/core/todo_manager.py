"""
Todo.sh operations orchestration and business logic.
"""

from datetime import datetime
from typing import Any, Optional


class TodoManager:
    """Orchestrates todo.sh operations with business logic."""

    def __init__(self, todo_shell: Any) -> None:
        self.todo_shell = todo_shell

    # ============================================================================
    # VALIDATION METHODS
    # ============================================================================

    def _normalize_empty_to_none(self, value: Optional[str]) -> Optional[str]:
        """Convert empty strings to None for consistent handling."""
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    def _validate_date_format(
        self, date_str: Optional[str], field_name: str = "date"
    ) -> None:
        """Validate date format (YYYY-MM-DD)."""
        if date_str is None or not date_str.strip():
            return
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"Invalid {field_name} format '{date_str}'. Must be YYYY-MM-DD."
            )

    def _validate_priority(self, priority: Optional[str]) -> None:
        """Validate priority format (single uppercase letter A-Z)."""
        if priority is None:
            return
        if not (len(priority) == 1 and priority.isalpha() and priority.isupper()):
            raise ValueError(
                f"Invalid priority '{priority}'. Must be a single uppercase letter (A-Z)."
            )

    def _validate_parent_number(self, parent_number: Optional[int]) -> None:
        """Validate parent task number."""
        if parent_number is not None and (
            not isinstance(parent_number, int) or parent_number <= 0
        ):
            raise ValueError(
                f"Invalid parent_number '{parent_number}'. Must be a positive integer."
            )

    def _validate_duration(self, duration: Optional[str]) -> None:
        """Validate duration format (e.g., '30m', '2h', '1d')."""
        if duration is None:
            return

        if not isinstance(duration, str) or not duration.strip():
            raise ValueError("Duration must be a non-empty string.")

        if not any(duration.endswith(unit) for unit in ["m", "h", "d"]):
            raise ValueError(
                f"Invalid duration format '{duration}'. Must end with m (minutes), h (hours), or d (days)."
            )

        value = duration[:-1]
        if not value:
            raise ValueError("Duration value cannot be empty.")

        try:
            numeric_value = float(value)
            if numeric_value <= 0:
                raise ValueError("Duration value must be positive.")
        except ValueError:
            raise ValueError(
                f"Invalid duration value '{value}'. Must be a positive number."
            )

    def _clean_project_name(self, project: Optional[str]) -> Optional[str]:
        """Clean and validate project name."""
        if project is None:
            return None
        if not project.strip():
            return None
        clean_project = project.strip().lstrip("+")
        if not clean_project:
            raise ValueError("Project name cannot be empty after removing + symbol.")
        return clean_project

    def _clean_context_name(self, context: Optional[str]) -> Optional[str]:
        """Clean and validate context name."""
        if context is None:
            return None
        if not context.strip():
            return ""  # Return empty string for empty input (used by set_context for removal)
        clean_context = context.strip().lstrip("@")
        if not clean_context:
            raise ValueError("Context name cannot be empty after removing @ symbol.")
        return clean_context

    # ============================================================================
    # TASK BUILDING AND UTILITY METHODS
    # ============================================================================

    def _build_task_description(
        self,
        description: str,
        priority: Optional[str] = None,
        project: Optional[str] = None,
        context: Optional[str] = None,
        due: Optional[str] = None,
        duration: Optional[str] = None,
        parent_number: Optional[int] = None,
    ) -> str:
        """Build full task description with all components."""
        full_description = description

        if priority:
            full_description = f"({priority}) {full_description}"

        if project:
            clean_project = self._clean_project_name(project)
            if clean_project:  # Only add if not None/empty after cleaning
                full_description = f"{full_description} +{clean_project}"

        if context:
            clean_context = self._clean_context_name(context)
            if clean_context:  # Only add if not None/empty after cleaning
                full_description = f"{full_description} @{clean_context}"

        if due:
            full_description = f"{full_description} due:{due}"

        if duration:
            full_description = f"{full_description} duration:{duration}"

        if parent_number:
            full_description = f"{full_description} parent:{parent_number}"

        return full_description

    def _format_task_operation_response(
        self, operation: str, task_number: int, result: str, additional_info: str = ""
    ) -> str:
        """Format consistent task operation response messages."""
        # Handle special cases for backward compatibility with tests
        if operation == "Set due date" and additional_info:
            return f"Set due date {additional_info} for task {task_number}: {result}"
        elif operation == "Set context" and additional_info:
            return f"Set context {additional_info} for task {task_number}: {result}"
        elif operation == "Set priority" and additional_info:
            return f"Set priority {additional_info} for task {task_number}: {result}"
        else:
            base_message = f"{operation} task {task_number}"
            if additional_info:
                base_message += f" ({additional_info})"
            return f"{base_message}: {result}"

    def _handle_empty_result(self, result: str, empty_message: str) -> str:
        """Handle empty results with consistent messaging."""
        return empty_message if not result.strip() else result

    def _find_task_number_by_description(self, description: str) -> int:
        """Find task number by description in the current task list."""
        # Defensive check: ensure description is a string
        if not isinstance(description, str):
            raise ValueError(
                f"Description must be a string, got {type(description)}: {description}"
            )

        if not description.strip():
            raise ValueError("Description cannot be empty or whitespace-only")

        tasks = self.todo_shell.list_tasks()

        # Defensive check: ensure tasks is a string
        if not isinstance(tasks, str):
            raise RuntimeError(
                f"Expected string from list_tasks(), got {type(tasks)}: {tasks}"
            )

        task_lines = [line.strip() for line in tasks.split("\n") if line.strip()]

        if not task_lines:
            raise RuntimeError("Failed to add task - no tasks found after addition")

        import re

        for line in reversed(task_lines):
            if description in line:
                match = re.match(r"^(\d+)", line)
                if match:
                    return int(match.group(1))

        raise RuntimeError(
            f"Could not find task with description '{description}' after adding it. "
            f"This indicates a serious issue with task matching."
        )

    # ============================================================================
    # CORE CRUD OPERATIONS
    # ============================================================================

    def add_task(
        self,
        description: str,
        priority: Optional[str] = None,
        project: Optional[str] = None,
        context: Optional[str] = None,
        due: Optional[str] = None,
        duration: Optional[str] = None,
        parent_number: Optional[int] = None,
    ) -> str:
        """Add new task with explicit project/context parameters."""
        # Validate description early - it's required and must be a non-empty string
        if not isinstance(description, str):
            raise ValueError(
                f"Description must be a string, got {type(description)}: {description}"
            )
        if not description.strip():
            raise ValueError("Description cannot be empty or whitespace-only")

        # Normalize empty strings to None for optional parameters
        priority = self._normalize_empty_to_none(priority)
        project = self._normalize_empty_to_none(project)
        context = self._normalize_empty_to_none(context)
        due = self._normalize_empty_to_none(due)
        # Note: duration is not normalized - empty strings should raise validation errors

        # Validate inputs
        self._validate_priority(priority)
        self._validate_date_format(due, "due date")
        self._validate_duration(duration)
        self._validate_parent_number(parent_number)

        # Build the full task description
        full_description = self._build_task_description(
            description, priority, project, context, due, duration, parent_number
        )

        self.todo_shell.add(full_description)
        return f"Added task: {full_description}"

    def list_tasks(
        self, filter: Optional[str] = None, suppress_color: bool = True
    ) -> str:
        """List tasks with optional filtering."""
        result = self.todo_shell.list_tasks(filter, suppress_color=suppress_color)
        return self._handle_empty_result(result, "No tasks found.")

    def complete_task(self, task_number: int) -> str:
        """Mark task complete by line number."""
        result = self.todo_shell.complete(task_number)
        return self._format_task_operation_response("Completed", task_number, result)

    def replace_task(self, task_number: int, new_description: str) -> str:
        """Replace entire task content."""
        result = self.todo_shell.replace(task_number, new_description)
        return self._format_task_operation_response("Replaced", task_number, result)

    def append_to_task(self, task_number: int, text: str) -> str:
        """Add text to end of existing task."""
        result = self.todo_shell.append(task_number, text)
        return self._format_task_operation_response("Appended to", task_number, result)

    def prepend_to_task(self, task_number: int, text: str) -> str:
        """Add text to beginning of existing task."""
        result = self.todo_shell.prepend(task_number, text)
        return self._format_task_operation_response("Prepended to", task_number, result)

    def delete_task(self, task_number: int, term: Optional[str] = None) -> str:
        """Delete entire task or specific term from task."""
        result = self.todo_shell.delete(task_number, term)
        if term is not None:
            return self._format_task_operation_response(
                "Removed", task_number, result, f"'{term}'"
            )
        else:
            return self._format_task_operation_response("Deleted", task_number, result)

    def set_priority(self, task_number: int, priority: str) -> str:
        """Set or change task priority (A-Z)."""
        priority = self._normalize_empty_to_none(priority)
        self._validate_priority(priority)
        result = self.todo_shell.set_priority(task_number, priority)
        return self._format_task_operation_response(
            "Set priority", task_number, result, priority or ""
        )

    def remove_priority(self, task_number: int) -> str:
        """Remove priority from task."""
        result = self.todo_shell.remove_priority(task_number)
        return self._format_task_operation_response(
            "Removed priority from", task_number, result
        )

    def set_due_date(self, task_number: int, due_date: str) -> str:
        """
        Set or update due date for a task by intelligently rewriting it.

        Args:
            task_number: The task number to modify
            due_date: Due date in YYYY-MM-DD format, or empty string to remove due date

        Returns:
            Confirmation message with the updated task
        """
        # Validate due date format only if not empty
        self._validate_date_format(due_date, "due date")

        result = self.todo_shell.set_due_date(task_number, due_date)
        if due_date.strip():
            return self._format_task_operation_response(
                "Set due date", task_number, result, due_date
            )
        else:
            return self._format_task_operation_response(
                "Removed due date from", task_number, result
            )

    def set_context(self, task_number: int, context: str) -> str:
        """
        Set or update context for a task by intelligently rewriting it.

        Args:
            task_number: The task number to modify
            context: Context name (without @ symbol), or empty string to remove context

        Returns:
            Confirmation message with the updated task
        """
        # Validate context name if not empty
        clean_context = self._clean_context_name(context) if context.strip() else ""

        result = self.todo_shell.set_context(task_number, context)
        if context.strip():
            return self._format_task_operation_response(
                "Set context", task_number, result, f"@{clean_context}"
            )
        else:
            return self._format_task_operation_response(
                "Removed context from", task_number, result
            )

    def set_project(self, task_number: int, projects: list) -> str:
        """
        Set or update projects for a task by intelligently rewriting it.

        Args:
            task_number: The task number to modify
            projects: List of project operations. Each item can be:
                     - "project" (add project)
                     - "-project" (remove project)
                     - Empty string removes all projects

        Returns:
            Confirmation message with the updated task
        """
        # Validate project names if not empty
        if projects:
            for project in projects:
                if project.strip() and not project.startswith("-"):
                    self._clean_project_name(project)
                elif project.startswith("-"):
                    clean_project = project[1:].strip().lstrip("+")
                    if not clean_project:
                        raise ValueError(
                            "Project name cannot be empty after removing - and + symbols."
                        )

        result = self.todo_shell.set_project(task_number, projects)

        if not projects:
            return self._format_task_operation_response(
                "No project changes made to", task_number, result
            )
        else:
            # Build operation description
            operations = []
            for project in projects:
                if not project.strip():
                    # Empty string is a NOOP - skip
                    continue
                elif project.startswith("-"):
                    clean_project = project[1:].strip().lstrip("+")
                    operations.append(f"removed +{clean_project}")
                else:
                    clean_project = project.strip().lstrip("+")
                    operations.append(f"added +{clean_project}")

            if not operations:
                return self._format_task_operation_response(
                    "No project changes made to", task_number, result
                )
            else:
                operation_desc = ", ".join(operations)
                return self._format_task_operation_response(
                    "Updated projects for", task_number, result, operation_desc
                )

    def set_parent(self, task_number: int, parent_number: Optional[int]) -> str:
        """
        Set or update parent task number for a task by intelligently rewriting it.

        Args:
            task_number: The task number to modify
            parent_number: Parent task number, or None to remove parent

        Returns:
            Confirmation message with the updated task
        """
        # Validate parent_number if provided
        self._validate_parent_number(parent_number)

        result = self.todo_shell.set_parent(task_number, parent_number)
        if parent_number is not None:
            return self._format_task_operation_response(
                "Set parent task", task_number, result, str(parent_number)
            )
        else:
            return self._format_task_operation_response(
                "Removed parent from", task_number, result
            )

    # ============================================================================
    # LISTING AND QUERY METHODS
    # ============================================================================

    def list_projects(self, suppress_color: bool = True, **kwargs: Any) -> str:
        """List all available projects in todo.txt."""
        result = self.todo_shell.list_projects(suppress_color=suppress_color)
        return self._handle_empty_result(result, "No projects found.")

    def list_contexts(self, suppress_color: bool = True, **kwargs: Any) -> str:
        """List all available contexts in todo.txt."""
        result = self.todo_shell.list_contexts(suppress_color=suppress_color)
        return self._handle_empty_result(result, "No contexts found.")

    def list_completed_tasks(
        self,
        filter: Optional[str] = None,
        project: Optional[str] = None,
        context: Optional[str] = None,
        text_search: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        suppress_color: bool = True,
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

        result = self.todo_shell.list_completed(
            combined_filter, suppress_color=suppress_color
        )
        return self._handle_empty_result(
            result, "No completed tasks found matching the criteria."
        )

    # ============================================================================
    # UTILITY OPERATIONS
    # ============================================================================

    def move_task(
        self, task_number: int, destination: str, source: Optional[str] = None
    ) -> str:
        """Move task from source to destination file."""
        result = self.todo_shell.move(task_number, destination, source)
        return self._format_task_operation_response(
            "Moved", task_number, result, f"to {destination}"
        )

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
        week_number = now.isocalendar()[1]
        timezone = now.astimezone().tzinfo
        return f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')} {timezone} ({now.strftime('%A, %B %d, %Y at %I:%M %p')}) - Week {week_number}"

    # ============================================================================
    # ADVANCED OPERATIONS
    # ============================================================================

    def create_completed_task(
        self,
        description: str,
        completion_date: Optional[str] = None,
        project: Optional[str] = None,
        context: Optional[str] = None,
        parent_number: Optional[int] = None,
    ) -> str:
        """
        Create a task and immediately mark it as completed.

        This is a convenience method for handling "I did X on [date]" statements.
        The task is created with the specified completion date and immediately marked complete.

        Args:
            description: The task description of what was completed
            completion_date: Completion date in YYYY-MM-DD format (defaults to today)
            project: Optional project name (without the + symbol)
            context: Optional context name (without the @ symbol)
            parent_number: Optional parent task number (required for subtasks)

        Returns:
            Confirmation message with the completed task details
        """
        # Normalize empty strings to None
        project = self._normalize_empty_to_none(project)
        context = self._normalize_empty_to_none(context)

        # Set default completion date to today if not provided
        if not completion_date:
            completion_date = datetime.now().strftime("%Y-%m-%d")

        # Validate inputs
        self._validate_date_format(completion_date, "completion date")
        self._validate_parent_number(parent_number)

        # Build the task description
        full_description = self._build_task_description(
            description, project=project, context=context, parent_number=parent_number
        )

        # Check if we need to use a specific completion date
        current_date = datetime.now().strftime("%Y-%m-%d")
        use_specific_date = completion_date != current_date

        if use_specific_date:
            # When using a specific completion date, add directly to done.txt
            # Format: "x YYYY-MM-DD [task description]"
            completed_task_line = f"x {completion_date} {full_description}"
            self.todo_shell.addto("done.txt", completed_task_line)
            return f"Created and completed task: {full_description} (completed on {completion_date})"
        else:
            # When using current date, use the standard add + complete workflow
            # Add the task first
            self.todo_shell.add(full_description)

            # Find the task number and mark it complete
            task_number = self._find_task_number_by_description(description)
            self.todo_shell.complete(task_number)

            return f"Created and completed task: {full_description} (completed on {completion_date})"

    def restore_completed_task(self, task_number: int) -> str:
        """
        Restore a completed task from done.txt back to todo.txt.

        This method moves a completed task from done.txt back to todo.txt,
        effectively restoring it to active status.

        Args:
            task_number: The line number of the completed task in done.txt to restore

        Returns:
            Confirmation message with the restored task details
        """
        # Validate task number
        if task_number <= 0:
            raise ValueError("Task number must be a positive integer")

        # Use the move command to restore the task from done.txt to todo.txt
        result = self.todo_shell.move(task_number, "todo.txt", "done.txt")

        # Extract the task description from the result for confirmation
        # The result format is typically: "TODO: X moved from '.../done.txt' to '.../todo.txt'."
        if "moved from" in result and "to" in result:
            # Try to extract the task description if possible
            return f"Restored completed task {task_number} to active status: {result}"
        else:
            return f"Restored completed task {task_number} to active status"
