"""
tests/test_tool_registry.py
────────────────────────────
Tests for the tool registry — dispatch, validation, and tool-call parsing.
All external I/O (webbrowser, subprocess, file system) is mocked.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from app.tools.registry import ToolRegistry, PendingApproval
from app.tools.permissions import RiskLevel


@pytest.fixture
def registry():
    return ToolRegistry()


class TestDispatchLowRisk:
    """Low-risk tools (get_time, list_tools, diagnostics) run immediately."""

    def test_get_time_runs(self, registry):
        result = registry.dispatch("get_time", {})
        assert isinstance(result, dict)
        assert result.get("ok") is True
        assert "time" in result

    def test_list_tools_runs(self, registry):
        result = registry.dispatch("list_tools", {})
        assert result.get("ok") is True
        assert "tools" in result
        assert len(result["tools"]) > 0


class TestDispatchMediumRisk:
    """Medium-risk tools return PendingApproval — never run automatically."""

    def test_open_url_needs_approval(self, registry):
        result = registry.dispatch("open_url", {"url": "https://google.com"})
        assert isinstance(result, PendingApproval)

    def test_open_app_needs_approval(self, registry):
        result = registry.dispatch("open_app", {"app_name": "notepad"})
        assert isinstance(result, PendingApproval)

    def test_create_note_needs_approval(self, registry):
        result = registry.dispatch("create_note", {"title": "Test", "content": "hello"})
        assert isinstance(result, PendingApproval)


class TestPendingApprovalExecution:
    """After approval, PendingApproval.execute() runs the actual tool."""

    def test_open_url_executes_after_approve(self, registry):
        pending = registry.dispatch("open_url", {"url": "https://example.com"})
        assert isinstance(pending, PendingApproval)
        with patch("webbrowser.open") as mock_open:
            result = pending.execute()
        mock_open.assert_called_once_with("https://example.com")
        assert result.get("ok") is True

    def test_open_url_blocked_url_returns_error(self, registry):
        pending = registry.dispatch("open_url", {"url": "file:///etc/passwd"})
        assert isinstance(pending, PendingApproval)
        result = pending.execute()
        assert result.get("ok") is False


class TestArgValidation:
    def test_missing_required_arg(self, registry):
        result = registry.dispatch("open_url", {})
        assert isinstance(result, dict)
        assert result.get("ok") is False
        assert "Missing" in result.get("message", "")

    def test_wrong_type_arg(self, registry):
        result = registry.dispatch("open_url", {"url": 12345})
        assert isinstance(result, dict)
        assert result.get("ok") is False

    def test_unknown_tool(self, registry):
        result = registry.dispatch("launch_missiles", {})
        assert isinstance(result, dict)
        assert result.get("ok") is False
        assert "Unknown" in result.get("message", "")


class TestParseToolCall:
    def test_valid_json_block(self):
        text = 'Sure! {"tool": "get_time", "args": {}} done.'
        parsed = ToolRegistry.parse_tool_call(text)
        assert parsed is not None
        name, args = parsed
        assert name == "get_time"
        assert args == {}

    def test_with_args(self):
        text = '{"tool": "open_url", "args": {"url": "https://x.com"}}'
        parsed = ToolRegistry.parse_tool_call(text)
        assert parsed is not None
        name, args = parsed
        assert name == "open_url"
        assert args["url"] == "https://x.com"

    def test_plain_text_returns_none(self):
        assert ToolRegistry.parse_tool_call("Hello, how can I help?") is None

    def test_malformed_json_returns_none(self):
        assert ToolRegistry.parse_tool_call('{"tool": "open_url"') is None
