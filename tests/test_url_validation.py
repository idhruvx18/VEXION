"""
tests/test_url_validation.py
─────────────────────────────
Tests for URL validation in open_url tool.
"""

import pytest
from app.tools.open_url import validate_url


class TestValidUrls:
    def test_https_url_ok(self):
        ok, _ = validate_url("https://www.google.com")
        assert ok

    def test_http_url_ok(self):
        ok, _ = validate_url("http://example.com/path?q=1")
        assert ok

    def test_https_with_path_ok(self):
        ok, _ = validate_url("https://github.com/user/repo")
        assert ok

    def test_localhost_allowed(self):
        ok, _ = validate_url("http://localhost:8080")
        assert ok   # allowed with a warning in logs


class TestInvalidUrls:
    def test_empty_string(self):
        ok, reason = validate_url("")
        assert not ok
        assert "empty" in reason.lower()

    def test_none_value(self):
        ok, reason = validate_url(None)  # type: ignore
        assert not ok

    def test_file_scheme_blocked(self):
        ok, reason = validate_url("file:///etc/passwd")
        assert not ok
        assert "file" in reason.lower() or "not allowed" in reason.lower()

    def test_javascript_scheme_blocked(self):
        ok, reason = validate_url("javascript:alert(1)")
        assert not ok

    def test_data_scheme_blocked(self):
        ok, reason = validate_url("data:text/html,<h1>xss</h1>")
        assert not ok

    def test_ftp_scheme_blocked(self):
        ok, reason = validate_url("ftp://example.com/file.zip")
        assert not ok

    def test_no_scheme_blocked(self):
        ok, reason = validate_url("www.google.com")
        assert not ok

    def test_aws_metadata_blocked(self):
        ok, reason = validate_url("http://169.254.169.254/latest/meta-data/")
        assert not ok
        assert "blocked" in reason.lower()

    def test_no_host_blocked(self):
        ok, reason = validate_url("https://")
        assert not ok
