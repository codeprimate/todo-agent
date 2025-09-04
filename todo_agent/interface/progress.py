"""
Progress tracking interface for tool call execution.
"""

from abc import ABC, abstractmethod


class ToolCallProgress(ABC):
    """Abstract interface for tool call progress tracking."""

    @abstractmethod
    def on_thinking_start(self) -> None:
        """Called when LLM starts thinking."""
        pass

    @abstractmethod
    def on_tool_call_start(
        self,
        tool_name: str,
        progress_description: str,
        sequence: int,
        total_sequences: int,
    ) -> None:
        """Called when a tool call starts."""
        pass

    @abstractmethod
    def on_tool_call_complete(
        self, tool_name: str, success: bool, duration: float
    ) -> None:
        """Called when a tool call completes (optional - no action needed)."""
        pass

    @abstractmethod
    def on_sequence_complete(self, sequence: int, total_sequences: int) -> None:
        """Called when a tool call sequence completes."""
        pass

    @abstractmethod
    def on_thinking_complete(self, total_time: float) -> None:
        """Called when thinking is complete."""
        pass


class NoOpProgress(ToolCallProgress):
    """No-operation implementation for when progress tracking is not needed."""

    def on_thinking_start(self) -> None:
        pass

    def on_tool_call_start(
        self,
        tool_name: str,
        progress_description: str,
        sequence: int,
        total_sequences: int,
    ) -> None:
        pass

    def on_tool_call_complete(
        self, tool_name: str, success: bool, duration: float
    ) -> None:
        pass

    def on_sequence_complete(self, sequence: int, total_sequences: int) -> None:
        pass

    def on_thinking_complete(self, total_time: float) -> None:
        pass
