"""
app/tools/permissions.py
─────────────────────────
VEXION permission / risk model.

Risk levels:
  LOW    — safe to run automatically if user has allowed it.
  MEDIUM — show a brief confirmation when scope is ambiguous.
  HIGH   — ALWAYS require explicit user approval before executing.

No tool execution bypasses this layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class RiskLevel(Enum):
    LOW    = auto()
    MEDIUM = auto()
    HIGH   = auto()


@dataclass
class PermissionRequest:
    tool_name:   str
    args:        dict
    risk:        RiskLevel
    description: str          # Human-readable action description shown to user

    @property
    def requires_approval(self) -> bool:
        return self.risk in (RiskLevel.MEDIUM, RiskLevel.HIGH)

    @property
    def always_approve(self) -> bool:
        """High-risk actions ALWAYS show the approval overlay."""
        return self.risk == RiskLevel.HIGH


# ── Tool risk registry ────────────────────────────────────────────────────────
# Maps tool name → RiskLevel
TOOL_RISK: dict[str, RiskLevel] = {
    # Low risk — informational
    "get_time":        RiskLevel.LOW,
    "list_tools":      RiskLevel.LOW,
    "diagnostics":     RiskLevel.LOW,

    # Medium risk — opens external things
    "open_url":        RiskLevel.MEDIUM,
    "open_app":        RiskLevel.MEDIUM,
    "search_files":    RiskLevel.MEDIUM,
    "open_file":       RiskLevel.MEDIUM,

    # Medium risk — creates/writes
    "create_note":     RiskLevel.MEDIUM,

    # High risk — destructive / irreversible
    "delete_file":     RiskLevel.HIGH,
    "overwrite_file":  RiskLevel.HIGH,
    "run_command":     RiskLevel.HIGH,
    "send_message":    RiskLevel.HIGH,
}


def get_risk(tool_name: str) -> RiskLevel:
    return TOOL_RISK.get(tool_name, RiskLevel.HIGH)   # unknown → HIGH by default


def build_request(tool_name: str, args: dict, description: str = "") -> PermissionRequest:
    risk = get_risk(tool_name)
    if not description:
        description = f"{tool_name}({', '.join(f'{k}={v!r}' for k, v in args.items())})"
    return PermissionRequest(
        tool_name=tool_name,
        args=args,
        risk=risk,
        description=description,
    )
