"""
Command-line interface for todo.sh LLM agent.
"""

try:
    from rich.console import Console
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.text import Text

    from todo_agent.core.todo_manager import TodoManager
    from todo_agent.infrastructure.config import Config
    from todo_agent.infrastructure.inference import Inference
    from todo_agent.infrastructure.logger import Logger
    from todo_agent.infrastructure.todo_shell import TodoShell
    from todo_agent.interface.tools import ToolCallHandler
except ImportError:
    from core.todo_manager import TodoManager  # type: ignore[no-redef]
    from infrastructure.config import Config  # type: ignore[no-redef]
    from infrastructure.inference import Inference  # type: ignore[no-redef]
    from infrastructure.logger import Logger  # type: ignore[no-redef]
    from infrastructure.todo_shell import TodoShell  # type: ignore[no-redef]
    from interface.tools import ToolCallHandler  # type: ignore[no-redef]
    from rich.console import Console
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.text import Text


class CLI:
    """User interaction loop and input/output handling."""

    def __init__(self) -> None:
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

        # Initialize rich console for animations
        self.console = Console()

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

    def run(self) -> None:
        """Main CLI interaction loop."""
        self.logger.info("Starting CLI interaction loop")
        print("Todo.sh LLM Agent - Type 'quit' to exit")
        print("Commands: 'clear' (clear conversation), 'history' (show stats), 'help'")
        print("=" * 50)

        while True:
            try:
                user_input = input("\n> ").strip()

                if user_input.lower() in ["quit", "exit", "q"]:
                    self.logger.info("User requested exit")
                    print("Goodbye!")
                    break

                if not user_input:
                    continue

                # Handle special commands
                if user_input.lower() == "clear":
                    self.logger.info("User requested conversation clear")
                    self.inference.clear_conversation()
                    print("Conversation history cleared.")
                    continue

                if user_input.lower() == "history":
                    self.logger.debug("User requested conversation history")
                    summary = self.inference.get_conversation_summary()
                    print(f"Conversation Stats:")
                    print(f"  Total messages: {summary['total_messages']}")
                    print(f"  User messages: {summary['user_messages']}")
                    print(f"  Assistant messages: {summary['assistant_messages']}")
                    print(f"  Tool messages: {summary['tool_messages']}")
                    print(f"  Estimated tokens: {summary['estimated_tokens']}")

                    # Display thinking time statistics if available
                    if (
                        "thinking_time_count" in summary
                        and summary["thinking_time_count"] > 0
                    ):
                        print(f"  Thinking time stats:")
                        print(
                            f"    Total thinking time: {summary['total_thinking_time']:.2f}s"
                        )
                        print(
                            f"    Average thinking time: {summary['average_thinking_time']:.2f}s"
                        )
                        print(
                            f"    Min thinking time: {summary['min_thinking_time']:.2f}s"
                        )
                        print(
                            f"    Max thinking time: {summary['max_thinking_time']:.2f}s"
                        )
                        print(
                            f"    Requests with timing: {summary['thinking_time_count']}"
                        )
                    continue

                if user_input.lower() == "help":
                    self.logger.debug("User requested help")
                    print("Available commands:")
                    print("  clear    - Clear conversation history")
                    print("  history  - Show conversation statistics")
                    print("  help     - Show this help message")
                    print("  list     - List all tasks (no LLM interaction)")
                    print("  quit     - Exit the application")
                    print("  Or just type your request naturally!")
                    continue

                if user_input.lower() == "list":
                    self.logger.debug("User requested task list")
                    try:
                        output = self.todo_shell.list_tasks()
                        print(output)
                    except Exception as e:
                        self.logger.error(f"Error listing tasks: {e!s}")
                        print(f"Error: Failed to list tasks: {e!s}")
                    continue

                self.logger.info(
                    f"Processing user request: {user_input[:50]}{'...' if len(user_input) > 50 else ''}"
                )
                response = self.handle_request(user_input)
                print(response)

            except KeyboardInterrupt:
                self.logger.info("User interrupted with Ctrl+C")
                print("\nGoodbye!")
                break
            except Exception as e:
                self.logger.error(f"Error in CLI loop: {e!s}")
                print(f"Error: {e!s}")

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
                return f"Error: {e!s}"

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
