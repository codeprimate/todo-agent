"""
Command-line interface for todo.sh LLM agent.
"""

try:
    import readline

    from rich.align import Align
    from rich.console import Console
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.text import Text

    from todo_agent.core.todo_manager import TodoManager
    from todo_agent.infrastructure.config import Config
    from todo_agent.infrastructure.inference import Inference
    from todo_agent.infrastructure.logger import Logger
    from todo_agent.infrastructure.todo_shell import TodoShell
    from todo_agent.interface.formatters import (
        CLI_WIDTH,
        PanelFormatter,
        ResponseFormatter,
        TableFormatter,
        TaskFormatter,
    )
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
        TableFormatter,
        TaskFormatter,
    )
    from interface.tools import ToolCallHandler  # type: ignore[no-redef]
    from rich.align import Align
    from rich.console import Console
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.text import Text


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

        # Initialize rich console for animations with consistent width
        self.console = Console(width=CLI_WIDTH)

        self.logger.info("CLI initialization completed")

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
        """Print help information in a formatted table."""
        table = TableFormatter.create_command_table()
        self.console.print(table)
        self.console.print("Or just type your request naturally!", style="italic green")

    def _print_about(self) -> None:
        """Print about information in a formatted panel."""
        about_panel = PanelFormatter.create_about_panel()
        self.console.print(about_panel)

    def _print_stats(self, summary: dict) -> None:
        """Print conversation statistics in a formatted table."""
        table = TableFormatter.create_stats_table(summary)
        self.console.print(table)

    def run(self) -> None:
        """Main CLI interaction loop."""
        self.logger.info("Starting CLI interaction loop")

        # Print header
        self._print_header()

        # Print separator
        self.console.print("─" * CLI_WIDTH, style="dim")

        while True:
            try:
                # Print prompt with unicode character
                user_input = self.console.input("\n[bold cyan]▶[/bold cyan] ").strip()

                if user_input.lower() in ["quit", "exit", "q"]:
                    self.logger.info("User requested exit")
                    self.console.print("\n[bold green]Goodbye! 👋[/bold green]")
                    break

                if not user_input:
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

                if user_input.lower() == "stats":
                    self.logger.debug("User requested conversation stats")
                    summary = self.inference.get_conversation_summary()
                    self._print_stats(summary)
                    continue

                if user_input.lower() == "help":
                    self.logger.debug("User requested help")
                    self._print_help()
                    continue

                if user_input.lower() == "about":
                    self.logger.debug("User requested about information")
                    self._print_about()
                    continue

                if user_input.lower() == "list":
                    self.logger.debug("User requested task list")
                    try:
                        output = self.todo_shell.list_tasks()
                        formatted_output = TaskFormatter.format_task_list(output)

                        # Create a wide console for list output with border
                        wide_console = Console(width=120)

                        # Use a simple approach - just print the content with top and bottom borders
                        wide_console.print("─" * 120, style="green")
                        wide_console.print(formatted_output)
                        wide_console.print("─" * 120, style="green")
                    except Exception as e:
                        self.logger.error(f"Error listing tasks: {e!s}")
                        error_msg = ResponseFormatter.format_error(
                            f"Failed to list tasks: {e!s}"
                        )
                        self.console.print(error_msg)
                    continue

                self.logger.info(
                    f"Processing user request: {user_input[:50]}{'...' if len(user_input) > 50 else ''}"
                )
                response = self.handle_request(user_input)

                # Format the response and create a panel
                formatted_response = ResponseFormatter.format_response(response)
                response_panel = PanelFormatter.create_response_panel(
                    formatted_response
                )
                self.console.print(response_panel)

            except KeyboardInterrupt:
                self.logger.info("User interrupted with Ctrl+C")
                self.console.print("\n[bold green]Goodbye! 👋[/bold green]")
                break
            except Exception as e:
                self.logger.error(f"Error in CLI loop: {e!s}")
                error_msg = ResponseFormatter.format_error(str(e))
                self.console.print(error_msg)

    def handle_request(self, user_input: str) -> str:
        """
        Handle user request with LLM-driven tool orchestration and conversation memory.

        Args:
            user_input: Natural language user request

        Returns:
            Formatted response for user
        """
        # Show thinking spinner during LLM processing
        with self._get_thinking_live() as live:
            try:
                # Process request through inference engine
                response, thinking_time = self.inference.process_request(user_input)

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

    def run_single_request(self, user_input: str) -> str:
        """
        Run a single request without entering the interactive loop.

        Args:
            user_input: Natural language user request

        Returns:
            Formatted response
        """
        self.logger.info(
            f"Running single request: {user_input[:50]}{'...' if len(user_input) > 50 else ''}"
        )
        return self.handle_request(user_input)
