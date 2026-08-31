"""Workspace-panel Terminal tab: static contracts.

The tab HOSTS the existing composer terminal (one xterm instance + one PTY per
WebUI session) by moving the #composerTerminalPanel DOM node into the tab host
— it must never create a second terminal or embed an external one.
"""

from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent


def _workspace_js() -> str:
    return (REPO_ROOT / "static" / "workspace.js").read_text(encoding="utf-8")


def _terminal_js() -> str:
    return (REPO_ROOT / "static" / "terminal.js").read_text(encoding="utf-8")


def _index_html() -> str:
    return (REPO_ROOT / "static" / "index.html").read_text(encoding="utf-8")


def test_workspace_terminal_tab_button_and_host_exist():
    html = _index_html()
    assert 'id="workspaceTerminalTab"' in html
    assert 'id="workspaceTerminalHost"' in html
    assert "workspace_terminal_tab" in html
    # No external embed: no iframe, no ttyd URL setting.
    assert "workspaceTerminalFrame" not in html
    assert "settingsWorkspaceTerminalUrl" not in html


def test_workspace_terminal_tab_is_opt_in_and_hidden_by_default():
    config = (REPO_ROOT / "api" / "config.py").read_text(encoding="utf-8")
    assert '"workspace_terminal_tab": False' in config
    assert "workspace_terminal_url" not in config

    workspace = _workspace_js()
    visibility_start = workspace.find("function _applyWorkspaceTerminalTabVisibility()")
    assert visibility_start != -1
    visibility = workspace[visibility_start:]
    assert "tab.hidden=!window._workspaceTerminalTab" in visibility
    assert "workspaceTerminalTab" in visibility


def test_terminal_tab_hosts_composer_panel_instead_of_second_terminal():
    workspace = _workspace_js()
    assert 'const host = $(\'workspaceTerminalHost\')' in workspace
    assert "host.appendChild(panel)" in workspace
    assert "parent.appendChild(panel)" in workspace
    assert "TERMINAL_UI.hosted = true" in workspace
    # Unmount must restore the node into its original composer parent.
    mount = workspace.find("function _mountWorkspacePanelTerminal()")
    unmount = workspace.find("function _unmountWorkspacePanelTerminal()")
    assert mount != -1 and unmount != -1
    assert "_workspaceTerminalHostParent = panel.parentNode" in workspace


def test_composer_terminal_open_and_close_resync_host_location():
    terminal = _terminal_js()
    assert (
        "if(typeof _syncWorkspaceTerminalHostLocation==='function')_syncWorkspaceTerminalHostLocation();"
        in terminal
    )
    assert terminal.count(
        "if(typeof _syncWorkspaceTerminalHostLocation==='function')_syncWorkspaceTerminalHostLocation();"
    ) >= 2, "open and close paths must both resync the host location"


def test_hosted_terminal_suppresses_transcript_space_reservation():
    terminal = _terminal_js()
    sync_start = terminal.find("function _syncTerminalTranscriptSpace(")
    assert sync_start != -1
    sync = terminal[sync_start : sync_start + 800]
    assert "TERMINAL_UI.hosted" in sync
    assert "if(open&&TERMINAL_UI.hosted)return;" in sync

    ui_state = terminal[: terminal.find("function _terminalEls()")]
    assert "hosted:false," in ui_state


def test_hosted_mode_css_removes_overlay_chrome():
    css = (REPO_ROOT / "static" / "style.css").read_text(encoding="utf-8")
    assert ".workspace-terminal .composer-terminal-panel" in css
    assert "position:static" in css
    assert ".workspace-terminal .composer-terminal-resize-handle" in css
    assert "workspace-terminal-frame" not in css
