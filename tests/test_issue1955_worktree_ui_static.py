from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_session_new_route_accepts_worktree_flag_and_uses_worktree_info():
    src = read("api/routes.py")
    assert "create_worktree_for_workspace" in src
    assert 'body.get("worktree")' in src or "body.get('worktree')" in src
    assert "worktree_info=" in src


def test_new_session_request_can_include_worktree_flag():
    src = read("static/sessions.js")
    assert "async function newSession(flash, options={})" in src
    # Three-value contract (#6022): explicit true/false forwarded verbatim,
    # absent key omitted so the server applies the config default.
    assert "reqBody.worktree=!!options.worktree" in src


def test_workspace_dropdown_inlines_workspaces_and_drops_footer_actions():
    src = read("static/panels.js")
    # The three footer actions were removed from the dropdown: the worktree
    # action, the "choose path" prompt, and the bottom "Manage workspaces" row.
    assert "workspace_new_worktree_conversation" not in src
    assert "newSession(false,{worktree:true})" not in src
    assert "workspace_choose_path" not in src
    # Workspaces render inline in the dropdown — no nested scroll container.
    assert "ws-list-container" not in src
    # "Manage workspaces" now lives behind a gear button in the search row.
    assert "ws-search-settings" in src
    assert "mobileSwitchPanel('workspaces')" in src


def test_session_sidebar_renders_worktree_indicator():
    src = read("static/sessions.js")
    assert "session-worktree-indicator" in src
    assert "s.worktree_path" in src
    assert "s.worktree_branch" in src


def test_worktree_indicator_styles_and_i18n_exist():
    css = read("static/style.css")
    i18n = read("static/i18n.js")
    assert ".session-worktree-indicator" in css
    assert "workspace_new_worktree_conversation" in i18n
    assert "session_worktree_badge" in i18n
