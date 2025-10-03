"""
Command-line interface for todo.sh LLM agent.
"""

import os
import readline
from datetime import datetime
from typing import Optional

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

try:
    from todo_agent.core.todo_manager import TodoManager
    from todo_agent.infrastructure.config import Config
    from todo_agent.infrastructure.inference import Inference
    from todo_agent.infrastructure.logger import Logger
    from todo_agent.infrastructure.todo_shell import TodoShell
    from todo_agent.interface.formatters import (
        CLI_WIDTH,
        PanelFormatter,
        ResponseFormatter,
        TaskFormatter,
    )
    from todo_agent.interface.progress import ToolCallProgress
    from todo_agent.interface.tools import ToolCallHandler
except ImportError:
    from core.todo_manager import TodoManager  # type: ignore[no-redef]
    from infrastructure.config import Config  # type: ignore[no-redef]
    from infrastructure.inference import Inference  # type: ignore[no-redef]
    from infrastructure.logger import Logger  # type: ignore[no-redef]
    from infrastructure.todo_shell import TodoShell  # type: ignore[no-redef]
    from interface.formatters import (  # type: ignore[no-redef]
        CLI_WIDTH,
        PanelFormatter,
        ResponseFormatter,
        TaskFormatter,
    )
    from interface.progress import ToolCallProgress  # type: ignore[no-redef]
    from interface.tools import ToolCallHandler  # type: ignore[no-redef]


