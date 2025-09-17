"""
Configuration management for todo.sh LLM agent.
"""

import os


class Config:
    """Environment and configuration management."""

    DEFAULT_MODEL = "openai/gpt-4o-mini"
    # DEFAULT_MODEL = "mistralai/mistral-small-3.1-24b-instruct"

    def __init__(self) -> None:
        # Provider selection
        self.provider = os.getenv("LLM_PROVIDER", "openrouter")

        # OpenRouter configuration
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", self.DEFAULT_MODEL)

        # Ollama configuration
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")

        # Common configuration
        self.model = self._get_model_for_provider()
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.todo_file_path = os.getenv("TODO_FILE", "todo.txt")

        # Model parameters
        self.reasoning_effort = os.getenv("REASONING_EFFORT", "low")

        # UI/UX parameters
        self.use_mini_prompt = False

    def _get_model_for_provider(self) -> str:
        """Get model name for current provider."""
        if self.provider == "openrouter":
            return self.openrouter_model
        elif self.provider == "ollama":
            return self.ollama_model
        return self.openrouter_model  # fallback

    def validate(self) -> bool:
        """Validate required configuration."""
        if self.provider == "openrouter":
            if not self.openrouter_api_key:
                raise ValueError(
                    "OPENROUTER_API_KEY environment variable is required for OpenRouter provider"
                )
        elif self.provider == "ollama":
            # Ollama doesn't require API key, but we could validate the base URL is reachable
            pass
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
        return True

    def set_mini_prompt(self, use_mini: bool) -> None:
        """Set the use_mini_prompt flag programmatically (e.g., from command line args)."""
        self.use_mini_prompt = use_mini

    @property
    def todo_dir(self) -> str:
        """Get todo.sh directory path."""
        return os.path.dirname(self.todo_file_path)

    @property
    def done_file_path(self) -> str:
        """Get done.txt file path."""
        return os.path.join(self.todo_dir, "done.txt")
