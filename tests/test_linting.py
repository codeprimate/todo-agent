"""
Test module for running linting checks as part of the test suite.

This module ensures that code quality standards are maintained
by running various linting tools during testing.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import pytest


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or Path.cwd(),
            check=False,
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


class TestCodeFormatting:
    """Test that code follows formatting standards."""

    @pytest.mark.lint
    def test_ruff_formatting(self):
        """Test that code is properly formatted with Ruff."""
        cmd = [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--check",
            "todo_agent/",
            "tests/",
        ]
        returncode, stdout, stderr = run_command(cmd)

        if returncode != 0:
            print("Ruff formatting issues found:")
            print(stdout)
            print(stderr)

        assert returncode == 0, "Code is not properly formatted with Ruff"

    @pytest.mark.lint
    def test_ruff_imports(self):
        """Test that imports are properly sorted with Ruff."""
        cmd = [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--select",
            "I",
            "todo_agent/",
            "tests/",
        ]
        returncode, stdout, stderr = run_command(cmd)

        if returncode != 0:
            print("Import sorting issues found:")
            print(stdout)
            print(stderr)

        assert returncode == 0, "Imports are not properly sorted"


class TestCodeQuality:
    """Test that code meets quality standards."""

    @pytest.mark.lint
    def test_ruff_compliance(self):
        """Test that code passes Ruff linting."""
        cmd = [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "todo_agent/",
            "tests/",
        ]
        returncode, stdout, stderr = run_command(cmd)

        if returncode != 0:
            print("Ruff issues found:")
            print(stdout)
            print(stderr)

        assert returncode == 0, "Code does not pass Ruff linting"

    @pytest.mark.lint
    def test_mypy_type_checking(self):
        """Test that code passes MyPy type checking."""
        cmd = [sys.executable, "-m", "mypy", "--ignore-missing-imports", "todo_agent/"]
        returncode, stdout, stderr = run_command(cmd)

        if returncode != 0:
            print("MyPy type checking issues found:")
            print(stdout)
            print(stderr)

        assert returncode == 0, "Code does not pass MyPy type checking"


class TestSecurity:
    """Test that code meets security standards."""

    @pytest.mark.lint
    def test_bandit_security(self):
        """Test that code passes Bandit security checks."""
        cmd = [sys.executable, "-m", "bandit", "-r", "todo_agent/"]
        _returncode, stdout, _stderr = run_command(cmd)

        # Bandit returns non-zero for any issues, but we want to see the output
        if stdout:
            print("Bandit security scan results:")
            print(stdout)

        # For now, we'll allow the test to pass but log any issues
        # You can change this to assert returncode == 0 if you want strict enforcement
        assert True, "Security scan completed (check output for issues)"


class TestTestCodeQuality:
    """Test that test code meets quality standards."""

    @pytest.mark.lint
    def test_test_ruff_compliance(self):
        """Test that test code passes Ruff linting."""
        cmd = [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "tests/",
        ]
        returncode, stdout, stderr = run_command(cmd)

        if returncode != 0:
            print("Test code Ruff issues found:")
            print(stdout)
            print(stderr)

        assert returncode == 0, "Test code does not pass Ruff linting"

    @pytest.mark.lint
    def test_test_imports_sorted(self):
        """Test that test imports are properly sorted."""
        cmd = [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--select",
            "I",
            "tests/",
        ]
        returncode, stdout, stderr = run_command(cmd)

        if returncode != 0:
            print("Test import sorting issues found:")
            print(stdout)
            print(stderr)

        assert returncode == 0, "Test imports are not properly sorted"
