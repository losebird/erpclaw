"""Standard response helpers for ERPClaw skill scripts.

Replaces the _ok(), _err(), and _row_to_dict() functions that were
duplicated across all 24 skill db_query.py files.
"""
import json
import sys


def ok(data: dict = None) -> None:
    """Send success response and exit.

    Sets status to "ok" only if not already present, preserving
    domain-specific status fields (e.g., visit_status, plan_status).
    """
    if data is None:
        data = {}
    if "status" not in data:
        data["status"] = "ok"
    print(json.dumps(data, indent=2, default=str))
    sys.exit(0)


def err(message: str, suggestion: str = None) -> None:
    """Send error response and exit."""
    data = {"status": "error", "message": message}
    if suggestion:
        data["suggestion"] = suggestion
    print(json.dumps(data, indent=2))
    sys.exit(1)


def row_to_dict(row) -> dict:
    """Convert sqlite3.Row to plain dict."""
    return dict(row) if row else {}


def rows_to_list(rows) -> list[dict]:
    """Convert list of sqlite3.Row to list of dicts."""
    return [dict(r) for r in rows] if rows else []
