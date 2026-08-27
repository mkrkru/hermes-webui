"""Regression coverage for steer edit preservation + per-steer delete.

While a steer indicator's edit input is open, the indicator must survive the
next ``tool_complete`` (which calls ``_dismissSteerIndicators``) so the user's
edit is not dropped and subsequent steers stay queued. A delete button removes
only that steer: the backend keeps a single pending-steer buffer, so deleting
one steer rewrites the buffer to the remaining steers (or cancels when none).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMMANDS_JS = ROOT / "static" / "commands.js"
STYLE_CSS = ROOT / "static" / "style.css"
I18N_JS = ROOT / "static" / "i18n.js"
NODE = shutil.which("node")

node_test = pytest.mark.skipif(NODE is None, reason="node not on PATH")


def _cmds() -> str:
    return COMMANDS_JS.read_text(encoding="utf-8")


def test_dismiss_steer_indicators_preserves_active_edit():
    src = _cmds()
    assert "function _dismissSteerIndicators()" in src
    assert "if(el.dataset.editing==='1'){ editing=true; return; }" in src
    # Must not blanket-reset edit state while an edit is open.
    assert "if(!editing){" in src


def test_delete_button_is_wired():
    src = _cmds()
    assert "steer-edit-delete" in src
    assert "li('trash-2',12)" in src
    assert "function _deleteSteerEdit(el)" in src
    assert "function _remainingPendingSteerTexts(excludeEl)" in src
    assert "_steerModeRequest('replace',remaining.join('\\n'))" in src
    assert "_steerModeRequest('cancel')" in src
    # Blur must not fire a commit before the delete/cancel click runs.
    assert "let suppressBlurCommit=false;" in src


def test_delete_button_styles_exist():
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert ".steer-edit-delete{" in css
    assert ".steer-edit-delete:hover{" in css


def test_steer_delete_i18n_key_added_to_en():
    i18n = I18N_JS.read_text(encoding="utf-8")
    assert "steer_delete: 'Delete steer'," in i18n


def test_steer_indicators_persist_across_reload():
    src = _cmds()
    # Pending steer indicators are persisted per session and restored on load so
    # a mid-run page reload doesn't drop queued steers.
    assert "function _syncSteerIndicatorsPersistence(sid)" in src
    assert "function _restoreSteerIndicators(sid)" in src
    assert "hermes-steer-indicators-" in src
    assert "sessionStorage" in src
    sessions_js = (ROOT / "static" / "sessions.js").read_text(encoding="utf-8")
    assert "if(typeof _restoreSteerIndicators==='function') _restoreSteerIndicators(sid);" in sessions_js


def _delete_block() -> str:
    src = _cmds()
    start = src.index("function _remainingPendingSteerTexts")
    end = src.index("async function _flushSteerQueue")
    return src[start:end]


def _run_delete_case(texts, target_index):
    block = _delete_block()
    driver = textwrap.dedent(
        f"""
        const calls = [];
        let _steerEditActive = false;
        let _steerQueue = [];
        const indicators = [];
        function makeIndicator(text){{
          const el = {{
            dataset: {{steerText: text, editing: ''}},
            removed: false,
            remove() {{ this.removed = true; }},
          }};
          indicators.push(el);
          return el;
        }}
        {chr(10).join(f"const i{n} = makeIndicator({json.dumps(t)});" for n, t in enumerate(texts))}
        global.document = {{
          getElementById(id) {{
            return {{
              querySelectorAll(sel) {{ return indicators.slice(); }},
            }};
          }},
        }};
        async function _steerModeRequest(mode, text) {{
          calls.push({{mode, text}});
          return {{accepted:true}};
        }}
        function _flushSteerQueue() {{ calls.push({{flush:true}}); }}

        {block}

        (async () => {{
          _steerEditActive = true;
          await _deleteSteerEdit(indicators[{target_index}]);
          console.log('RESULT:' + JSON.stringify({{calls, removed: indicators[{target_index}].removed}}));
        }})().catch(err => {{ console.error(err && err.stack || err); process.exit(1); }});
        """
    )
    result = subprocess.run(
        [NODE, "-e", driver], cwd=ROOT, text=True, capture_output=True, timeout=30, check=False
    )
    assert result.returncode == 0, result.stderr or result.stdout
    out = result.stdout.strip().splitlines()[-1]
    assert out.startswith("RESULT:")
    return json.loads(out[len("RESULT:"):])


@node_test
def test_delete_steer_rewrites_pending_buffer():
    data = _run_delete_case(["steer one", "steer two", "steer three"], 1)
    assert data["removed"] is True
    assert {"mode": "replace", "text": "steer one\nsteer three"} in data["calls"]


@node_test
def test_delete_last_steer_cancels_pending_buffer():
    data = _run_delete_case(["only steer"], 0)
    assert data["removed"] is True
    assert {"mode": "cancel"} in data["calls"]
    assert not any(c.get("mode") == "replace" for c in data["calls"])
