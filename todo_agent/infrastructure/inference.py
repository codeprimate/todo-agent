"""
LLM inference engine for todo.sh agent.
"""

import os
import signal
import time
from datetime import datetime
from typing import Any, Dict, Optional

try:
    from todo_agent.core.conversation_manager import ConversationManager, MessageRole
    from todo_agent.infrastructure.config import Config
    from todo_agent.infrastructure.llm_client_factory import LLMClientFactory
    from todo_agent.infrastructure.logger import Logger
    from todo_agent.interface.formatters import (
        get_provider_error_message as _get_error_msg,
    )
    from todo_agent.interface.progress import NoOpProgress, ToolCallProgress
    from todo_agent.interface.tools import ToolCallHandler
except ImportError:
    from core.conversation_manager import (  # type: ignore[no-redef]
        ConversationManager,
        MessageRole,
    )
    from infrastructure.config import Config  # type: ignore[no-redef]
    from infrastructure.llm_client_factory import (  # type: ignore[no-redef]
        LLMClientFactory,
    )
    from infrastructure.logger import Logger  # type: ignore[no-redef]
    from interface.formatters import (  # type: ignore[no-redef]
        get_provider_error_message as _get_error_msg,
    )
    from interface.progress import (  # type: ignore[no-redef]
        NoOpProgress,
        ToolCallProgress,
    )
    from interface.tools import ToolCallHandler  # type: ignore[no-redef]


