#!/usr/bin/env python3
"""
Glue adapter: JSON CLI bridge for VS Code extension.
Reads JSON commands from stdin, calls glue functions, writes JSON responses to stdout.
"""
import json
import sys
import traceback
from typing import Any, Dict

# Import all glue functions
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
from glue.runs import get_runs, get_run_details, delete_run


def handle_command(command_str: str) -> str:
    """
    Parse JSON command, invoke glue function, return JSON response.
    
    Command format:
    {
        "id": "uuid",
        "command": "startRecording",
        "filePath": "...",
        "interval": 0.5
    }
    """
    try:
        data = json.loads(command_str)
        cmd = data.get("command")
        result = None
        
        if cmd == "startRecording":
            result = start_recording(
                data["filePath"],
                data.get("interval", 1.0),
                data.get("numThreads")
            )
        
        elif cmd == "stopRecording":
            result = stop_recording(data["filePath"])
        
        elif cmd == "jumpToTick":
            result = jump_to_tick(data["filePath"], data["tickId"])
        
        elif cmd == "listRuns":
            runs = get_runs(
                data["filePath"],
                data.get("gapThresholdSeconds", 30.0)
            )
            result = runs
        
        elif cmd == "getRunDetails":
            result = get_run_details(data["filePath"], data["runId"])
        
        elif cmd == "deleteRun":
            result = delete_run(data["filePath"], data["runId"])
        
        elif cmd == "deleteRecording":
            result = delete_recording(data["tickId"])
        
        elif cmd == "deleteAllRecordings":
            result = delete_all_recordings(data["filePath"])
        
        elif cmd == "listRecordings":
            result = list_recordings(data["filePath"])
        
        elif cmd == "getRecording":
            result = get_recording(data["tickId"])
        
        elif cmd == "getStatus":
            result = get_status(data["filePath"])
        
        elif cmd == "getCursor":
            result = get_cursor(data["filePath"])
        
        elif cmd == "setCursor":
            result = set_cursor(
                data["filePath"],
                data["branch"],
                data.get("tick")
            )
        
        elif cmd == "getVariableTimeline":
            result = get_variable_timeline(
                data["filePath"],
                data["variableName"],
                data.get("maxTicks", 200)
            )
        
        elif cmd == "listTrackedVariables":
            result = list_tracked_variables(data["filePath"])
        
        elif cmd == "getBranches":
            result = get_branches(data["filePath"])
        
        elif cmd == "createBranch":
            result = create_branch(
                data["name"],
                data.get("parent"),
                data.get("forkedAtTick")
            )
        
        elif cmd == "renameBranch":
            result = rename_branch(data["oldName"], data["newName"])
        
        elif cmd == "deleteBranch":
            result = delete_branch(data["name"])
        
        elif cmd == "getInsights":
            result = get_insights(
                data["filePath"],
                data["fromTick"],
                data["toTick"],
                data.get("model")
            )
        
        elif cmd == "listDaemons":
            result = list_daemon_processes()
        
        else:
            return json.dumps({
                "id": data.get("id"),
                "success": False,
                "error": f"Unknown command: {cmd}"
            })
        
        return json.dumps({
            "id": data.get("id"),
            "success": True,
            "result": result
        })
    
    except GlueError as e:
        try:
            data = json.loads(command_str)
            request_id = data.get("id")
        except:
            request_id = None
        
        return json.dumps({
            "id": request_id,
            "success": False,
            "error": str(e),
            "errorType": "GlueError"
        })
    
    except Exception as e:
        try:
            data = json.loads(command_str)
            request_id = data.get("id")
        except:
            request_id = None
        
        return json.dumps({
            "id": request_id,
            "success": False,
            "error": str(e),
            "errorType": "Exception",
            "traceback": traceback.format_exc()
        })


def main():
    """Read lines from stdin, process as JSON commands, write responses to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        response = handle_command(line)
        print(response, flush=True)


if __name__ == "__main__":
    main()
