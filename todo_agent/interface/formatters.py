"""
Formatters for CLI output with unicode characters and consistent styling.
"""

from typing import Optional

from rich.align import Align
from rich.box import ROUNDED
from rich.panel import Panel
from rich.text import Text

# CLI width configuration
CLI_WIDTH = 100
PANEL_WIDTH = CLI_WIDTH - 2  # Leave 2 characters for borders

# Provider error message mapping
PROVIDER_ERROR_MESSAGES = {
    "malformed_response": "I got a confusing response from my AI service. Please try again, or type 'clear' to reset our conversation.",
    "malformed_tool_call": "I received a malformed request. Please try again, or type 'clear' to reset our conversation.",
    "rate_limit": "I'm a bit overwhelmed right now. Please wait a moment and try again, or type 'clear' to start fresh.",
    "auth_error": "I can't connect to my AI service. Please check your configuration, or type 'clear' to reset.",
    "timeout": "The request took too long. Please try again, or type 'clear' to reset our conversation.",
    "general_error": "Something went wrong with my AI service. Please try again, or type 'clear' to reset our conversation.",
}


def get_provider_error_message(error_type: str) -> str:
    """
    Get user-friendly error message for provider errors.

    Args:
        error_type: The type of provider error

    Returns:
        User-friendly error message with recovery suggestion
    """
    return PROVIDER_ERROR_MESSAGES.get(
        error_type, PROVIDER_ERROR_MESSAGES["general_error"]
    )


class TaskFormatter:
    """Formats task-related output with unicode characters and consistent styling."""

    @staticmethod
    def format_task_list(raw_tasks: str) -> Text:
        """
        Format a raw task list while preserving ANSI color codes from todo.sh.

        Args:
            raw_tasks: Raw task output from todo.sh with ANSI codes

        Returns:
            Formatted task list as Rich Text object with preserved ANSI codes
        """
        if not raw_tasks.strip():
            return Text("No tasks found.")

        lines = raw_tasks.strip().split("\n")
        formatted_text = Text()
        task_count = 0

        for line in lines:
            line = line.strip()
            # Skip empty lines, separators, and todo.sh's own summary line
            if line and line != "--" and not line.startswith("TODO:"):
                task_count += 1
                # Preserve the original ANSI codes by using Text.from_ansi directly
                task_text = Text.from_ansi(line)
                formatted_text.append(task_text)
                formatted_text.append("\n")

        # Add task count at the end
        if task_count > 0:
            formatted_text.append("\n")
            formatted_text.append(f"TODO: {task_count} of {task_count} tasks shown")
        else:
            formatted_text = Text("No tasks found.")

        return formatted_text

    @staticmethod
    def format_completed_tasks(raw_tasks: str) -> Text:
        """
        Format a raw completed task list while preserving ANSI color codes from todo.sh.

        Args:
            raw_tasks: Raw completed task output from todo.sh with ANSI codes

        Returns:
            Formatted completed task list as Rich Text object with preserved ANSI codes
        """
        if not raw_tasks.strip():
            return Text("No completed tasks found.")

        lines = raw_tasks.strip().split("\n")
        formatted_text = Text()
        task_count = 0

        for line in lines:
            line = line.strip()
            # Skip empty lines, separators, and todo.sh's own summary line
            if line and line != "--" and not line.startswith("TODO:"):
                task_count += 1
                # Preserve the original ANSI codes by using Text.from_ansi directly
                task_text = Text.from_ansi(line)
                formatted_text.append(task_text)
                formatted_text.append("\n")

        # Add task count at the end
        if task_count > 0:
            formatted_text.append("\n")
        else:
            formatted_text = Text("No completed tasks found.")

        return formatted_text

    @staticmethod
    def _format_single_task(task_line: str, task_number: int) -> str:
        """
        Format a single task line with unicode characters.

        Args:
            task_line: Raw task line from todo.sh
            task_number: Task number for display

        Returns:
            Formatted task string
        """
        # Parse todo.txt format: "1 (A) 2025-08-29 Clean cat box @home +chores due:2025-08-29"
        parts = task_line.split(
            " ", 1
        )  # Split on first space to separate number from rest
        if len(parts) < 2:
            return f"  {task_number:2d} │   │ {task_line}"

        rest = parts[1]

        # Extract priority if present (format: "(A)")
        priority = ""
        description = rest

        if rest.startswith("(") and ")" in rest:
            priority_end = rest.find(")")
            priority = rest[1:priority_end]
            description = rest[priority_end + 1 :].strip()

        # Format with unicode characters
        if priority:
            formatted_line = f"  {task_number:2d} │ {priority} │ {description}"
        else:
            formatted_line = f"  {task_number:2d} │   │ {description}"

        return formatted_line

    @staticmethod
    def _format_single_completed_task(task_line: str, task_number: int) -> str:
        """
        Format a single completed task line with unicode characters.

        Args:
            task_line: Raw completed task line from todo.sh
            task_number: Task number for display

        Returns:
            Formatted completed task string
        """
        # Parse completed task format: "x 2025-08-29 2025-08-28 Clean cat box @home +chores"
        # The format is: "x completion_date creation_date description"
        parts = task_line.split(
            " ", 2
        )  # Split on first two spaces to separate x, dates, and description
        if len(parts) < 3:
            return f"  {task_number:2d} │   │ {task_line}"

        description = parts[2]

        # Format with unicode characters
        formatted_line = f"  {task_number:2d} │ {description}"

        return formatted_line

    @staticmethod
    def format_projects(raw_projects: str) -> str:
        """
        Format project list with unicode characters.

        Args:
            raw_projects: Raw project output from todo.sh

        Returns:
            Formatted project list string
        """
        if not raw_projects.strip():
            return "No projects found."

        lines = raw_projects.strip().split("\n")
        formatted_lines = []

        for i, project in enumerate(lines, 1):
            if project.strip():
                # Remove the + prefix and format nicely
                clean_project = project.strip().lstrip("+")
                formatted_lines.append(f"  {i:2d} │ {clean_project}")

        if formatted_lines:
            return "\n".join(formatted_lines)
        else:
            return "No projects found."

    @staticmethod
    def format_contexts(raw_contexts: str) -> str:
        """
        Format context list with unicode characters.

        Args:
            raw_contexts: Raw context output from todo.sh

        Returns:
            Formatted context list string
        """
        if not raw_contexts.strip():
            return "No contexts found."

        lines = raw_contexts.strip().split("\n")
        formatted_lines = []

        for i, context in enumerate(lines, 1):
            if context.strip():
                # Remove the @ prefix and format nicely
                clean_context = context.strip().lstrip("@")
                formatted_lines.append(f"  {i:2d} │ {clean_context}")

        if formatted_lines:
            return "\n".join(formatted_lines)
        else:
            return "No contexts found."