class CLI:
    """User interaction loop and input/output handling."""

    def __init__(self) -> None:
        # Initialize readline for arrow key navigation
        readline.set_history_length(50)  # Match existing conversation cap

        # Initialize logger first
        self.logger = Logger("cli")
        self.logger.info("Initializing CLI")

        self.config = Config()
        self.config.validate()
        self.logger.debug("Configuration validated")

        # Initialize infrastructure
        self.todo_shell = TodoShell(self.config.todo_file_path, self.logger)
        self.logger.debug("Infrastructure components initialized")

        # Initialize core
        self.todo_manager = TodoManager(self.todo_shell)
        self.logger.debug("Core components initialized")

        # Initialize interface
        self.tool_handler = ToolCallHandler(self.todo_manager, self.logger)
        self.logger.debug("Interface components initialized")

        # Initialize inference engine
        self.inference = Inference(self.config, self.tool_handler, self.logger)
        self.logger.debug("Inference engine initialized")

        # Initialize rich console for animations with consistent width and color support
        self.console = Console(width=CLI_WIDTH, color_system="auto")

        self.logger.info("CLI initialization completed")

    def _load_review_prompt(self) -> str:
        """Load the review prompt from file."""
        prompt_file_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "infrastructure",
            "prompts",
            "review_prompt.txt",
        )

        try:
            with open(prompt_file_path, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(f"Review prompt file not found: {prompt_file_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading review prompt: {e!s}")
            raise

    def _create_thinking_spinner(self, message: str = "Thinking...") -> Spinner:
        """
        Create a thinking spinner with the given message.

        Args:
            message: The message to display alongside the spinner

        Returns:
            Spinner object ready for display
        """
        return Spinner("dots", text=Text(message, style="cyan"))

    def _get_thinking_live(self) -> Live:
        """
        Create a live display context for the thinking spinner.

        Returns:
            Live display context manager
        """
        initial_spinner = self._create_thinking_spinner("Thinking...")
        return Live(initial_spinner, console=self.console, refresh_per_second=10)

    def _create_tool_call_spinner(
        self, progress_description: str, sequence: int = 0, total_sequences: int = 0
    ) -> Group:
        """
        Create a multi-line spinner showing tool call progress.

        Args:
            progress_description: User-friendly description of what the tool is doing
            sequence: Current sequence number
            total_sequences: Total number of sequences

        Returns:
            Group object with spinner and optional sequence info
        """
        # Line 1: Main progress with spinner
        main_line = Spinner("dots", text=Text(progress_description, style="cyan"))

        # Line 2: Sequence progress (show current sequence even if we don't know total)
        # if sequence > 0:
        #     if total_sequences > 0:
        #         sequence_text = Text(f"Sequence {sequence}/{total_sequences}", style="dim")
        #     else:
        #         sequence_text = Text(f"Sequence {sequence}", style="dim")
        #     return Group(main_line, sequence_text)

        return Group(main_line)

    def _create_completion_spinner(self, thinking_time: float) -> Spinner:
        """
        Create completion spinner with timing.

        Args:
            thinking_time: Total thinking time in seconds

        Returns:
            Spinner object showing completion
        """
        return Spinner(
            "dots", text=Text(f"✅ Complete ({thinking_time:.1f}s)", style="green")
        )

    def _create_cli_progress_callback(self, live_display: Live) -> ToolCallProgress:
        """
        Create a CLI-specific progress callback for tool call tracking.

        Args:
            live_display: The live display to update

        Returns:
            ToolCallProgress implementation for CLI
        """

        class CLIProgressCallback(ToolCallProgress):
            def __init__(self, cli: CLI, live: Live):
                self.cli = cli
                self.live = live
                self.current_sequence = 0
                self.total_sequences = 0

            def on_thinking_start(self) -> None:
                """Show initial thinking spinner."""
                spinner = self.cli._create_thinking_spinner(
                    "🤔 Analyzing your request..."
                )
                self.live.update(spinner)

            def on_tool_call_start(
                self,
                tool_name: str,
                progress_description: str,
                sequence: int,
                total_sequences: int,
            ) -> None:
                """Show tool execution progress."""
                self.current_sequence = sequence
                self.total_sequences = total_sequences

                # Create multi-line spinner
                spinner = self.cli._create_tool_call_spinner(
                    progress_description=progress_description,
                    sequence=sequence,
                    total_sequences=total_sequences,
                )
                self.live.update(spinner)

            def on_tool_call_complete(
                self, tool_name: str, success: bool, duration: float
            ) -> None:
                """Tool completion - no action needed."""
                pass

            def on_sequence_complete(self, sequence: int, total_sequences: int) -> None:
                """Show sequence completion."""
                spinner = self.cli._create_tool_call_spinner(
                    progress_description=f"🔄 Sequence {sequence} complete",
                    sequence=sequence,
                    total_sequences=total_sequences,
                )
                self.live.update(spinner)

            def on_thinking_complete(self, total_time: float) -> None:
                """Show completion spinner."""
                spinner = self.cli._create_completion_spinner(total_time)
                self.live.update(spinner)

        return CLIProgressCallback(self, live_display)

    def _print_header(self) -> None:
        """Print the application header with unicode borders."""
        header_panel = PanelFormatter.create_header_panel()
        self.console.print(header_panel)

        subtitle = Text(
            "Type your request naturally, or enter 'quit' to exit, or 'help' for commands",
            style="dim",
        )
        self.console.print(Align.center(subtitle), style="dim")

    def _print_help(self) -> None:
        """Print help information in a formatted panel."""
        help_panel = PanelFormatter.create_help_panel()
        self.console.print(help_panel)

    def _print_todo_help(self) -> None:
        """Print todo.sh help information."""
        try:
            # Get todo.sh help output
            help_output = self.todo_shell.get_help()
            formatted_output = TaskFormatter.format_task_list(help_output)
            help_panel = PanelFormatter.create_task_panel(
                formatted_output, title="📋 Todo.sh Help"
            )
            self.console.print(help_panel)
        except Exception as e:
            self.logger.error(f"Error getting todo.sh help: {e!s}")
            error_msg = ResponseFormatter.format_error(
                f"Failed to get todo.sh help: {e!s}"
            )
            self.console.print(error_msg)

    def _print_about(self) -> None:
        """Print about information in a formatted panel."""
        about_panel = PanelFormatter.create_about_panel()
        self.console.print(about_panel)

    def _get_memory_usage(self) -> Optional[Text]:
        """Get session memory usage as a progress bar."""
        # Get conversation manager to access memory limits and current usage
        conversation_manager = self.inference.get_conversation_manager()

        # Get current usage from conversation summary
        summary = self.inference.get_conversation_summary()
        current_tokens = summary.get("request_tokens", 0)  # Use request_tokens
        current_messages = summary.get("total_messages", 0)

        # Get limits from conversation manager
        max_tokens = conversation_manager.max_tokens
        max_messages = conversation_manager.max_messages

        # Create memory usage bar
        memory_bar = PanelFormatter.create_memory_usage_bar(
            current_tokens, max_tokens, current_messages, max_messages
        )

        return memory_bar

    def run(self) -> None:
        """Main CLI interaction loop."""
        self.logger.info("Starting CLI interaction loop")

        # Print header
        self._print_header()

        # Print separator
        self.console.print("─" * CLI_WIDTH, style="dim")

        # Prime conversation with today's date
        today = datetime.now()
        self.inference.add_user_message(f"Today is {today.strftime('%A, %Y-%m-%d')}.")

        while True:
            try:
                # Print prompt character on separate line to prevent deletion
                self.console.print("\n[bold cyan]▶[/bold cyan]", end=" ")
                user_input = self.console.input().strip()
            except KeyboardInterrupt:
                self.logger.info("User interrupted with Ctrl+C at prompt")
                self.console.print("\n[bold green]Goodbye! 👋[/bold green]")
                break
            except EOFError:
                self.logger.info("Input stream ended (EOF)")
                self.console.print("\n[bold green]Goodbye! 👋[/bold green]")
                break

            try:
                if user_input.lower() in ["quit", "exit", "q"]:
                    self.logger.info("User requested exit")
                    self.console.print("\n[bold green]Goodbye! 👋[/bold green]")
                    break

                if not user_input:
                    continue

                # Handle todo.sh passthrough commands (starting with /)
                if user_input.startswith("/"):
                    self.logger.debug(
                        f"Processing todo.sh passthrough command: {user_input}"
                    )
                    try:
                        # Remove the leading / and execute as todo.sh command
                        todo_command = user_input[1:].strip()
                        if not todo_command:
                            self.console.print(
                                ResponseFormatter.format_error("Empty todo.sh command")
                            )
                            continue

                        # Execute the todo.sh command directly
                        output = self.todo_shell.execute(
                            ["todo.sh", *todo_command.split()]
                        )
                        formatted_output = TaskFormatter.format_task_list(output)
                        task_panel = PanelFormatter.create_task_panel(
                            formatted_output, title="📋 Todo.sh Output"
                        )
                        self.console.print(task_panel)
                    except Exception as e:
                        self.logger.error(f"Error executing todo.sh command: {e!s}")
                        error_msg = ResponseFormatter.format_error(
                            f"Todo.sh command failed: {e!s}"
                        )
                        self.console.print(error_msg)
                    continue

                # Handle special commands
                if user_input.lower() == "clear":
                    self.logger.info("User requested conversation clear")
                    self.inference.clear_conversation()
                    self.console.print(
                        ResponseFormatter.format_success(
                            "Conversation history cleared."
                        )
                    )
                    continue

                if user_input.lower() == "help":
                    self.logger.debug("User requested help")
                    self._print_help()
                    continue

                if user_input.lower() == "todo-help":
                    self.logger.debug("User requested todo.sh help")
                    self._print_todo_help()
                    continue

                if user_input.lower() == "about":
                    self.logger.debug("User requested about information")
                    self._print_about()
                    continue

                if user_input.lower() == "list":
                    self.logger.debug("User requested task list")
                    try:
                        # Use suppress_color=False for interactive display to preserve colors
                        output = self.todo_shell.list_tasks(suppress_color=False)
                        formatted_output = TaskFormatter.format_task_list(output)
                        task_panel = PanelFormatter.create_task_panel(formatted_output)
                        self.console.print(task_panel)
                    except Exception as e:
                        self.logger.error(f"Error listing tasks: {e!s}")
                        error_msg = ResponseFormatter.format_error(
                            f"Failed to list tasks: {e!s}"
                        )
                        self.console.print(error_msg)
                    continue

                if user_input.lower() == "done":
                    self.logger.debug("User requested completed task list")
                    try:
                        # Use suppress_color=False for interactive display to preserve colors
                        output = self.todo_shell.list_completed(suppress_color=False)
                        formatted_output = TaskFormatter.format_completed_tasks(output)
                        task_panel = PanelFormatter.create_task_panel(
                            formatted_output, title="✅ Completed Tasks"
                        )
                        self.console.print(task_panel)
                    except Exception as e:
                        self.logger.error(f"Error listing completed tasks: {e!s}")
                        error_msg = ResponseFormatter.format_error(
                            f"Failed to list completed tasks: {e!s}"
                        )
                        self.console.print(error_msg)
                    continue

                self.logger.info(
                    f"Processing user request: {user_input[:50]}{'...' if len(user_input) > 50 else ''}"
                )

                # This is a natural language request

                # Perform the first pass of the response
                response = self.handle_request(user_input)

                # Second pass: provide the best possible response as if this is the first answer
                # review_prompt = self._load_review_prompt()
                # response = self.handle_request(review_prompt, system_request=True)

                # Format the response and create a panel
                formatted_response = ResponseFormatter.format_response(response)

                # Get memory usage
                # memory_usage = self._get_memory_usage()
                memory_usage = None

                # Create response panel with memory usage
                response_panel = PanelFormatter.create_response_panel(
                    formatted_response, memory_usage=memory_usage
                )
                self.console.print(response_panel)

            except KeyboardInterrupt:
                self.logger.info(
                    "User interrupted with Ctrl+C during request processing"
                )
                self.console.print("\n[bold green]Goodbye! 👋[/bold green]")
                break
            except Exception as e:
                self.logger.error(f"Error processing request: {e!s}")
                error_msg = ResponseFormatter.format_error(str(e))
                self.console.print(error_msg)

    def handle_request(self, user_input: str, system_request: bool = False) -> str:
        """
        Handle user request with LLM-driven tool orchestration and conversation memory.

        Args:
            user_input: Natural language user request
            system_request: If True, treat the input as a system message instead of user message

        Returns:
            Formatted response for user
        """
        # Reset cancellation flag before processing request
        self.inference.reset_cancellation_flag()

        # Show thinking spinner during LLM processing
        with self._get_thinking_live() as live:
            try:
                # Create progress callback for tool call tracking
                progress_callback = self._create_cli_progress_callback(live)

                # First pass: Process user request
                response, thinking_time = self.inference.process_request(
                    user_input, progress_callback, system_request
                )

                # # Second pass: Refine the response
                # review_prompt = self._load_review_prompt()
                # response, thinking_time2 = self.inference.process_request(review_prompt, progress_callback, system_request=True)
                # thinking_time = thinking_time + thinking_time2

                # Update spinner with completion message and thinking time
                live.update(
                    self._create_thinking_spinner(f"(thought for {thinking_time:.1f}s)")
                )

                return response
            except Exception as e:
                # Update spinner with error message
                live.update(self._create_thinking_spinner("Request failed"))

                # Log the error
                self.logger.error(f"Error in handle_request: {e!s}")

                # Return error message
                return ResponseFormatter.format_error(str(e))

    def run_single_request(
        self, input_prompt: str, system_request: bool = False
    ) -> str:
        """
        Run a single request without entering the interactive loop.

        Args:
            user_input: Natural language user request
            system_request: If True, treat the input as a system message instead of user message

        Returns:
            Formatted response
        """
        self.logger.info(
            f"Running single request: {input_prompt[:50]}{'...' if len(input_prompt) > 50 else ''}"
        )
        return self.handle_request(input_prompt, system_request)
