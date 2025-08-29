"""
Domain-specific exceptions for todo.sh operations.
"""


class TodoError(Exception):
    """Base exception for todo operations."""

    pass


class TaskNotFoundError(TodoError):
    """Task not found in todo file."""

    pass


class InvalidTaskFormatError(TodoError):
    """Invalid task format."""

    pass


class TodoShellError(TodoError):
    """Subprocess execution error."""

    pass
