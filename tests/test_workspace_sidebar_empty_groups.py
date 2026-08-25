"""Regression coverage for workspace sidebar grouping + new-chat headers.

Empty registered workspaces must render as always-expanded sidebar group
headers so every configured workspace stays visible even when it has no chats
yet. Workspace headers are not collapsible: clicking one creates a new chat
bound to that workspace explicitly.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SESSIONS_JS = ROOT / "static" / "sessions.js"
STYLE_CSS = ROOT / "static" / "style.css"
NODE = shutil.which("node")

node_test = pytest.mark.skipif(NODE is None, reason="node not on PATH")


def _js() -> str:
    return SESSIONS_JS.read_text(encoding="utf-8")


def _extract_async_function(source: str, name: str) -> str:
    marker = f"async function {name}("
    start = source.find(marker)
    assert start >= 0, f"{name}() function must exist"
    brace = source.find("{", source.find(")", start))
    assert brace > start, f"{name}() function body must start"
    depth = 0
    in_string = None
    escaped = False
    in_line_comment = False
    in_block_comment = False
    for idx in range(brace, len(source)):
        ch = source[idx]
        nxt = source[idx + 1] if idx + 1 < len(source) else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
            continue
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == in_string:
                in_string = None
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            continue
        if ch in ("'", '"', "`"):
            in_string = ch
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[start : idx + 1]
    raise AssertionError(f"could not extract {name}()")


def test_new_session_reads_explicit_workspace_override():
    js = _js()
    assert (
        "const explicitWs=(options&&options.workspace)?String(options.workspace):null;"
        in js
    )
    assert (
        "const inheritWs=explicitWs||switchWs||sessionWs||(S._profileDefaultWorkspace||null);"
        in js
    )


def test_sidebar_grouping_includes_empty_registered_workspaces():
    js = _js()
    assert "typeof _workspaceList!=='undefined'&&Array.isArray(_workspaceList)" in js
    assert "wsGroups.push({label:label,path:p,items:[],isWorkspace:true});" in js
    # Still groups by workspace (not date buckets).
    assert "const unpinnedByWorkspace=[...unpinned].sort((a,b)=>" in js


def test_workspace_header_click_creates_new_chat():
    js = _js()
    assert "function _attachWorkspaceNewChatAction(hdr, wsPath)" in js
    assert "newSession(false,{workspace:wsPath})" in js
    assert "_attachWorkspaceNewChatAction(hdr,g.path)" in js
    assert "hdr.setAttribute('role','button')" in js


def test_workspace_groups_are_not_collapsible():
    js = _js()
    # Collapse machinery removed: no caret, no persisted collapsed state.
    assert "session-date-caret" not in js
    assert "_groupCollapsed" not in js
    assert "hermes-date-groups-collapsed" not in js
    # Always-expanded: the flat row builder no longer skips collapsed labels.
    assert "if(_groupCollapsed[g.label]) continue;" not in js


def test_workspace_header_styles_exist():
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert ".session-date-header .session-date-label" in css
    assert ".session-date-header.workspace{cursor:pointer;}" in css
    # The old "+" quick-create button styles are gone.
    assert ".session-date-quick-create" not in css
    assert ".session-date-caret" not in css


def _run_new_session_workspace_case(options: dict) -> dict:
    new_session = _extract_async_function(_js(), "newSession")
    driver = textwrap.dedent(
        f"""
        var _newSessionInFlight=null;
        var _messagesTruncated=false;
        var _oldestIdx=0;
        var _activeProject=null;
        var NO_PROJECT_FILTER='__all__';
        var _sessionSourceFilter='webui';
        var S={{
          session:{{session_id:'previous-session',workspace:'/current-workspace'}},
          _profileDefaultWorkspace:'/profile-default',
          _profileSwitchWorkspace:null,
          activeProfile:'default',
          toolCalls:[],
        }};
        global.window={{}};
        global.document={{createElement:()=>({{dataset:{{}},appendChild:()=>{{}}}})}};
        global.localStorage={{setItem:()=>{{}}}};
        function $(id){{return null;}}
        function _newSessionPendingText(){{return 'Creating';}}
        function _setNewSessionPending(){{}}
        function updateQueueBadge(){{}}
        function clearLiveToolCards(){{}}
        function api(path,opts){{
          captured={{path,body:JSON.parse(opts.body)}};
          return Promise.resolve({{session:{{session_id:'new-session',messages:[],workspace:captured.body.workspace,last_usage:{{}}}}}});
        }}
        function _rememberNewChatDraftSession(){{}}
        function _setActiveSessionUrl(){{}}
        function _setSessionViewedCount(){{}}
        function updateSendBtn(){{}}
        function setStatus(){{}}
        function setComposerStatus(){{}}
        function syncTopbar(){{}}
        function renderMessages(){{}}
        function loadDir(){{return Promise.resolve();}}
        {new_session}
        newSession(false, {json.dumps(options)}).then(()=>{{
          process.stdout.write(JSON.stringify(captured));
        }}).catch(err=>{{
          console.error(err && err.stack || err);
          process.exit(1);
        }});
        """
    )
    result = subprocess.run(
        [NODE, "-e", driver],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


@node_test
def test_new_session_explicit_workspace_wins_and_is_not_inherited():
    payload = _run_new_session_workspace_case({"workspace": "/explicit-workspace"})
    assert payload["path"] == "/api/session/new"
    assert payload["body"]["workspace"] == "/explicit-workspace"
    assert "workspace_inherited_from_prev_session" not in payload["body"]
    assert payload["body"]["prev_session_id"] == "previous-session"


@node_test
def test_new_session_without_override_still_inherits_current_workspace():
    payload = _run_new_session_workspace_case({})
    assert payload["body"]["workspace"] == "/current-workspace"
    assert payload["body"]["workspace_inherited_from_prev_session"] is True
