"""
Formatters for CLI output with unicode characters and consistent styling.
"""

from typing import List, Dict, Any, Optional
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich.box import ROUNDED
from rich.align import Align

# CLI width configuration
CLI_WIDTH = 100
PANEL_WIDTH = CLI_WIDTH - 2  # Leave 2 characters for borders


class TaskFormatter:
    """Formats task-related output with unicode characters and consistent styling."""
    
    @staticmethod
    def format_task_list(raw_tasks: str, title: str = "📋 Tasks") -> str:
        """
        Format a raw task list with unicode characters and numbering.
        
        Args:
            raw_tasks: Raw task output from todo.sh
            title: Title for the task list
            
        Returns:
            Formatted task list string
        """
        if not raw_tasks.strip():
            return "No tasks found."
        
        lines = raw_tasks.strip().split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines, 1):
            if line.strip():
                # Parse todo.txt format and make it more readable
                formatted_task = TaskFormatter._format_single_task(line.strip(), i)
                formatted_lines.append(formatted_task)
        
        if formatted_lines:
            return "\n".join(formatted_lines)
        else:
            return "No tasks found."
    
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
        # Extract priority if present
        priority = ""
        description = task_line
        
        if task_line.startswith("(") and ")" in task_line:
            priority_end = task_line.find(")")
            priority = task_line[1:priority_end]
            description = task_line[priority_end + 1:].strip()
        
        # Format with unicode characters
        if priority:
            return f"  {task_number:2d} │ {priority} │ {description}"
        else:
            return f"  {task_number:2d} │   │ {description}"
    
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
        
        lines = raw_projects.strip().split('\n')
        formatted_lines = []
        
        for i, project in enumerate(lines, 1):
            if project.strip():
                # Remove the + prefix and format nicely
                clean_project = project.strip().lstrip('+')
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
        
        lines = raw_contexts.strip().split('\n')
        formatted_lines = []
        
        for i, context in enumerate(lines, 1):
            if context.strip():
                # Remove the @ prefix and format nicely
                clean_context = context.strip().lstrip('@')
                formatted_lines.append(f"  {i:2d} │ {clean_context}")
        
        if formatted_lines:
            return "\n".join(formatted_lines)
        else:
            return "No contexts found."


class ResponseFormatter:
    """Formats LLM responses and other output with consistent styling."""
    
    @staticmethod
    def format_response(response: str, title: str = "🤖 Assistant") -> str:
        """
        Format an LLM response with consistent styling.
        
        Args:
            response: Raw response text
            title: Title for the response panel
            
        Returns:
            Formatted response string
        """
        # If response contains task lists, format them nicely
        if "No tasks found" in response or "1." in response:
            # This might be a task list response, try to format it
            lines = response.split('\n')
            formatted_lines = []
            
            for line in lines:
                if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                    # This looks like a numbered task list, format it
                    parts = line.split('.', 1)
                    if len(parts) == 2:
                        number = parts[0].strip()
                        content = parts[1].strip()
                        formatted_lines.append(f"  {number:>2} │ {content}")
                    else:
                        formatted_lines.append(line)
                else:
                    formatted_lines.append(line)
            
            return "\n".join(formatted_lines)
        
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
            lines = overview.split('\n')
            formatted_lines = []
            
            for line in lines:
                if line.startswith('- Active tasks:'):
                    formatted_lines.append(f"📋 {line[2:]}")
                elif line.startswith('- Completed tasks:'):
                    formatted_lines.append(f"✅ {line[2:]}")
                else:
                    formatted_lines.append(line)
            
            return "\n".join(formatted_lines)
        
        return overview


class TableFormatter:
    """Creates rich tables for various data displays."""
    
    @staticmethod
    def create_command_table() -> Table:
        """Create a table for displaying available commands."""
        table = Table(
            title="Available Commands",
            box=ROUNDED,
            show_header=True,
            header_style="bold magenta",
            width=PANEL_WIDTH
        )
        
        table.add_column("Command", style="cyan", width=12)
        table.add_column("Description", style="white")
        
        commands = [
            ("clear", "Clear conversation history"),
            ("stats", "Show conversation statistics"),
            ("help", "Show this help message"),
            ("list", "List all tasks (no LLM interaction)"),
            ("quit", "Exit the application"),
        ]
        
        for cmd, desc in commands:
            table.add_row(cmd, desc)
        
        return table
    
    @staticmethod
    def create_stats_table(summary: Dict[str, Any]) -> Table:
        """Create a table for displaying conversation statistics."""
        table = Table(
            title="Conversation Statistics",
            box=ROUNDED,
            show_header=True,
            header_style="bold magenta",
            width=PANEL_WIDTH
        )
        
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="white")
        
        # Basic stats
        table.add_row("Total Messages", str(summary['total_messages']))
        table.add_row("User Messages", str(summary['user_messages']))
        table.add_row("Assistant Messages", str(summary['assistant_messages']))
        table.add_row("Tool Messages", str(summary['tool_messages']))
        table.add_row("Estimated Tokens", str(summary['estimated_tokens']))
        
        # Thinking time stats if available
        if "thinking_time_count" in summary and summary["thinking_time_count"] > 0:
            table.add_row("", "")  # Empty row for spacing
            table.add_row("Total Thinking Time", f"{summary['total_thinking_time']:.2f}s")
            table.add_row("Average Thinking Time", f"{summary['average_thinking_time']:.2f}s")
            table.add_row("Min Thinking Time", f"{summary['min_thinking_time']:.2f}s")
            table.add_row("Max Thinking Time", f"{summary['max_thinking_time']:.2f}s")
            table.add_row("Requests with Timing", str(summary['thinking_time_count']))
        
        return table


class PanelFormatter:
    """Creates rich panels for various content displays."""
    
    @staticmethod
    def create_header_panel() -> Panel:
        """Create the application header panel."""
        header_text = Text("Todo.sh LLM Agent", style="bold blue")
        return Panel(
            Align.center(header_text),
            title="🤖",
            border_style="blue",
            box=ROUNDED,
            width=PANEL_WIDTH+2
        )
    
    @staticmethod
    def create_task_panel(content: str, title: str = "📋 Current Tasks") -> Panel:
        """Create a panel for displaying task lists."""
        return Panel(
            content,
            title=title,
            border_style="green",
            box=ROUNDED,
            width=PANEL_WIDTH
        )
    
    @staticmethod
    def create_response_panel(content: str, title: str = "🤖 Assistant") -> Panel:
        """Create a panel for displaying LLM responses."""
        return Panel(
            content,
            title=title,
            border_style="blue",
            box=ROUNDED,
            width=PANEL_WIDTH
        )
    
    @staticmethod
    def create_error_panel(content: str, title: str = "❌ Error") -> Panel:
        """Create a panel for displaying errors."""
        return Panel(
            content,
            title=title,
            border_style="red",
            box=ROUNDED,
            width=PANEL_WIDTH
        )
