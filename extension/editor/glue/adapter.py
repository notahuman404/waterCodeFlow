#!/usr/bin/env python3
"""
Glue adapter: JSON stdin/stdout bridge between the VS Code extension and
the real recording filesystem.

Reads newline-delimited JSON commands from stdin, dispatches to the
appropriate glue function, writes JSON responses to stdout.

Command format:
  {"id": "uuid", "command": "listRecordings", "filePath": "...", ...}

Response format:
  {"id": "uuid", "success": true, "result": <any>}
  {"id": "uuid", "success": false, "error": "...", "errorType": "..."}
"""
import json
import sys
import traceback
from typing import Any

from glue import (
    list_recordings,
    get_recording,
    delete_recording,
    delete_all_recordings,
    start_recording,
    stop_recording,
    jump_to_tick,
    get_status,
    get_cursor,
    set_cursor,
    get_branches,
    create_branch,
    rename_branch,
    delete_branch,
    get_insights,
    get_variable_timeline,
    list_tracked_variables,
    list_daemon_processes,
    GlueError,
)
from glue.api import save_recording
from glue.runs import get_runs, get_run_details, delete_run


def handle_command(command_str: str) -> str:
    try:
        data = json.loads(command_str)
        cmd = data.get("command")
        result: Any = None

        if cmd == "startRecording":
            result = start_recording(
                data["filePath"],
                data.get("interval", 1.0),
                data.get("numThreads"),
            )

        elif cmd == "stopRecording":
            result = stop_recording(data["filePath"])

        elif cmd == "jumpToTick":
            result = jump_to_tick(data["filePath"], data["tickId"])

        elif cmd == "listRuns":
            result = get_runs(
                data["filePath"],
                data.get("gapThresholdSeconds", 30.0),
            )

        elif cmd == "getRunDetails":
            result = get_run_details(data["filePath"], data["runId"])

        elif cmd == "deleteRun":
            result = delete_run(data["filePath"], data["runId"])

        elif cmd == "deleteRecording":
            result = delete_recording(data["runId"] if "runId" in data else data["tickId"])

        elif cmd == "deleteAllRecordings":
            result = delete_all_recordings(data["filePath"])

        elif cmd == "listRecordings":
            result = list_recordings(data["filePath"])

        elif cmd == "getRecording":
            result = get_recording(data.get("runId") or data.get("tickId"))

        elif cmd == "saveRecording":
            # Called by GlueBridge.ts after each spawnRun completes.
            # Merges glue metadata into the recording JSON.
            result = save_recording(
                run_id=data["runId"],
                recording_path=data.get("recordingPath", ""),
                file_path=data.get("filePath", ""),
                timestamp=data.get("timestamp", ""),
                duration_ms=int(data.get("durationMs", 0)),
                exit_code=int(data.get("exitCode", 0)),
                variables=data.get("variables"),
            )

        elif cmd == "getStatus":
            result = get_status(data["filePath"])

        elif cmd == "getCursor":
            result = get_cursor(data["filePath"])

        elif cmd == "setCursor":
            result = set_cursor(data["filePath"], data["branch"], data.get("tick"))

        elif cmd == "getVariableTimeline":
            result = get_variable_timeline(
                data["filePath"],
                data["variableName"],
                data.get("maxTicks", 200),
            )

        elif cmd == "listTrackedVariables":
            result = list_tracked_variables(data["filePath"])

        elif cmd == "getBranches":
            result = get_branches(data["filePath"])

        elif cmd == "createBranch":
            result = create_branch(data["name"], data.get("parent"), data.get("forkedAtTick"))

        elif cmd == "renameBranch":
            result = rename_branch(data["oldName"], data["newName"])

        elif cmd == "deleteBranch":
            result = delete_branch(data["name"])

        elif cmd == "getInsights":
            result = get_insights(
                data["filePath"],
                data["fromTick"],
                data["toTick"],
                data.get("model"),
            )

        elif cmd == "listDaemons":
            result = list_daemon_processes()

        else:
            return json.dumps({
                "id": data.get("id"),
                "success": False,
                "error": f"Unknown command: {cmd!r}",
            })

        return json.dumps({"id": data.get("id"), "success": True, "result": result})

    except GlueError as e:
        try:
            req_id = json.loads(command_str).get("id")
        except Exception:
            req_id = None
        return json.dumps({
            "id": req_id,
            "success": False,
            "error": str(e),
            "errorType": "GlueError",
        })

    except Exception as e:
        try:
            req_id = json.loads(command_str).get("id")
        except Exception:
            req_id = None
        return json.dumps({
            "id": req_id,
            "success": False,
            "error": str(e),
            "errorType": "Exception",
            "traceback": traceback.format_exc(),
        })


def main():
    """Read JSON commands from stdin, dispatch, write responses to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        response = handle_command(line)
        print(response, flush=True)


if __name__ == "__main__":
    main()
