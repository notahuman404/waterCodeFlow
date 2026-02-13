"""
CodeVovle CLI entry point.

Validates CWD, parses arguments, and dispatches to appropriate handlers.
"""

import sys
from codevovle.cli import validate_cwd, parse_args, CLIError
from codevovle.handlers import (
    handle_record,
    handle_revert,
    handle_branch_list,
    handle_branch_create,
    handle_branch_delete,
    handle_branch_rename,
    handle_branch_jump,
    handle_status,
    handle_insights,
    handle_daemon_start,
    handle_daemon_stop,
    handle_daemon_status,
    handle_daemon_list,
    handle_daemon_stop_all,
    handle_daemon_set_threads,
    handle_daemon_get_threads,
    HandlerError,
)


def main() -> int:
    """
    Main entry point for CodeVovle CLI.
    
    Dispatches to appropriate command handlers based on parsed arguments.
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Validate CWD before anything else
        validate_cwd()
        
        # Parse arguments
        args = parse_args()
        
        # Dispatch to appropriate handler
        if args.command == "record":
            return handle_record(args)
        
        elif args.command == "revert":
            return handle_revert(args)
        
        elif args.command == "branch":
            if args.branch_command == "list":
                return handle_branch_list(args)
            elif args.branch_command == "create":
                return handle_branch_create(args)
            elif args.branch_command == "delete":
                return handle_branch_delete(args)
            elif args.branch_command == "rename":
                return handle_branch_rename(args)
            elif args.branch_command == "jump":
                return handle_branch_jump(args)
            else:
                raise CLIError(f"Unknown branch subcommand: {args.branch_command}")
        
        elif args.command == "status":
            return handle_status(args)
        
        elif args.command == "insights":
            return handle_insights(args)
        
        elif args.command == "daemon":
            if args.daemon_command == "start":
                return handle_daemon_start(args)
            elif args.daemon_command == "stop":
                return handle_daemon_stop(args)
            elif args.daemon_command == "status":
                return handle_daemon_status(args)
            elif args.daemon_command == "list":
                return handle_daemon_list(args)
            elif args.daemon_command == "stop-all":
                return handle_daemon_stop_all(args)
            elif args.daemon_command == "set-threads":
                return handle_daemon_set_threads(args)
            elif args.daemon_command == "get-threads":
                return handle_daemon_get_threads(args)
            else:
                raise CLIError(f"Unknown daemon subcommand: {args.daemon_command}")
        
        else:
            raise CLIError(f"Unknown command: {args.command}")
    
    except CLIError as e:
        print(f"\n{e}", file=sys.stderr)
        return 1
    except HandlerError as e:
        print(f"\nHandler error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
