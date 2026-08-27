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
    headers)."""
    js = (
        pathlib.Path(__file__).parent.parent / "static" / "sessions.js"
    ).read_text(encoding="utf-8")
    assert (
        "if(unpinned.length) groups.push({label:'',items:unpinned,isFlat:true});"
        in js
    )
    assert "if(!g.isFlat){" in js


def test_resolve_chat_workspace_cli_session_no_persist(tmp_path, monkeypatch):
    """Continuing a workspace-unbound CLI session resolves a run cwd from the
    active workspace WITHOUT persisting a binding back into the sidecar."""
    routes = pytest.importorskip("api.routes")
    from pathlib import Path
    from types import SimpleNamespace

    s = SimpleNamespace(workspace="", is_cli_session=True, session_id="cli_no_persist")
    monkeypatch.setattr(routes, "get_last_workspace", lambda: str(tmp_path))
    # Bypass trust validation (tmp_path is outside $HOME) — this test pins the
    # no-persist contract, not the trust-boundary check.
    monkeypatch.setattr(
        routes, "resolve_trusted_workspace", lambda p: Path(str(p)).resolve()
    )
    persist_calls = {"n": 0}

    def _boom(*_a, **_k):
        persist_calls["n"] += 1
        raise AssertionError("must not persist a workspace binding for CLI sessions")

    monkeypatch.setattr(routes, "persist_recovered_workspace_binding", _boom)

    result = routes._resolve_chat_workspace_with_recovery(s, None)

    assert result == str(tmp_path.resolve())
    assert persist_calls["n"] == 0, (
        "CLI sessions must stay unbound: no workspace binding may be persisted"
    )


def test_switch_to_workspace_does_not_rebind_cli_session():
    """switchToWorkspace must not overwrite a CLI session's workspace locally
    after the server-side global active-workspace switch."""
    js = (
        pathlib.Path(__file__).parent.parent / "static" / "panels.js"
    ).read_text(encoding="utf-8")
    assert "if(!(S.session&&S.session.is_cli_session)) S.session.workspace=path;" in js


def test_session_update_does_not_rebind_cli_session():
    """/api/session/update must skip the session workspace mutation for CLI
    sessions while still updating the global active workspace."""
    src = (
        pathlib.Path(__file__).parent.parent / "api" / "routes.py"
    ).read_text(encoding="utf-8")
    start = src.index('parsed.path == "/api/session/update"')
    nxt = src.find("if parsed.path ==", start + 1)
    block = src[start: nxt if nxt != -1 else start + 4000]
    assert "is_cli = bool(getattr(s, \"is_cli_session\", False))" in block
    assert "if not is_cli:" in block
    assert "s.workspace = new_ws" in block
    assert "if not is_cli and str(old_ws or \"\") != str(new_ws or \"\"):" in block
    assert "set_last_workspace(new_ws)" in block
