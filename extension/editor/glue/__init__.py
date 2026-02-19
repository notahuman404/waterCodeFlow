"""
Glue package: stable facades for VS Code extension integration.

Submodules:
  api       - recording read/write (filesystem-based, no codevovle dependency)
  variables - AST-based variable extraction + watcher event support
  runs      - grouping recordings into logical run objects
  watch     - watch() shim and WatchProxy
  errors    - GlueError, NotFoundError
"""
from . import api as api
from . import variables as variables
from . import watch as watch
from . import errors as errors
from . import runs as runs

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
    "api", "variables", "watch", "errors", "runs",
    "list_recordings", "get_recording", "delete_recording", "delete_all_recordings",
    "get_cursor", "set_cursor", "jump_to_tick", "get_status",
    "start_recording", "stop_recording", "list_daemon_processes",
    "get_branches", "create_branch", "rename_branch", "delete_branch",
    "get_insights", "get_variable_timeline", "list_tracked_variables",
    "watch_value", "WatchProxy", "GlueError", "NotFoundError",
]
