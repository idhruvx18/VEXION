"""
app/tools/registry.py
──────────────────────
VEXION Tool Registry.

The assistant core calls `registry.dispatch(tool_name, args)`.
The registry:
  1. Looks up the tool.
  2. Validates arguments.
  3. Builds a PermissionRequest.
  4. Returns either the result (LOW risk, auto-allowed) or a
     PendingApproval object that the UI must confirm before execution.

Model output is NEVER executed directly — it must match a registered tool name.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable

from app.tools.permissions import (
    PermissionRequest, RiskLevel, build_request, get_risk
)
from app.tools.open_url    import open_url, validate_url
from app.tools.open_app    import open_app, list_allowed_apps
from app.tools.files       import search_files, open_file, create_note
from app.tools.system_info import get_time, get_diagnostics, list_tools

logger = logging.getLogger(__name__)


# ── Tool entry ────────────────────────────────────────────────────────────────
@dataclass
class ToolEntry:
    name:        str
    fn:          Callable[..., dict]
    description: str
    arg_schema:  dict[str, type]    # name → expected type


# ── Pending approval ──────────────────────────────────────────────────────────
@dataclass
class PendingApproval:
    request:  PermissionRequest
    tool_fn:  Callable[..., dict]
    args:     dict

    def execute(self) -> dict:
        """Called after the user presses Approve."""
        return self.tool_fn(**self.args)


# ── Registry ──────────────────────────────────────────────────────────────────
class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolEntry] = {}
        self._register_defaults()

    def _register(self, entry: ToolEntry) -> None:
        self._tools[entry.name] = entry

    def _register_defaults(self) -> None:
        self._register(ToolEntry(
            name="get_time", fn=get_time,
            description="Return the current date and time.",
            arg_schema={},
        ))
        self._register(ToolEntry(
            name="open_url", fn=lambda url: open_url(url),
            description="Open a validated URL in the default browser.",
            arg_schema={"url": str},
        ))
        self._register(ToolEntry(
            name="open_app", fn=lambda app_name: open_app(app_name),
            description="Launch an allowlisted desktop application.",
            arg_schema={"app_name": str},
        ))
        self._register(ToolEntry(
            name="search_files",
            fn=lambda query, root=None: search_files(query, root),
            description="Search for files in approved directories.",
            arg_schema={"query": str},
        ))
        self._register(ToolEntry(
            name="open_file", fn=lambda file_path: open_file(file_path),
            description="Open a file with the OS default handler.",
            arg_schema={"file_path": str},
        ))
        self._register(ToolEntry(
            name="create_note",
            fn=lambda title, content="": create_note(title, content),
            description="Create a text note in the VEXION notes folder.",
            arg_schema={"title": str, "content": str},
        ))
        self._register(ToolEntry(
            name="diagnostics", fn=get_diagnostics,
            description="Show VEXION configuration and provider status.",
            arg_schema={},
        ))
        self._register(ToolEntry(
            name="list_tools", fn=list_tools,
            description="List all available tools.",
            arg_schema={},
        ))

    # ── Validation ─────────────────────────────────────────────────────────
    def _validate_args(self, entry: ToolEntry, args: dict) -> tuple[bool, str]:
        for required_name, required_type in entry.arg_schema.items():
            if required_name not in args:
                if required_name in ("content", "root"):
                    continue   # optional args
                return False, f"Missing required argument: '{required_name}'"
            val = args[required_name]
            if not isinstance(val, required_type):
                return False, (
                    f"Argument '{required_name}' must be {required_type.__name__}, "
                    f"got {type(val).__name__}."
                )
        return True, "ok"

    # ── Dispatch ───────────────────────────────────────────────────────────
    def dispatch(
        self, tool_name: str, args: dict
    ) -> dict | PendingApproval:
        """
        Execute or stage a tool call.

        Returns:
          dict          — result (LOW risk or auto-approved)
          PendingApproval — needs UI confirmation
        """
        entry = self._tools.get(tool_name)
        if entry is None:
            logger.warning("Unknown tool requested: %s", tool_name)
            return {
                "ok":      False,
                "message": f"Unknown tool: '{tool_name}'. Ask 'list tools' for options.",
            }

        ok, reason = self._validate_args(entry, args)
        if not ok:
            return {"ok": False, "message": reason}

        risk = get_risk(tool_name)
        description = self._build_description(tool_name, args)
        request = build_request(tool_name, args, description)

        if risk == RiskLevel.LOW:
            result = entry.fn(**args)
            logger.info("Tool executed (LOW): %s %s → %s", tool_name, args, result.get("ok"))
            return result

        # MEDIUM and HIGH require approval
        return PendingApproval(request=request, tool_fn=entry.fn, args=args)

    def _build_description(self, tool_name: str, args: dict) -> str:
        descs = {
            "open_url":     lambda a: f"Open website: {a.get('url', '')}",
            "open_app":     lambda a: f"Launch application: {a.get('app_name', '')}",
            "search_files": lambda a: f"Search files for: '{a.get('query', '')}'",
            "open_file":    lambda a: f"Open file: {a.get('file_path', '')}",
            "create_note":  lambda a: f"Create note titled: '{a.get('title', '')}'",
        }
        fn = descs.get(tool_name)
        if fn:
            return fn(args)
        return f"{tool_name}({', '.join(f'{k}={v!r}' for k, v in args.items())})"

    # ── Parse AI tool call from model text ────────────────────────────────
    @staticmethod
    def parse_tool_call(text: str) -> tuple[str, dict] | None:
        """
        Extract a tool call from model output.
        Expects a JSON block like:
          {"tool": "open_url", "args": {"url": "https://example.com"}}
        Returns (tool_name, args) or None if not a tool call.
        """
        # Find the first JSON-like block
        match = re.search(r'\{[^{}]*"tool"[^{}]*\}', text, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group())
            tool_name = data.get("tool", "")
            args      = data.get("args", {})
            if tool_name and isinstance(args, dict):
                return tool_name, args
        except (json.JSONDecodeError, AttributeError):
            pass
        return None

    def all_tools(self) -> list[ToolEntry]:
        return list(self._tools.values())