class ResponseFormatter:
    """Formats LLM responses and other output with consistent styling."""

    @staticmethod
    def format_response(response: str) -> str:
        """
        Format am LLM response.

        Args:
            response: Raw response text

        Returns:
            Formatted response string
        """

        return response

    @staticmethod
    def format_error(error_message: str) -> str:
        """
        Format error messages consistently.

        Args:
            error_message: Error message to format

        Returns:
            Formatted error string
        """
        return f"❌ {error_message}"

    @staticmethod
    def format_success(message: str) -> str:
        """
        Format success messages consistently.

        Args:
            message: Success message to format

        Returns:
            Formatted success string
        """
        return f"✅ {message}"


class StatsFormatter:
    """Formats statistics and overview information."""

    @staticmethod
    def format_overview(overview: str) -> str:
        """
        Format task overview with unicode characters.

        Args:
            overview: Raw overview string

        Returns:
            Formatted overview string
        """
        if "Task Overview:" in overview:
            lines = overview.split("\n")
            formatted_lines = []

            for line in lines:
                if line.startswith("- Active tasks:"):
                    formatted_lines.append(f"📋 {line[2:]}")
                elif line.startswith("- Completed tasks:"):
                    formatted_lines.append(f"✅ {line[2:]}")
                else:
                    formatted_lines.append(line)

            return "\n".join(formatted_lines)

        return overview


