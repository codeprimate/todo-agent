"""
Subprocess wrapper for todo.sh operations.
"""

import os
import subprocess  # nosec B404
from typing import Any, List, Optional, TypedDict

try:
    from todo_agent.core.exceptions import TodoShellError
except ImportError:
    from core.exceptions import TodoShellError  # type: ignore[no-redef]


class TaskComponents(TypedDict):
    """Type definition for task components."""

    priority: str | None
    description: str
    projects: list[str]
    contexts: list[str]
    due: str | None

    other_tags: list[str]


class TodoShell:
    """Subprocess execution wrapper with error management."""

    def __init__(self, todo_file_path: str, logger: Optional[Any] = None) -> None:
        self.todo_file_path = todo_file_path
        self.todo_dir = os.path.dirname(todo_file_path) or os.getcwd()
        self.logger = logger

    def execute(
        self,
        command: List[str],
        cwd: Optional[str] = None,
        suppress_color: bool = False,
    ) -> str:
        """
        Execute a todo.sh command and return the output.

        Args:
            command: List of command arguments
            cwd: Working directory (defaults to todo.sh directory)
            suppress_color: If True, strip ANSI color codes from output (for LLM consumption)

        Returns:
            Command output as string

        Raises:
            TodoShellError: If command execution fails
        """
        # Log the raw command being executed
        if self.logger:
            raw_command = " ".join(command)
            self.logger.debug(f"=== RAW COMMAND EXECUTION ===")
            self.logger.debug(f"Raw command: {raw_command}")
            self.logger.debug(f"Working directory: {cwd or self.todo_dir}")
            self.logger.debug(f"Suppress color: {suppress_color}")

        try:
            working_dir = cwd or self.todo_dir
            result = subprocess.run(  # nosec B603
                command, cwd=working_dir, capture_output=True, text=True, check=True
            )

            # Log the raw output
            if self.logger:
                self.logger.debug(f"=== RAW COMMAND OUTPUT ===")
                self.logger.debug(f"Raw command: {raw_command}")
                self.logger.debug(f"Raw stdout: {result.stdout}")
                self.logger.debug(f"Raw stderr: {result.stderr}")
                self.logger.debug(f"Return code: {result.returncode}")

            output = result.stdout.strip()

            # Strip ANSI color codes if requested (for LLM consumption)
            if suppress_color:
                from rich.text import Text

                # Use Rich's Text.from_ansi to parse and then get plain text
                try:
                    plain_output = Text.from_ansi(output).plain
                    output = plain_output
                except Exception as e:
                    if self.logger:
                        self.logger.warning(
                            f"Failed to strip ANSI codes using Rich: {e}, falling back to original output"
                        )
                    # Fallback: keep original output if Rich processing fails

                if self.logger:
                    self.logger.debug(
                        f"Stripped ANSI codes from output for LLM consumption"
                    )

            return output
        except subprocess.CalledProcessError as e:
            # Log error details
            if self.logger:
                self.logger.error(f"=== COMMAND EXECUTION FAILED ===")
                self.logger.error(f"Raw command: {' '.join(command)}")
                self.logger.error(f"Error stderr: {e.stderr}")
                self.logger.error(f"Error return code: {e.returncode}")
            raise TodoShellError(f"Todo.sh command failed: {e.stderr}")
        except Exception as e:
            # Log error details
            if self.logger:
                self.logger.error(f"=== COMMAND EXECUTION EXCEPTION ===")
                self.logger.error(f"Raw command: {' '.join(command)}")
                self.logger.error(f"Exception: {e!s}")
            raise TodoShellError(f"Todo.sh command failed: {e}")

    def add(self, description: str) -> str:
        """Add new task."""
        return self.execute(["todo.sh", "add", description])

    def addto(self, destination: str, text: str) -> str:
        """Add text to a specific file in the todo.txt directory."""
        return self.execute(["todo.sh", "addto", destination, text])

    def list_tasks(
        self, filter_str: Optional[str] = None, suppress_color: bool = True
    ) -> str:
        """List tasks with optional filtering."""
        command = ["todo.sh", "ls"]
        if filter_str:
            command.append(filter_str)
        return self.execute(command, suppress_color=suppress_color)

    def complete(self, task_number: int) -> str:
        """Mark task complete."""
        return self.execute(["todo.sh", "do", str(task_number)])

    def replace(self, task_number: int, new_description: str) -> str:
        """Replace task content."""
        return self.execute(["todo.sh", "replace", str(task_number), new_description])

    def append(self, task_number: int, text: str) -> str:
        """Append text to task."""
        return self.execute(["todo.sh", "append", str(task_number), text])

    def prepend(self, task_number: int, text: str) -> str:
        """Prepend text to task."""
        return self.execute(["todo.sh", "prepend", str(task_number), text])

    def delete(self, task_number: int, term: Optional[str] = None) -> str:
        """Delete task or term."""
        command = ["todo.sh", "-f", "del", str(task_number)]
        if term:
            command.append(term)
        return self.execute(command)

    def move(
        self, task_number: int, destination: str, source: Optional[str] = None
    ) -> str:
        """Move task from source to destination file."""
        command = ["todo.sh", "-f", "move", str(task_number), destination]
        if source:
            command.append(source)
        return self.execute(command)

    def set_priority(self, task_number: int, priority: str) -> str:
        """Set task priority."""
        return self.execute(["todo.sh", "pri", str(task_number), priority])

    def remove_priority(self, task_number: int) -> str:
        """Remove task priority."""
        return self.execute(["todo.sh", "depri", str(task_number)])

    def list_projects(self, suppress_color: bool = True) -> str:
        """List projects."""
        return self.execute(["todo.sh", "lsp"], suppress_color=suppress_color)

    def list_contexts(self, suppress_color: bool = True) -> str:
        """List contexts."""
        return self.execute(["todo.sh", "lsc"], suppress_color=suppress_color)

    def list_completed(
        self, filter_str: Optional[str] = None, suppress_color: bool = True
    ) -> str:
        """List completed tasks with optional filtering."""
        command = ["todo.sh", "listfile", "done.txt"]
        if filter_str:
            command.append(filter_str)
        return self.execute(command, suppress_color=suppress_color)

    def archive(self) -> str:
        """Archive completed tasks."""
        return self.execute(["todo.sh", "-f", "archive"])

    def get_help(self) -> str:
        """Get todo.sh help output."""
        return self.execute(["todo.sh", "help"], suppress_color=False)

    def set_due_date(self, task_number: int, due_date: str) -> str:
        """
        Set or update due date for a task by intelligently rewriting it.

        Args:
            task_number: The task number to modify
            due_date: Due date in YYYY-MM-DD format, or empty string to remove due date

        Returns:
            The updated task description
        """
        # First, get the current task to parse its components
        tasks_output = self.list_tasks()
        task_lines = tasks_output.strip().split("\n")

        # Find the task by its actual number (not array index)
        current_task = None
        for line in task_lines:
            if line.strip():
                # Extract task number from the beginning of the line (handling ANSI codes)
                extracted_number = self._extract_task_number(line)
                if extracted_number == task_number:
                    current_task = line
                    break

        if not current_task:
            raise TodoShellError(f"Task number {task_number} not found")

        # Parse the current task components
        components = self._parse_task_components(current_task)

        # Update the due date (empty string removes it)
        if due_date.strip():
            components["due"] = due_date
        else:
            components["due"] = None

        # Reconstruct the task
        new_description = self._reconstruct_task(components)

        # Replace the task with the new description
        return self.replace(task_number, new_description)

    def set_context(self, task_number: int, context: str) -> str:
        """
        Set or update context for a task by intelligently rewriting it.

        Args:
            task_number: The task number to modify
            context: Context name (without @ symbol), or empty string to remove context

        Returns:
            The updated task description
        """
        # First, get the current task to parse its components
        tasks_output = self.list_tasks()
        task_lines = tasks_output.strip().split("\n")

        # Find the task by its actual number (not array index)
        current_task = None
        for line in task_lines:
            if line.strip():
                # Extract task number from the beginning of the line (handling ANSI codes)
                extracted_number = self._extract_task_number(line)
                if extracted_number == task_number:
                    current_task = line
                    break

        if not current_task:
            raise TodoShellError(f"Task number {task_number} not found")

        # Parse the current task components
        components = self._parse_task_components(current_task)

        # Update the context (empty string removes it)
        if context.strip():
            # Remove any existing @ symbols to prevent duplication
            clean_context = context.strip().lstrip("@")
            if not clean_context:
                raise TodoShellError(
                    "Context name cannot be empty after removing @ symbol."
                )
            context_tag = f"@{clean_context}"
            # Only add if not already present (deduplication)
            if context_tag not in components["contexts"]:
                components["contexts"] = [context_tag]
            else:
                # Context already exists, no change needed
                return self._reconstruct_task(components)
        else:
            components["contexts"] = []

        # Reconstruct the task
        new_description = self._reconstruct_task(components)

        # Replace the task with the new description
        return self.replace(task_number, new_description)

    def set_parent(self, task_number: int, parent_number: Optional[int]) -> str:
        """
        Set or update parent task number for a task by intelligently rewriting it.

        Args:
            task_number: The task number to modify
            parent_number: Parent task number, or None to remove parent

        Returns:
            The updated task description
        """
        # First, get the current task to parse its components
        tasks_output = self.list_tasks()
        task_lines = tasks_output.strip().split("\n")

        # Find the task by its actual number (not array index)
        current_task = None
        for line in task_lines:
            if line.strip():
                # Extract task number from the beginning of the line (handling ANSI codes)
                extracted_number = self._extract_task_number(line)
                if extracted_number == task_number:
                    current_task = line
                    break

        if not current_task:
            raise TodoShellError(f"Task number {task_number} not found")

        # Parse the current task components
        components = self._parse_task_components(current_task)

        # Update the parent (None removes it)
        if parent_number is not None:
            if not isinstance(parent_number, int) or parent_number <= 0:
                raise TodoShellError(
                    f"Invalid parent_number '{parent_number}'. Must be a positive integer."
                )
            parent_tag = f"parent:{parent_number}"
            # Remove any existing parent tag and add the new one
            components["other_tags"] = [
                tag for tag in components["other_tags"] if not tag.startswith("parent:")
            ]
            components["other_tags"].append(parent_tag)
        else:
            # Remove parent tag
            components["other_tags"] = [
                tag for tag in components["other_tags"] if not tag.startswith("parent:")
            ]

        # Reconstruct the task
        new_description = self._reconstruct_task(components)

        # Replace the task with the new description
        return self.replace(task_number, new_description)

    def _extract_task_number(self, line: str) -> Optional[int]:
        """
        Extract task number from a line that may contain ANSI color codes.

        Args:
            line: Task line that may contain ANSI color codes

        Returns:
            Task number if found, None otherwise
        """
        from rich.text import Text

        # Use rich to properly handle ANSI color codes
        text = Text.from_ansi(line)
        clean_line = text.plain

        # Split on first space and check if first part is a number
        parts = clean_line.split(" ", 1)
        if parts and parts[0].isdigit():
            return int(parts[0])
        return None

    def set_project(self, task_number: int, projects: list) -> str:
        """
        Set or update projects for a task by intelligently rewriting it.

        Args:
            task_number: The task number to modify
            projects: List of project operations. Each item can be:
                     - "project" (add project)
                     - "-project" (remove project)
                     - Empty string is a NOOP

        Returns:
            The updated task description
        """
        # First, get the current task to parse its components
        tasks_output = self.list_tasks()
        task_lines = tasks_output.strip().split("\n")

        # Find the task by its actual number (not array index)
        current_task = None
        for line in task_lines:
            if line.strip():
                # Extract task number from the beginning of the line (handling ANSI codes)
                extracted_number = self._extract_task_number(line)
                if extracted_number == task_number:
                    current_task = line
                    break

        if not current_task:
            raise TodoShellError(f"Task number {task_number} not found")

        # Parse the current task components
        components = self._parse_task_components(current_task)

        # Store original projects to check if any changes were made
        original_projects = components["projects"].copy()

        # Handle project operations
        if not projects:
            # Empty list is a NOOP - return original task unchanged
            return self._reconstruct_task(components)
        else:
            # Process each project operation
            for project in projects:
                if not project.strip():
                    # Empty string is a NOOP - skip this operation
                    continue
                elif project.startswith("-"):
                    # Remove project
                    clean_project = project[1:].strip().lstrip("+")
                    if not clean_project:
                        raise TodoShellError(
                            "Project name cannot be empty after removing - and + symbols."
                        )
                    # Remove the project if it exists (with or without + prefix)
                    project_to_remove = f"+{clean_project}"
                    components["projects"] = [
                        p
                        for p in components["projects"]
                        if p != project_to_remove and p != clean_project
                    ]
                else:
                    # Add project
                    clean_project = project.strip().lstrip("+")
                    if not clean_project:
                        raise TodoShellError(
                            "Project name cannot be empty after removing + symbol."
                        )
                    project_tag = f"+{clean_project}"
                    # Only add if not already present (deduplication)
                    if project_tag not in components["projects"]:
                        components["projects"].append(project_tag)

        # Check if any changes were actually made
        if components["projects"] == original_projects:
            # No changes made - return original task unchanged
            return self._reconstruct_task(components)

        # Reconstruct the task
        new_description = self._reconstruct_task(components)

        # Replace the task with the new description
        return self.replace(task_number, new_description)

    def _parse_task_components(self, task_line: str) -> TaskComponents:
        """
        Parse a todo.txt task line into its components.

        Args:
            task_line: Raw task line from todo.txt

        Returns:
            Dictionary with parsed components
        """
        # Remove ANSI color codes first using rich
        from rich.text import Text

        text = Text.from_ansi(task_line)
        task_line = text.plain

        # Remove task number prefix if present (e.g., "1 " or "1. ")
        # First try the format without dot (standard todo.sh format)
        if " " in task_line and task_line.split(" ")[0].isdigit():
            task_line = task_line.split(" ", 1)[1]
        # Fallback to dot format if present
        elif ". " in task_line:
            task_line = task_line.split(". ", 1)[1]

        components: TaskComponents = {
            "priority": None,
            "description": "",
            "projects": [],
            "contexts": [],
            "due": None,
            "other_tags": [],
        }

        # Use sets to automatically deduplicate projects and contexts
        projects_set = set()
        contexts_set = set()
        other_tags_set = set()

        # Split by spaces to process each word
        words = task_line.split()

        for word in words:
            # Priority: (A), (B), etc.
            if word.startswith("(") and word.endswith(")") and len(word) == 3:
                priority = word[1]
                if priority.isalpha() and priority.isupper():
                    components["priority"] = priority
                    continue

            # Projects: +project
            if word.startswith("+"):
                projects_set.add(word)
                continue

            # Contexts: @context
            if word.startswith("@"):
                contexts_set.add(word)
                continue

            # Due date: due:YYYY-MM-DD
            if word.startswith("due:"):
                components["due"] = word[4:]  # Remove 'due:' prefix
                continue

            # Other tags (like custom tags)
            if ":" in word and not word.startswith("due:"):
                other_tags_set.add(word)
                continue

            # Regular description text
            if components["description"]:
                components["description"] += " " + word
            else:
                components["description"] = word

        # Convert sets back to sorted lists for consistent ordering
        components["projects"] = sorted(projects_set)
        components["contexts"] = sorted(contexts_set)
        components["other_tags"] = sorted(other_tags_set)

        return components

    def _reconstruct_task(self, components: TaskComponents) -> str:
        """
        Reconstruct a task description from parsed components.

        Args:
            components: Dictionary with task components

        Returns:
            Reconstructed task description
        """
        parts = []

        # Add priority if present
        if components["priority"]:
            parts.append(f"({components['priority']})")

        # Add description
        if components["description"]:
            parts.append(components["description"])

        # Add projects
        parts.extend(components["projects"])

        # Add contexts
        parts.extend(components["contexts"])

        # Add due date
        if components["due"]:
            parts.append(f"due:{components['due']}")

        # Add other tags
        parts.extend(components["other_tags"])

        return " ".join(parts)
