"""
Subprocess wrapper for todo.sh operations.
"""

import os
import subprocess
from typing import Any, List, Optional

try:
    from todo_agent.core.exceptions import TodoShellError
except ImportError:
    from core.exceptions import TodoShellError  # type: ignore[no-redef]


class TodoShell:
    """Subprocess execution wrapper with error management."""

    def __init__(self, todo_file_path: str, logger: Optional[Any] = None) -> None:
        self.todo_file_path = todo_file_path
        self.todo_dir = os.path.dirname(todo_file_path) or os.getcwd()
        self.logger = logger

    def execute(self, command: List[str], cwd: Optional[str] = None) -> str:
        """
        Execute todo.sh command.

        Args:
            command: List of command arguments
            cwd: Working directory (defaults to todo.sh directory)

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

        try:
            working_dir = cwd or self.todo_dir
            result = subprocess.run(
                command, cwd=working_dir, capture_output=True, text=True, check=True
            )

            # Log the raw output
            if self.logger:
                self.logger.debug(f"=== RAW COMMAND OUTPUT ===")
                self.logger.debug(f"Raw command: {raw_command}")
                self.logger.debug(f"Raw stdout: {result.stdout}")
                self.logger.debug(f"Raw stderr: {result.stderr}")
                self.logger.debug(f"Return code: {result.returncode}")

            return result.stdout.strip()
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

    def list_tasks(self, filter_str: Optional[str] = None) -> str:
        """List tasks with optional filtering."""
        command = ["todo.sh", "ls"]
        if filter_str:
            command.append(filter_str)
        return self.execute(command)

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

    def list_projects(self) -> str:
        """List projects."""
        return self.execute(["todo.sh", "lsp"])

    def list_contexts(self) -> str:
        """List contexts."""
        return self.execute(["todo.sh", "lsc"])

    def list_completed(self, filter_str: Optional[str] = None) -> str:
        """List completed tasks with optional filtering."""
        command = ["todo.sh", "listfile", "done.txt"]
        if filter_str:
            command.append(filter_str)
        return self.execute(command)

    def archive(self) -> str:
        """Archive completed tasks."""
        return self.execute(["todo.sh", "-f", "archive"])

    def deduplicate(self) -> str:
        """Remove duplicate tasks."""
        try:
            return self.execute(["todo.sh", "-f", "deduplicate"])
        except TodoShellError as e:
            # Handle the case where no duplicates are found (not really an error)
            if "No duplicate tasks found" in str(e):
                return "No duplicate tasks found"
            raise
