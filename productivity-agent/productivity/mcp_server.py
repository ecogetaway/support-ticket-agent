"""
Lightweight MCP (Model Context Protocol) server that exposes
the productivity tools over stdio so ADK's MCPToolset can consume them.

Run standalone: python -m productivity.mcp_server
"""

import json
import sys
import logging
from productivity.db.database import init_db
from productivity.tools.task_tools import create_task, list_tasks, update_task, complete_task, delete_task
from productivity.tools.calendar_tools import create_event, list_events, upcoming_events, delete_event, update_event
from productivity.tools.notes_tools import create_note, list_notes, search_notes, update_note, delete_note

logging.basicConfig(level=logging.WARNING)

TOOLS = {
    "create_task": {
        "fn": create_task,
        "description": "Create a new task with title, priority, description and optional due date.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string", "default": ""},
                "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Critical"], "default": "Medium"},
                "due_date": {"type": "string", "default": ""},
            },
            "required": ["title"],
        },
    },
    "list_tasks": {
        "fn": list_tasks,
        "description": "List tasks, filtered by optional status or priority.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "default": ""},
                "priority": {"type": "string", "default": ""},
            },
        },
    },
    "complete_task": {
        "fn": complete_task,
        "description": "Mark a task as Done by its ID.",
        "inputSchema": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
    "delete_task": {
        "fn": delete_task,
        "description": "Delete a task by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
    "create_event": {
        "fn": create_event,
        "description": "Create a calendar event.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "start_time": {"type": "string"},
                "end_time": {"type": "string", "default": ""},
                "description": {"type": "string", "default": ""},
                "location": {"type": "string", "default": ""},
            },
            "required": ["title", "start_time"],
        },
    },
    "upcoming_events": {
        "fn": upcoming_events,
        "description": "Get upcoming events in the next N days.",
        "inputSchema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "default": 7}},
        },
    },
    "delete_event": {
        "fn": delete_event,
        "description": "Delete a calendar event by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {"event_id": {"type": "integer"}},
            "required": ["event_id"],
        },
    },
    "create_note": {
        "fn": create_note,
        "description": "Create a new note with title, content, and tags.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string", "default": ""},
                "tags": {"type": "string", "default": ""},
            },
            "required": ["title"],
        },
    },
    "list_notes": {
        "fn": list_notes,
        "description": "List all notes, optionally filtered by tag.",
        "inputSchema": {
            "type": "object",
            "properties": {"tag": {"type": "string", "default": ""}},
        },
    },
    "search_notes": {
        "fn": search_notes,
        "description": "Search notes by title or content.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    "delete_note": {
        "fn": delete_note,
        "description": "Delete a note by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {"note_id": {"type": "integer"}},
            "required": ["note_id"],
        },
    },
}


def send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def handle_request(req: dict) -> dict | None:
    method = req.get("method", "")
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "productivity-mcp", "version": "1.0.0"},
            },
        }

    if method == "tools/list":
        tools_list = [
            {
                "name": name,
                "description": meta["description"],
                "inputSchema": meta["inputSchema"],
            }
            for name, meta in TOOLS.items()
        ]
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools_list}}

    if method == "tools/call":
        tool_name = req.get("params", {}).get("name", "")
        arguments = req.get("params", {}).get("arguments", {})
        if tool_name not in TOOLS:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }
        try:
            result = TOOLS[tool_name]["fn"](**arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, default=str)}]
                },
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(exc)},
            }

    if method == "notifications/initialized":
        return None

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    init_db()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle_request(req)
        if response is not None:
            send(response)


if __name__ == "__main__":
    main()