class PanelFormatter:
    """Creates rich panels for various content displays."""

    @staticmethod
    def create_header_panel() -> Panel:
        """Create the application header panel."""
        header_text = Text("Todo.sh LLM Agent", style="bold blue")
        return Panel(
            Align.center(header_text),
            title="🤖",
            border_style="dim",
            box=ROUNDED,
            width=PANEL_WIDTH + 2,
        )

    @staticmethod
    def create_task_panel(
        content: str | Text, title: str = "📋 Current Tasks"
    ) -> Panel:
        """Create a panel for displaying task lists."""
        return Panel(
            content, title=title, border_style="dim", box=ROUNDED, width=PANEL_WIDTH
        )

    @staticmethod
    def create_response_panel(
        content: str, title: str = "🤖 Assistant", memory_usage: Optional[Text] = None
    ) -> Panel:
        """Create a panel for displaying LLM responses."""
        if memory_usage:
            # Create the combined content with centered memory usage
            combined_content = Text()
            combined_content.append(content)
            combined_content.append("\n\n")
            combined_content.append("─" * (PANEL_WIDTH - 4))  # Separator line
            combined_content.append("\n")
            combined_content.append(memory_usage)

            return Panel(
                Align.center(combined_content),
                title=title,
                border_style="dim",
                box=ROUNDED,
                width=PANEL_WIDTH,
            )
        else:
            return Panel(
                content, title=title, border_style="dim", box=ROUNDED, width=PANEL_WIDTH
            )

    @staticmethod
    def create_error_panel(content: str, title: str = "❌ Error") -> Panel:
        """Create a panel for displaying errors."""
        return Panel(
            content, title=title, border_style="red", box=ROUNDED, width=PANEL_WIDTH
        )

    @staticmethod
    def create_about_panel() -> Panel:
        """Create a panel for displaying about information."""
        from todo_agent._version import __commit_id__, __version__

        about_content = Text()
        about_content.append("Todo.sh LLM Agent\n", style="bold blue")
        about_content.append("\n")
        about_content.append(
            "A natural language interface for todo.sh task management\n", style="white"
        )
        about_content.append("powered by LLM function calling.\n", style="white")
        about_content.append("\n")
        about_content.append("Version: ", style="cyan")
        about_content.append(f"{__version__}\n", style="white")
        if __commit_id__:
            about_content.append("Commit: ", style="cyan")
            about_content.append(f"{__commit_id__}\n", style="white")
        about_content.append("\n")
        about_content.append(
            "Transform natural language into todo.sh commands:\n", style="italic"
        )
        about_content.append("• 'add buy groceries to shopping list'\n", style="dim")
        about_content.append("• 'show my work tasks'\n", style="dim")
        about_content.append("• 'mark task 3 as done'\n", style="dim")
        about_content.append("\n")
        about_content.append("GitHub: ", style="cyan")
        about_content.append(
            "https://github.com/codeprimate/todo-agent\n", style="blue"
        )

        return Panel(
            Align.center(about_content),
            title="i  About",
            border_style="dim",
            box=ROUNDED,
            width=PANEL_WIDTH + 2,
        )

    @staticmethod
    def create_help_panel() -> Panel:
        """Create a panel for displaying help information."""
        help_content = Text()
        help_content.append("Available Commands\n", style="bold blue")
        help_content.append("\n")

        # Add commands in a formatted list
        commands = [
            ("help", "Show this help message"),
            ("quit", "Exit the application"),
            ("list", "List all tasks"),
            ("done", "List completed tasks"),
            ("clear", "Clear conversation history"),
            ("/[cmd] [args]", "Direct todo.sh access: /add 'task'"),
            ("todo-help", "Show todo.sh help"),
            ("about", "Show application information"),
        ]

        for cmd, desc in commands:
            help_content.append(f"{cmd:<12} ", style="cyan")
            help_content.append(f"{desc}\n", style="white")

        help_content.append("\n")
        help_content.append(
            "Or just type your request naturally!", style="italic green"
        )

        return Panel(
            Align.center(help_content),
            title="?  Help",
            border_style="dim",
            box=ROUNDED,
            width=PANEL_WIDTH + 2,
        )

    @staticmethod
    def create_memory_usage_bar(
        current_tokens: int, max_tokens: int, current_messages: int, max_messages: int
    ) -> Text:
        """
        Create a rich progress bar showing session memory usage.

        Args:
            current_tokens: Current number of tokens in conversation
            max_tokens: Maximum allowed tokens
            current_messages: Current number of messages in conversation
            max_messages: Maximum allowed messages

        Returns:
            Rich Text object with memory usage progress bar
        """
        # Calculate percentage
        token_percentage = min(100, (current_tokens / max_tokens) * 100)

        # Create the progress bar text with new layout
        memory_text = Text()

        # Calculate available width (PANEL_WIDTH - 4 for borders = 94 chars)
        # Account for emoji width by using a slightly reduced width
        available_width = 92  # Balance between full width and emoji spacing

        # Left section: Floppy disk + token count
        left_section = f"💾 {current_tokens:,}/{max_tokens:,}"
        left_width = len(left_section)

        # Right section: Message count + floppy disk
        right_section = f"{current_messages}/{max_messages} 💾"
        right_width = len(right_section)

        # Center section: Progress bar (2x wider = 50 chars) + percentage
        bar_length = 50
        token_filled = int((token_percentage / 100) * bar_length)
        token_bar = "█" * token_filled + "░" * (bar_length - token_filled)
        center_section = f"[{token_bar}] {token_percentage:.1f}%"
        center_width = len(center_section)

        # Calculate spacing to center the progress bar
        total_content_width = left_width + center_width + right_width
        remaining_space = available_width - total_content_width

        # Ensure we have enough space, if not, reduce the progress bar length
        if remaining_space < 0:
            # Reduce bar length to fit everything
            excess = abs(remaining_space)
            bar_length = max(30, 50 - excess)  # Minimum 30 chars
            token_filled = int((token_percentage / 100) * bar_length)
            token_bar = "█" * token_filled + "░" * (bar_length - token_filled)
            center_section = f"[{token_bar}] {token_percentage:.1f}%"
            center_width = len(center_section)
            total_content_width = left_width + center_width + right_width
            remaining_space = available_width - total_content_width

        # Distribute remaining space equally for symmetrical layout
        left_spacing = remaining_space // 2
        right_spacing = remaining_space - left_spacing

        # Build the final layout
        memory_text.append(left_section, style="dim")
        memory_text.append(" " * left_spacing)
        memory_text.append(center_section, style="dim")
        memory_text.append(" " * right_spacing)
        memory_text.append(right_section, style="dim")

        return memory_text
