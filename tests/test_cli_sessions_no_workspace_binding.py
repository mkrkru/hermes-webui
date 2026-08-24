"""CLI sessions must not be bound to a workspace.

CLI/agent sessions live in Hermes' own state.db with their own directory
layout, not in a WebUI workspace folder. The sidebar projection must not
attach the active WebUI workspace (``get_last_workspace()``) to them, and the
"CLI sessions" view must render as one flat, continuous list instead of being
grouped under a workspace heading.
"""
from __future__ import annotations

import pathlib
import sqlite3

import pytest

import api.models as models


def _make_state_db(path, sessions):
    """Create a state.db with the schema get_cli_sessions() expects.

    ``sessions`` is a list of (id, title, source) tuples.
    """
    conn = sqlite3.connect(str(path))
    conn.execute(
        """
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            model TEXT,
            message_count INTEGER,
            started_at REAL,
            source TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp REAL
        )
        """
    )
    for sid, title, source in sessions:
        conn.execute(
            "INSERT INTO sessions (id, title, model, message_count, started_at, source) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (sid, title, "gpt-x", 1, 1700000000.0, source),
        )
        conn.execute(
            "INSERT INTO messages (session_id, timestamp) VALUES (?, ?)",
            (sid, 1700000001.0),
        )
    conn.commit()
    conn.close()


@pytest.fixture
def fake_hermes_home(tmp_path, monkeypatch):
    """Point get_cli_sessions() at a temporary HERMES_HOME and disable
    profile lookups so the test runs hermetically."""
    home = tmp_path / "hermes"
    home.mkdir()
    import api.profiles as profiles

    monkeypatch.setattr(profiles, "get_active_hermes_home", lambda: home)
    monkeypatch.setattr(profiles, "get_active_profile_name", lambda: None)
    return home


def test_cli_session_rows_have_no_workspace(fake_hermes_home, monkeypatch):
    """A CLI-sourced row must project with an empty workspace, even when the
    active WebUI workspace is set."""
    _make_state_db(fake_hermes_home / "state.db", [
        ("20260101_cli_abc123", "CLI chat", "cli"),
    ])
    # Force get_last_workspace() to a concrete path; the projection must NOT
    # use it for CLI rows.
    monkeypatch.setattr(models, "get_last_workspace", lambda: "/active/ws")

    sessions = models.get_cli_sessions()

    assert len(sessions) == 1
    assert sessions[0]["source_tag"] == "cli"
    assert sessions[0]["workspace"] == "", (
        "CLI sessions must not be bound to the active WebUI workspace"
    )


def test_cli_sessions_render_flat_in_sidebar():
    """sessions.js must render the CLI view as one flat group (no workspace
    headers) and skip the workspace filter bar for CLI sessions."""
    js = (
        pathlib.Path(__file__).parent.parent / "static" / "sessions.js"
    ).read_text(encoding="utf-8")
    assert (
        "if(unpinned.length) groups.push({label:'',items:unpinned,isFlat:true});"
        in js
    )
    assert "if(!isCliView){" in js
    assert "if(!g.isFlat){" in js
