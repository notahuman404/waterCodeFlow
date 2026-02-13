"""
CLI argument parsing and validation for CodeVovle.

Provides:
- Argument parser with subcommands (record, revert, branch, insights, status)
- Enforcement of --file parameter on all commands
- File path validation (must be inside CodeVovle directory)
- Clean error messages
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional


class CLIError(Exception):
    """CLI argument or validation error."""
    pass


def validate_cwd() -> None:
    """
    Validate that the current working directory is 'CodeVovle'.
    
    Raises:
        CLIError: If CWD is not named 'CodeVovle'
    """
    cwd = os.getcwd()
    cwd_basename = os.path.basename(cwd)
    
    if cwd_basename != "CodeVovle":
        raise CLIError(
            f"Error: CodeVovle CLI must be run from a directory named 'CodeVovle'\n"
            f"Current directory: {cwd}\n"
            f"Please navigate to your CodeVovle project directory and try again."
        )


def validate_file_path(file_path: str) -> Path:
    """
    Validate that a file path is inside the CodeVovle directory.
    
    Args:
        file_path: File path to validate
        
    Returns:
        Absolute Path object
        
    Raises:
        CLIError: If path is outside CodeVovle directory
    """
    cwd = Path.cwd()
    target = Path(file_path).resolve()
    
    # Check if target is inside cwd
    try:
        target.relative_to(cwd)
    except ValueError:
        raise CLIError(
            f"Error: File path must be inside the CodeVovle directory\n"
            f"Target: {target}\n"
            f"CodeVovle directory: {cwd}"
        )
    
    return target


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create the main argument parser with all subcommands.
    
    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="codevovle",
        description="Multi-file code timeline tracking CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Recording and basic operations
  codevovle record --file src/main.py --interval 5
  codevovle revert --file src/main.py --at 5
  codevovle status --file src/main.py

  # Hierarchical branching
  codevovle branch create --file src/main.py main/feature
  codevovle branch create --file src/main.py main/feature/sub-feature
  codevovle branch jump --file src/main.py main/feature
  codevovle branch list --file src/main.py --parent main
  codevovle branch rename --file src/main.py main/feature feature2
  codevovle branch delete --file src/main.py main/feature

  # AI insights with hierarchical paths
  codevovle insights --file src/main.py --from main@1 --to main@5
  codevovle insights --file src/main.py --from main/feature@1 --to main/feature@10
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # record command
    record_parser = subparsers.add_parser("record", help="Start/resume interval recording")
    record_parser.add_argument("--file", required=True, help="File path to record")
    record_parser.add_argument("--interval", type=float, required=True, help="Interval duration (seconds)")
    record_parser.add_argument("--out", help="Output directory for diffs (optional)")
    record_parser.add_argument("--profile", action="store_true", help="Enable performance profiling")
    record_parser.add_argument("--threads", type=int, help="Number of threads to use (internal use, set via daemon set-threads)")
    # Internal flag used when record is launched by the daemon manager
    record_parser.add_argument("--daemonized", action="store_true", help=argparse.SUPPRESS)
    
    # revert command
    revert_parser = subparsers.add_parser("revert", help="Revert file to a specific tick")
    revert_parser.add_argument("--file", required=True, help="File path to revert")
    revert_parser.add_argument("--at", required=True, help="Tick ID to revert to")
    
    # branch commands
    branch_parser = subparsers.add_parser("branch", help="Manage branches")
    branch_subparsers = branch_parser.add_subparsers(dest="branch_command", help="Branch subcommands")
    
    # branch list
    branch_list = branch_subparsers.add_parser("list", help="List all branches (hierarchical)")
    branch_list.add_argument("--file", required=True, help="File path")
    branch_list.add_argument("--parent", help="Parent branch to list children (optional)")
    
    # branch create
    branch_create = branch_subparsers.add_parser("create", help="Create a new branch (supports nesting)")
    branch_create.add_argument("--file", required=True, help="File path")
    branch_create.add_argument("branch", help="Branch name or path (e.g., 'main/feature' or 'main/feature/sub')")
    
    # branch rename
    branch_rename = branch_subparsers.add_parser("rename", help="Rename a branch (short name)")
    branch_rename.add_argument("--file", required=True, help="File path")
    branch_rename.add_argument("branch", help="Current branch path (e.g., 'main/feature')")
    branch_rename.add_argument("new_name", help="New short name (e.g., 'feature2')")
    
    # branch delete
    branch_delete = branch_subparsers.add_parser("delete", help="Delete a branch and its children")
    branch_delete.add_argument("--file", required=True, help="File path")
    branch_delete.add_argument("branch", help="Branch path to delete (e.g., 'main/feature')")
    
    # branch jump
    branch_jump = branch_subparsers.add_parser("jump", help="Switch to a different branch")
    branch_jump.add_argument("--file", required=True, help="File path")
    branch_jump.add_argument("branch", help="Branch path to switch to (e.g., 'main/feature')")
    
    # insights command
    insights_parser = subparsers.add_parser("insights", help="Generate AI insights from code changes")
    insights_parser.add_argument("--file", required=True, help="File path")
    insights_parser.add_argument("--from", dest="from_spec", required=True, help="From tick (e.g., 'main@5', 'main/feature@7', or '5')")
    insights_parser.add_argument("--to", dest="to_spec", required=True, help="To tick (e.g., 'main@10', 'main/feature/sub@12', or '10')")
    insights_parser.add_argument("--model", choices=["gemini", "chatgpt", "claude"], default="gemini", help="AI model to use (default: gemini)")
    
    # status command
    status_parser = subparsers.add_parser("status", help="Show current tracking status")
    status_parser.add_argument("--file", required=True, help="File path")
    
    # daemon commands
    daemon_parser = subparsers.add_parser("daemon", help="Manage background recording")
    daemon_subparsers = daemon_parser.add_subparsers(dest="daemon_command", help="Daemon subcommands")
    
    # daemon start
    daemon_start = daemon_subparsers.add_parser("start", help="Start background recording")
    daemon_start.add_argument("--file", required=True, help="File path to record")
    daemon_start.add_argument("--interval", type=float, required=True, help="Interval duration (seconds)")
    
    # daemon set-threads
    daemon_set_threads = daemon_subparsers.add_parser("set-threads", help="Set number of threads for daemon processing")
    daemon_set_threads.add_argument("--count", type=int, required=True, help="Number of threads to use (min: 1, max: 32)")
    
    # daemon stop
    daemon_stop = daemon_subparsers.add_parser("stop", help="Stop background recording")
    daemon_stop.add_argument("--file", required=True, help="File path to stop recording")
    
    # daemon status
    daemon_status = daemon_subparsers.add_parser("status", help="Show daemon status")
    daemon_status.add_argument("--file", help="File path (optional, shows all if not specified)")
    
    # daemon get-threads
    daemon_get_threads = daemon_subparsers.add_parser("get-threads", help="Get current thread configuration")
    
    # daemon list
    daemon_list = daemon_subparsers.add_parser("list", help="List all running daemons")
    
    # daemon stop-all
    daemon_stop_all = daemon_subparsers.add_parser("stop-all", help="Stop all running daemons")
    
    return parser


def parse_args(args: Optional[list] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Args:
        args: List of arguments to parse (defaults to sys.argv[1:])
        
    Returns:
        Parsed arguments
        
    Raises:
        CLIError: If arguments are invalid
    """
    parser = create_argument_parser()
    
    try:
        parsed = parser.parse_args(args)
    except SystemExit as e:
        if e.code != 0:
            raise CLIError("Invalid arguments")
        sys.exit(0)
    
    # Check that a command was provided
    if not parsed.command:
        parser.print_help()
        raise CLIError("No command specified")
    
    # Validate branch subcommand if branch command was used
    if parsed.command == "branch" and not parsed.branch_command:
        parser.parse_args([parsed.command, "-h"])
        raise CLIError("No branch subcommand specified")
    
    # Validate daemon subcommand if daemon command was used
    if parsed.command == "daemon" and not parsed.daemon_command:
        parser.parse_args([parsed.command, "-h"])
        raise CLIError("No daemon subcommand specified")
    
    return parsed
