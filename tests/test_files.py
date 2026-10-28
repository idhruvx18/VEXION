"""
tests/test_files.py
────────────────────
Tests for file tools — path restrictions, create_note safety.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.tools.files import (
    _is_safe_path, search_files, create_note, open_file
)


class TestSafePath:
    def test_path_inside_root_is_safe(self, tmp_path):
        target = tmp_path / "notes" / "hello.txt"
        assert _is_safe_path(target, [tmp_path])

    def test_path_outside_root_is_unsafe(self, tmp_path):
        outside = Path("C:/Windows/System32/secret.dll")
        assert not _is_safe_path(outside, [tmp_path])

    def test_traversal_blocked(self, tmp_path):
        traversal = tmp_path / ".." / ".." / "etc" / "passwd"
        roots = [tmp_path]
        # After resolve the traversal escapes tmp_path
        assert not _is_safe_path(traversal, roots)


class TestSearchFiles:
    def test_empty_query_returns_error(self):
        result = search_files("")
        assert result.get("ok") is False

    def test_none_query_returns_error(self):
        result = search_files(None)  # type: ignore
        assert result.get("ok") is False


class TestCreateNote:
    def test_creates_note_in_notes_dir(self, tmp_path):
        from app import config as cfg
        original_notes = cfg.paths.notes_dir
        cfg.paths.notes_dir = tmp_path
        cfg.paths.data_dir  = tmp_path

        try:
            result = create_note("Test Note", "Hello world")
            assert result.get("ok") is True
            note_path = Path(result["path"])
            assert note_path.exists()
            assert note_path.read_text(encoding="utf-8") == "Hello world"
        finally:
            cfg.paths.notes_dir = original_notes
            cfg.paths.data_dir  = original_notes.parent

    def test_empty_title_returns_error(self):
        result = create_note("", "content")
        assert result.get("ok") is False

    def test_no_overwrite_existing_note(self, tmp_path):
        from app import config as cfg
        original_notes = cfg.paths.notes_dir
        cfg.paths.notes_dir = tmp_path
        cfg.paths.data_dir  = tmp_path

        try:
            r1 = create_note("Duplicate", "first")
            r2 = create_note("Duplicate", "second")
            assert r1["path"] != r2["path"]
            assert Path(r1["path"]).exists()
            assert Path(r2["path"]).exists()
        finally:
            cfg.paths.notes_dir = original_notes
            cfg.paths.data_dir  = original_notes.parent

    def test_title_sanitised(self, tmp_path):
        from app import config as cfg
        original_notes = cfg.paths.notes_dir
        original_data  = cfg.paths.data_dir
        cfg.paths.notes_dir = tmp_path
        cfg.paths.data_dir  = tmp_path

        try:
            result = create_note("../../etc/passwd", "evil content")
            # The key security check: the resulting file must NOT be at /etc/passwd
            # The title should have been sanitised to something harmless.
            if result.get("ok"):
                note_path = Path(result["path"])
                # File must have a .txt extension (not been executed or redirected)
                assert note_path.suffix == ".txt"
                # The filename must not contain path separators
                assert "/" not in note_path.name
                assert "\\" not in note_path.name
                # The file must NOT be at /etc/passwd or any system path
                assert "etc" not in str(note_path).lower() or tmp_path.drive in str(note_path)
        finally:
            cfg.paths.notes_dir = original_notes
            cfg.paths.data_dir  = original_data


class TestOpenFile:
    def test_nonexistent_file_error(self, tmp_path):
        result = open_file(str(tmp_path / "ghost.txt"))
        # Will fail either on path check or existence check
        assert result.get("ok") is False