class Inference:
    """LLM inference engine that orchestrates tool calling and conversation management."""

    def __init__(
        self,
        config: Config,
        tool_handler: ToolCallHandler,
        logger: Optional[Logger] = None,
    ):
        """
        Initialize the inference engine.

        Args:
            config: Configuration object
            tool_handler: Tool call handler for executing tools
            logger: Optional logger instance
        """
        self.config = config
        self.tool_handler = tool_handler
        self.logger = logger or Logger("inference")
        self.use_mini_prompt = config.use_mini_prompt

        self.llm_client = LLMClientFactory.create_client(config, self.logger)
        self.conversation_manager = ConversationManager()
        self._cancelled = False

        # Set up signal handler for user interruption (Ctrl+C)
        signal.signal(signal.SIGINT, self._handle_interrupt)

        # Set up system prompt
        self._setup_system_prompt()

        self.logger.info(
            f"Inference engine initialized with {config.provider} provider using model: {self.llm_client.get_model_name()}"
        )

    def _handle_interrupt(self, signum: int, frame: Any) -> None:
        """
        Handle user interruption signal (Ctrl+C).

        Args:
            signum: Signal number (should be SIGINT)
            frame: Current stack frame
        """
        self._cancelled = True
        self.logger.info("User interruption signal received (Ctrl+C)")
        # Don't exit immediately - let current operation finish gracefully

    def _handle_cancellation(self, start_time: float) -> tuple[str, float]:
        """
        Handle cancellation by adding "I stopped." message to conversation.

        Args:
            start_time: Request start time for calculating thinking time

        Returns:
            Tuple of (cancellation message, actual thinking time)
        """
        # Calculate actual thinking time
        end_time = time.time()
        thinking_time = end_time - start_time

        self.conversation_manager.add_message(MessageRole.ASSISTANT, "I stopped.")
        self._cancelled = False
        return "I stopped.", thinking_time

    def reset_cancellation_flag(self) -> None:
        """
        Reset the cancellation flag. Call this before starting a new request
        to ensure any previous cancellation state is cleared.
        """
        self._cancelled = False
        self.logger.debug("Cancellation flag reset")

    def _setup_system_prompt(self) -> None:
        """Set up the system prompt for the LLM."""
        system_prompt = self._load_system_prompt()
        self.conversation_manager.set_system_prompt(system_prompt)
        self.logger.debug("System prompt loaded and set")

    def current_tasks(self) -> str:
        """
        Get current tasks from the todo manager.

        Returns:
            Formatted string of current tasks or error message
        """
        try:
            # Use the todo manager from the tool handler to get current tasks
            tasks = self.tool_handler.todo_manager.list_tasks(suppress_color=True)

            # If no tasks found, return a clear message
            if not tasks.strip() or tasks == "No tasks found.":
                return "No current tasks found."

            return tasks

        except Exception as e:
            self.logger.warning(f"Failed to get current tasks: {e!s}")
            return f"Error retrieving current tasks: {e!s}"

    def _load_system_prompt(self) -> str:
        """Load and format the system prompt from file."""
        # Get current datetime for interpolation
        now = datetime.now()
        timezone_info = time.tzname[time.daylight]
        current_datetime = f"{now.strftime('%Y-%m-%d %H:%M:%S')} {timezone_info}"

        # Get calendar output
        from .calendar_utils import get_calendar_output

        try:
            calendar_output = get_calendar_output()
        except Exception as e:
            self.logger.warning(f"Failed to get calendar output: {e!s}")
            calendar_output = "Calendar unavailable"

        # Get current tasks
        current_tasks = self.current_tasks()

        # Load system prompt from file
        prompt_filename = (
            "system_prompt_small.txt" if self.use_mini_prompt else "system_prompt.txt"
        )
        prompt_file_path = os.path.join(
            os.path.dirname(__file__), "prompts", prompt_filename
        )

        try:
            with open(prompt_file_path, encoding="utf-8") as f:
                system_prompt_template = f.read()

            # Format the template with current datetime, calendar, and current tasks
            return system_prompt_template.format(
                current_datetime=current_datetime,
                calendar_output=calendar_output,
                current_tasks=current_tasks,
            )

        except FileNotFoundError:
            self.logger.error(f"System prompt file not found: {prompt_file_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading system prompt: {e!s}")
            raise

    def process_request(
        self,
        user_input: str,
        progress_callback: Optional[ToolCallProgress] = None,
        system_request: bool = False,
    ) -> tuple[str, float]:
        """
        Process a user request through the LLM with tool orchestration.

        Args:
            user_input: Natural language user request
            progress_callback: Optional progress callback for tool call tracking
            system_request: If True, treat the input as a system message instead of user message

        Returns:
            Tuple of (formatted response for user, thinking time in seconds)
        """
        # Start timing the request
        start_time = time.time()

        # Initialize progress callback if not provided
        if progress_callback is None:
            progress_callback = NoOpProgress()

        # Notify progress callback that thinking has started
        progress_callback.on_thinking_start()

        try:
            self.logger.debug(
                f"Starting request processing for: {user_input[:30]}{'...' if len(user_input) > 30 else ''}"
            )

            # Add message to conversation (user or system based on flag)
            message_role = MessageRole.SYSTEM if system_request else MessageRole.USER
            self.conversation_manager.add_message(message_role, user_input)
            self.logger.debug(f"Added {message_role.value} message to conversation")

            # Get conversation history for LLM
            messages = self.conversation_manager.get_messages()
            self.logger.debug(
                f"Retrieved {len(messages)} messages from conversation history"
            )

            # Check for cancellation before LLM API call
            if self._cancelled:
                self.logger.info("Request cancelled before LLM API call")
                return self._handle_cancellation(start_time)

            # Send to LLM with function calling enabled
            self.logger.debug("Sending request to LLM with tools")
            response = self.llm_client.chat_with_tools(
                messages=messages,
                tools=self.tool_handler.tools,
                cancelled=self._cancelled,
            )

            # Check for cancellation after LLM response received
            if self._cancelled:
                self.logger.info("Request cancelled after LLM response received")  # type: ignore
                return self._handle_cancellation(start_time)

            # Check for provider errors
            if response.get("error", False):
                error_type = response.get("error_type", "general_error")
                provider = response.get("provider", "unknown")
                self.logger.error(f"Provider error from {provider}: {error_type}")

                error_message = _get_error_msg(error_type)

                # Add error message to conversation
                self.conversation_manager.add_message(
                    MessageRole.ASSISTANT, error_message
                )

                # Calculate thinking time and return
                end_time = time.time()
                thinking_time = end_time - start_time
                progress_callback.on_thinking_complete(thinking_time)

                return error_message, thinking_time

            # Extract actual token usage from API response
            usage = response.get("usage", {})
            actual_prompt_tokens = usage.get("prompt_tokens", 0)
            actual_completion_tokens = usage.get("completion_tokens", 0)
            actual_total_tokens = usage.get("total_tokens", 0)

            # Update conversation manager with actual token count
            self.conversation_manager.update_request_tokens(actual_prompt_tokens)
            self.logger.debug(
                f"Updated with actual API tokens: prompt={actual_prompt_tokens}, completion={actual_completion_tokens}, total={actual_total_tokens}"
            )

            # Handle multiple tool calls in sequence
            tool_call_count = 0

            while True:
                tool_calls = self.llm_client.extract_tool_calls(response)

                if not tool_calls:
                    break

                tool_call_count += 1
                self.logger.debug(
                    f"Executing tool call sequence #{tool_call_count} with {len(tool_calls)} tools"
                )

                # Notify progress callback of sequence start
                progress_callback.on_sequence_complete(
                    tool_call_count, 0
                )  # We don't know total yet

                # Execute all tool calls and collect results
                tool_results = []
                for i, tool_call in enumerate(tool_calls):
                    # Check for cancellation before each tool execution
                    if self._cancelled:
                        self.logger.info(  # type: ignore
                            f"Request cancelled before tool execution #{i + 1}"
                        )
                        return self._handle_cancellation(start_time)

                    tool_name = tool_call.get("function", {}).get("name", "unknown")
                    tool_call_id = tool_call.get("id", "unknown")
                    self.logger.debug(
                        f"=== TOOL EXECUTION #{i + 1}/{len(tool_calls)} ==="
                    )
                    self.logger.debug(f"Tool: {tool_name}")
                    self.logger.debug(f"Tool Call ID: {tool_call_id}")
                    self.logger.debug(f"Raw tool call: {tool_call}")

                    # Get progress description for the tool
                    progress_description = self._get_tool_progress_description(
                        tool_name, tool_call
                    )

                    # Notify progress callback of tool call start
                    progress_callback.on_tool_call_start(
                        tool_name,
                        progress_description,
                        tool_call_count,
                        0,  # We don't know total yet
                    )

                    result = self.tool_handler.execute_tool(tool_call)

                    # Log tool execution result (success or error)
                    if result.get("error", False):
                        self.logger.warning(
                            f"Tool {tool_name} failed: {result.get('user_message', result.get('output', 'Unknown error'))}"
                        )
                    else:
                        self.logger.debug(f"Tool {tool_name} succeeded")

                    self.logger.debug(f"Tool result: {result}")
                    tool_results.append(result)

                    # Check for cancellation after each tool execution completes
                    if self._cancelled:
                        self.logger.info(  # type: ignore
                            f"Request cancelled after tool execution #{i + 1}"
                        )
                        return self._handle_cancellation(start_time)

                # Check for cancellation before adding tool results to conversation
                if self._cancelled:
                    self.logger.info(  # type: ignore
                        "Request cancelled before adding tool results to conversation"
                    )
                    return self._handle_cancellation(start_time)

                # Add tool call sequence to conversation
                self.conversation_manager.add_tool_call_sequence(
                    tool_calls, tool_results
                )
                self.logger.debug("Added tool call sequence to conversation")

                # Continue conversation with tool results
                messages = self.conversation_manager.get_messages()
                response = self.llm_client.chat_with_tools(
                    messages=messages,
                    tools=self.tool_handler.tools,
                    cancelled=self._cancelled,
                )

                # Check for provider errors in continuation
                if response.get("error", False):
                    error_type = response.get("error_type", "general_error")
                    provider = response.get("provider", "unknown")

                    # Handle cancellation specially
                    if error_type == "cancelled":
                        self.logger.info(
                            f"Request cancelled in continuation from {provider}"
                        )
                        return self._handle_cancellation(start_time)

                    self.logger.error(
                        f"Provider error in continuation from {provider}: {error_type}"
                    )

                    error_message = _get_error_msg(error_type)

                    # Add error message to conversation
                    self.conversation_manager.add_message(
                        MessageRole.ASSISTANT, error_message
                    )

                    # Calculate thinking time and return
                    end_time = time.time()
                    thinking_time = end_time - start_time
                    progress_callback.on_thinking_complete(thinking_time)

                    return error_message, thinking_time

                # Update with actual tokens from subsequent API calls
                usage = response.get("usage", {})
                actual_prompt_tokens = usage.get("prompt_tokens", 0)
                self.conversation_manager.update_request_tokens(actual_prompt_tokens)
                self.logger.debug(
                    f"Updated with actual API tokens after tool calls: prompt={actual_prompt_tokens}"
                )

            # Calculate and log total thinking time
            end_time = time.time()
            thinking_time = end_time - start_time

            # Notify progress callback that thinking is complete
            progress_callback.on_thinking_complete(thinking_time)

            # Add final assistant response to conversation with thinking time
            final_content = self.llm_client.extract_content(response)
            self.conversation_manager.add_message(
                MessageRole.ASSISTANT, final_content, thinking_time=thinking_time
            )

            self.logger.info(
                f"Request completed successfully with {tool_call_count} tool call sequences in {thinking_time:.2f}s"
            )

            # Return final user-facing response and thinking time
            return final_content, thinking_time

        except Exception as e:
            # Calculate and log thinking time even for failed requests
            end_time = time.time()
            thinking_time = end_time - start_time
            self.logger.error(
                f"Error processing request after {thinking_time:.2f}s: {e!s}"
            )
            return f"Error: {e!s}", thinking_time

    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get conversation statistics and summary.

        Returns:
            Dictionary with conversation metrics
        """
        return self.conversation_manager.get_conversation_summary(
            self.tool_handler.tools
        )

    def _get_tool_progress_description(
        self, tool_name: str, tool_call: Dict[str, Any]
    ) -> str:
        """
        Get user-friendly progress description for a tool with parameter interpolation.

        Args:
            tool_name: Name of the tool
            tool_call: The tool call dictionary containing parameters

        Returns:
            Progress description string with interpolated parameters
        """
        tool_def = next(
            (
                t
                for t in self.tool_handler.tools
                if t.get("function", {}).get("name") == tool_name
            ),
            None,
        )

        if tool_def and "progress_description" in tool_def:
            template = tool_def["progress_description"]

            # Extract arguments from tool call
            arguments = tool_call.get("function", {}).get("arguments", {})
            if isinstance(arguments, str):
                import json

                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}

            # Use .format() like the system prompt does
            try:
                return template.format(**arguments)
            except KeyError as e:
                # If a required parameter is missing, fall back to template
                self.logger.warning(
                    f"Missing parameter {e} for progress description of {tool_name}"
                )
                return template
            except Exception as e:
                self.logger.warning(
                    f"Failed to interpolate progress description for {tool_name}: {e}"
                )
                return template

        # Fallback to generic description
        return f"🔧 Executing {tool_name}..."

    def clear_conversation(self) -> None:
        """Clear conversation history."""
        self.conversation_manager.clear_conversation()
        self.logger.info("Conversation history cleared")

    def add_system_message(self, content: str) -> None:
        """
        Add a system message to the conversation.

        Args:
            content: The system message content
        """
        self.conversation_manager.add_message(MessageRole.SYSTEM, content)

    def add_user_message(self, content: str) -> None:
        """
        Add a user message to the conversation.

        Args:
            content: The user message content
        """
        self.conversation_manager.add_message(MessageRole.USER, content)

    def get_conversation_manager(self) -> ConversationManager:
        """
        Get the conversation manager instance.

        Returns:
            Conversation manager instance
        """
        return self.conversation_manager
