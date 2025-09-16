"""
Tests for Config class.
"""

import os
from unittest.mock import patch

import pytest

from todo_agent.infrastructure.config import Config


class TestConfig:
    """Test Config functionality."""

    def test_default_initialization(self):
        """Test default configuration initialization."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()

            assert config.provider == "openrouter"
            assert config.openrouter_model == "openai/gpt-4o-mini"
            assert config.ollama_base_url == "http://localhost:11434"
            assert config.ollama_model == "gpt-oss:20b"
            assert config.model == "openai/gpt-4o-mini"  # default for openrouter
            assert config.log_level == "INFO"
            assert config.todo_file_path == "todo.txt"

    def test_openrouter_provider_configuration(self):
        """Test OpenRouter provider configuration."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "openrouter",
                "OPENROUTER_MODEL": "mistralai/mistral-small-3.1-24b-instruct",
                "OPENROUTER_API_KEY": "test-key",
            },
            clear=True,
        ):
            config = Config()

            assert config.provider == "openrouter"
            assert config.openrouter_model == "mistralai/mistral-small-3.1-24b-instruct"
            assert config.model == "mistralai/mistral-small-3.1-24b-instruct"
            assert config.openrouter_api_key == "test-key"

    def test_ollama_provider_configuration(self):
        """Test Ollama provider configuration."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "ollama",
                "OLLAMA_MODEL": "llama3.1",
                "OLLAMA_BASE_URL": "http://localhost:8080",
            },
            clear=True,
        ):
            config = Config()

            assert config.provider == "ollama"
            assert config.ollama_model == "llama3.1"
            assert config.ollama_base_url == "http://localhost:8080"
            assert config.model == "llama3.1"

    def test_get_model_for_provider_openrouter(self):
        """Test getting model for OpenRouter provider."""
        config = Config()
        config.provider = "openrouter"
        config.openrouter_model = "test-model"

        model = config._get_model_for_provider()
        assert model == "test-model"

    def test_get_model_for_provider_ollama(self):
        """Test getting model for Ollama provider."""
        config = Config()
        config.provider = "ollama"
        config.ollama_model = "test-model"

        model = config._get_model_for_provider()
        assert model == "test-model"

    def test_get_model_for_provider_unknown(self):
        """Test getting model for unknown provider (fallback)."""
        config = Config()
        config.provider = "unknown"
        config.openrouter_model = "fallback-model"

        model = config._get_model_for_provider()
        assert model == "fallback-model"

    def test_validate_openrouter_with_api_key(self):
        """Test validation for OpenRouter with API key."""
        config = Config()
        config.provider = "openrouter"
        config.openrouter_api_key = "test-key"

        result = config.validate()
        assert result is True

    def test_validate_openrouter_without_api_key(self):
        """Test validation for OpenRouter without API key."""
        config = Config()
        config.provider = "openrouter"
        config.openrouter_api_key = None

        with pytest.raises(
            ValueError,
            match="OPENROUTER_API_KEY environment variable is required for OpenRouter provider",
        ):
            config.validate()

    def test_validate_ollama(self):
        """Test validation for Ollama provider."""
        config = Config()
        config.provider = "ollama"

        result = config.validate()
        assert result is True

    def test_validate_unsupported_provider(self):
        """Test validation for unsupported provider."""
        config = Config()
        config.provider = "unsupported"

        with pytest.raises(ValueError, match="Unsupported LLM provider: unsupported"):
            config.validate()

    def test_todo_dir_property(self):
        """Test todo_dir property."""
        config = Config()
        config.todo_file_path = "/path/to/todo.txt"

        assert config.todo_dir == "/path/to"

    def test_done_file_path_property(self):
        """Test done_file_path property."""
        config = Config()
        config.todo_file_path = "/path/to/todo.txt"

        assert config.done_file_path == "/path/to/done.txt"
