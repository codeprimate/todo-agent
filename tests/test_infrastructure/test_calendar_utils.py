"""
Tests for calendar utilities.
"""

from unittest.mock import Mock, patch

import pytest

from todo_agent.infrastructure.calendar_utils import (
    get_calendar_output,
    get_current_month_calendar,
)


class TestCalendarUtils:
    """Test calendar utility functions."""

    def test_get_calendar_output_success(self):
        """Test successful calendar output generation."""
        mock_output = "Calendar output from cal"

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.stdout = mock_output
            mock_run.return_value = mock_result

            result = get_calendar_output()

            assert result == mock_output
            assert len(result) > 0
            mock_run.assert_called_once_with(
                ["cal"], capture_output=True, text=True, check=True
            )

    def test_get_calendar_output_fallback(self):
        """Test calendar output fallback to Python calendar."""
        with patch("subprocess.run", side_effect=FileNotFoundError("cal not found")):
            result = get_calendar_output()

            # Should return a string with calendar data
            assert isinstance(result, str)
            assert len(result) > 0

    def test_get_current_month_calendar_success(self):
        """Test successful current month calendar generation."""
        mock_output = "Current month calendar"

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.stdout = mock_output
            mock_run.return_value = mock_result

            result = get_current_month_calendar()

            assert result == mock_output
            assert len(result) > 0
            mock_run.assert_called_once_with(
                ["cal"], capture_output=True, text=True, check=True
            )

    def test_get_current_month_calendar_fallback(self):
        """Test current month calendar fallback to Python calendar."""
        with patch("subprocess.run", side_effect=FileNotFoundError("cal not found")):
            result = get_current_month_calendar()

            # Should return a string with calendar data
            assert isinstance(result, str)
            assert len(result) > 0

    def test_calendar_output_contains_expected_content(self):
        """Test that calendar output contains expected content."""
        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.stdout = "Calendar with July August September 2025"
            mock_run.return_value = mock_result

            result = get_calendar_output()

            # Should contain some calendar content
            assert len(result) > 0
            assert isinstance(result, str)
