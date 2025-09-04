"""
Domain-specific exceptions for todo.sh operations.
"""


class TodoError(Exception):
    """Base exception for todo operations."""

    pass


class TaskNotFoundError(TodoError):
    """Task not found in todo file."""

    def __init__(self, message: str = "Task not found"):
        super().__init__(message)
        self.message = message


class InvalidTaskFormatError(TodoError):
    """Invalid task format."""

    def __init__(self, message: str = "Invalid task format"):
        super().__init__(message)
        self.message = message


class TodoShellError(TodoError):
    """Subprocess execution error."""

    def __init__(self, message: str = "Todo.sh command failed"):
        super().__init__(message)
        self.message = message


class ProviderError(Exception):
    """Base exception for LLM provider errors."""

    def __init__(self, message: str, error_type: str, provider: str):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.provider = provider


class MalformedResponseError(ProviderError):
    """Provider returned malformed or invalid response."""

    def __init__(self, message: str, provider: str):
        super().__init__(message, "malformed_response", provider)


class RateLimitError(ProviderError):
    """Provider rate limit exceeded."""

    def __init__(self, message: str, provider: str):
        super().__init__(message, "rate_limit", provider)


class AuthenticationError(ProviderError):
    """Provider authentication failed."""

    def __init__(self, message: str, provider: str):
        super().__init__(message, "auth_error", provider)


class TimeoutError(ProviderError):
    """Provider request timed out."""

    def __init__(self, message: str, provider: str):
        super().__init__(message, "timeout", provider)


class GeneralProviderError(ProviderError):
    """General provider error."""

    def __init__(self, message: str, provider: str):
        super().__init__(message, "general_error", provider)
