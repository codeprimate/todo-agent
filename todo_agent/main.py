#!/usr/bin/env python3
"""
Main entry point for todo.sh LLM agent.
"""

import argparse
import sys

from .interface.cli import CLI


def main() -> None:
    """Main application entry point."""
    from ._version import __version__
    
    parser = argparse.ArgumentParser(
        description=f"Todo.sh LLM Agent - Natural language task management (v{__version__})",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
        epilog="""
Examples:
  todo-agent                    # Interactive mode
  todo-agent "add buy groceries"  # Single command mode
  todo-agent "list my tasks"    # List all tasks
  todo-agent "complete task 3"  # Complete specific task
        """,
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show version information and exit",
    )
    
    parser.add_argument(
        "--help", "-h",
        action="help",
        help="Show this help message and exit",
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
            # Handle special commands that don't need LLM processing
            if args.command.lower() in ["help", "about"]:
                if args.command.lower() == "help":
                    cli._print_help()
                elif args.command.lower() == "about":
                    cli._print_about()
            else:
                # Process through LLM
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
