"""
tests/test_permissions.py
──────────────────────────
Tests for the permission/risk model.
"""

import pytest
from app.tools.permissions import (
    RiskLevel, build_request, get_risk, PermissionRequest
)


class TestRiskLevels:
    def test_get_time_is_low(self):
        assert get_risk("get_time") == RiskLevel.LOW

    def test_list_tools_is_low(self):
        assert get_risk("list_tools") == RiskLevel.LOW

    def test_open_url_is_medium(self):
        assert get_risk("open_url") == RiskLevel.MEDIUM

    def test_open_app_is_medium(self):
        assert get_risk("open_app") == RiskLevel.MEDIUM

    def test_delete_file_is_high(self):
        assert get_risk("delete_file") == RiskLevel.HIGH

    def test_run_command_is_high(self):
        assert get_risk("run_command") == RiskLevel.HIGH

    def test_unknown_tool_defaults_to_high(self):
        assert get_risk("totally_unknown_tool_xyz") == RiskLevel.HIGH


class TestPermissionRequest:
    def test_low_does_not_require_approval(self):
        req = build_request("get_time", {})
        assert not req.requires_approval

    def test_medium_requires_approval(self):
        req = build_request("open_url", {"url": "https://x.com"})
        assert req.requires_approval

    def test_high_requires_approval(self):
        req = build_request("delete_file", {"path": "/some/path"})
        assert req.requires_approval
        assert req.always_approve

    def test_medium_not_always_approve(self):
        req = build_request("open_url", {"url": "https://x.com"})
        assert not req.always_approve

    def test_description_auto_generated(self):
        req = build_request("open_url", {"url": "https://x.com"})
        assert "open_url" in req.description or "https" in req.description

    def test_custom_description(self):
        req = build_request("open_app", {"app_name": "notepad"}, "Launch Notepad")
        assert req.description == "Launch Notepad"
