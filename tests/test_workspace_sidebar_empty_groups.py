"""Regression coverage for workspace sidebar grouping + new-chat headers.

Empty registered workspaces must render as sidebar group headers so every
configured workspace stays visible even when it has no chats yet. Workspace
headers are card-style collapse toggles; a per-workspace "New chat" button
drops to the empty composer and creates the session lazily on the first send.
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


def test_workspace_header_toggles_collapse():
    js = _js()
    assert "function _attachWorkspaceToggleAction(hdr, wsPath)" in js
    assert "_workspaceCollapsed" in js
    assert "hdr.setAttribute('role','button')" in js
    assert "hdr.setAttribute('aria-expanded'" in js


def test_workspace_folder_grouping():
    js = _js()
    # Parent-directory grouping (one level) + folder collapse machinery.
    assert "function _workspaceParentDir(path)" in js
    assert "function _workspaceParentLeaf(parentDir)" in js
    assert "function _attachFolderToggleAction(hdr, path)" in js
    assert "_folderCollapsed" in js
    # Folder nodes only when a parent dir holds ≥2 workspaces.
    assert "if(fg.children.length>=2) treeNodes.push({label:fg.label,path:fg.path,isFolder:true,children:fg.children});" in js
    assert "const _renderFolderNode=(g)=>{" in js
    assert "const _renderWorkspaceNode=(g)=>{" in js
    # Flat row collection recurses into folder children.
    assert "if(g.isFolder&&Array.isArray(g.children))" in js


def test_workspace_new_chat_button_defers_session_creation():
    js = _js()
    assert "function _newChatInWorkspace(wsPath)" in js
    assert "S._profileSwitchWorkspace=wsPath||null;" in js
    assert "S.session=null; S.messages=[];" in js
    assert "function _attachWorkspaceNewChatAction(btn, wsPath)" in js
    assert "_attachWorkspaceNewChatAction(newChat,g.path)" in js
    assert "newChat.className='session-workspace-new-chat';" in js


def test_workspace_groups_are_collapsible():
    js = _js()
    # Re-introduced collapse machinery: caret toggle + in-memory collapsed state.
    assert "session-date-caret" in js
    assert "_workspaceCollapsed" in js
    # Old persisted-collapse machinery stays removed.
    assert "_groupCollapsed" not in js
    assert "hermes-date-groups-collapsed" not in js
    assert "if(_groupCollapsed[g.label]) continue;" not in js


def test_workspace_header_styles_exist():
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert ".session-date-header .session-date-label" in css
    assert ".session-date-header.workspace," in css
    assert ".session-date-header.folder{" in css
    assert ".session-date-header.workspace .session-date-icon," in css
    assert ".session-date-header.workspace .session-date-caret," in css
    assert ".session-date-group.collapsed .session-date-caret{transform:rotate(-90deg);}" in css
    assert ".session-date-group.collapsed .session-date-body{display:none;}" in css
    assert ".session-date-group.workspace-group>.session-date-body,.session-date-group.folder-group>.session-date-body{padding-left:14px;}" in css
    assert ".session-workspace-new-chat{" in css
    assert ".session-date-group.workspace-group .session-item{padding:6px 8px;}" in css
    # The old "+" quick-create button styles are gone.
    assert ".session-date-quick-create" not in css
    assert ".session-date-plus" not in css


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
