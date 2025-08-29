#!/usr/bin/env python3
"""
Main entry point for todo.sh LLM agent.
"""

import argparse
import sys

from .interface.cli import CLI


def main() -> None:
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="Todo.sh LLM Agent - Natural language task management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  todo-agent                    # Interactive mode
  todo-agent "add buy groceries"  # Single command mode
  todo-agent "list my tasks"    # List all tasks
  todo-agent "complete task 3"  # Complete specific task
        """,
    )

    parser.add_argument(
        "command",
        nargs="?",
        help="Single command to execute (optional, defaults to interactive mode)",
    )

    args = parser.parse_args()

    try:
        cli = CLI()

        if args.command:
            # Single command mode
            response = cli.run_single_request(args.command)
            print(response)
        else:
            # Interactive mode
            cli.run()

    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
