"""Glue package: small, stable façades for UI integration.

Expose a compact set of helpers implemented in submodules:
- api: recording/daemon/insights wrappers
- variables: naive variable timeline helpers
- watch: watch() shim and WatchProxy
- errors: Glue-specific exceptions
"""
from . import api as api
from . import variables as variables
from . import watch as watch
from . import errors as errors
from . import runs as runs

# Re-export commonly used symbols for convenience
from .api import (
    list_recordings,
    get_recording,
    delete_recording,
    delete_all_recordings,
    get_cursor,
    set_cursor,
    jump_to_tick,
    get_status,
    start_recording,
    stop_recording,
    list_daemon_processes,
    get_branches,
    create_branch,
    rename_branch,
    delete_branch,
    get_insights,
)
from .variables import get_variable_timeline, list_tracked_variables
from .watch import watch as watch_value, WatchProxy
from .errors import GlueError, NotFoundError

__all__ = [
    "api",
    "variables",
    "watch",
    "errors",
    "runs",
    # Recording management
    "list_recordings",
    "get_recording",
    "delete_recording",
    "delete_all_recordings",
    # Cursor / navigation
    "get_cursor",
    "set_cursor",
    "jump_to_tick",
    # Status and monitoring
    "get_status",
    # Daemon / background recording
    "start_recording",
    "stop_recording",
    "list_daemon_processes",
    # Branches
    "get_branches",
    "create_branch",
    "rename_branch",
    "delete_branch",
    # Insights (AI)
    "get_insights",
    # Variables
    "get_variable_timeline",
    "list_tracked_variables",
    # Watch
    "watch_value",
    "WatchProxy",
    # Errors
    "GlueError",
    "NotFoundError",
]
