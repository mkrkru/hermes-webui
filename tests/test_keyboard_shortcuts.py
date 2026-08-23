"""Keyboard shortcuts on the chat page: Ctrl+C stop, Cmd/Ctrl+K composer focus,
and composer focus on boot.

Ctrl+C stops the active run (same effect as the Stop button) and is hijacked
ONLY while a stream is active, so normal copy-to-clipboard keeps working when
the chat is idle. Cmd/Ctrl+K focuses the composer — the legacy new-session
binding on this chord is gone.
"""

from pathlib import Path

REPO = Path(__file__).parent.parent
BOOT_JS = (REPO / "static" / "boot.js").read_text(encoding="utf-8")


def _keydown_block() -> str:
    start = BOOT_JS.find("document.addEventListener('keydown',async e=>{")
    assert start >= 0, "global keydown listener not found"
    end = BOOT_JS.find("});\nconst LARGE_TEXT_PASTE_CHAR_THRESHOLD", start)
    assert end > start, "keydown listener end marker not found"
    return BOOT_JS[start:end]


def test_ctrl_c_stops_active_run_and_is_idle_gated():
    block = _keydown_block()
    assert "if(e.ctrlKey&&!e.metaKey&&!e.shiftKey&&!e.altKey&&(e.key==='c'||e.key==='C')){" in block, (
        "Ctrl+C stop handler missing from the global keydown listener"
    )
    assert "cancelStream('keyboard-cancel')" in block, (
        "Ctrl+C must cancel the active stream"
    )
    assert "S.activeStreamId||S.busy" in block, (
        "Ctrl+C must be gated on an active stream so idle copy is never hijacked"
    )
    ctrl_c_pos = block.find("e.key==='c'||e.key==='C'")
    cancel_pos = block.find("cancelStream('keyboard-cancel')")
    active_pos = block.find("S.activeStreamId||S.busy")
    assert ctrl_c_pos < active_pos < cancel_pos, (
        "the active-stream guard must run before the cancel call"
    )


def test_cmd_k_only_focuses_composer_and_legacy_new_session_binding_is_gone():
    block = _keydown_block()
    assert "if((e.metaKey||e.ctrlKey)&&e.key==='k'){" in block, (
        "Cmd/Ctrl+K handler missing"
    )
    assert "const composer=$('msg');" in block, "Cmd/Ctrl+K must resolve the composer"
    assert "composer.focus();" in block, "Cmd/Ctrl+K must focus the composer"
    assert "await newSession();" not in block, (
        "legacy Cmd/Ctrl+K new-session behavior must be removed from the keydown "
        "listener (the + button keeps its own newSession call)"
    )


def test_boot_focuses_composer_on_chat_page():
    assert "function _focusComposerOnChatPage(){" in BOOT_JS, (
        "boot composer-focus helper missing"
    )
    helper_start = BOOT_JS.index("function _focusComposerOnChatPage(){")
    helper_end = BOOT_JS.index("// Mobile navigation.", helper_start)
    helper = BOOT_JS[helper_start:helper_end]
    assert "_isPhoneWidthViewport()" not in helper, (
        "composer autofocus must apply on phones too (user opted into the "
        "soft keyboard popping on mobile)"
    )
    focus_calls = BOOT_JS.count("_focusComposerOnChatPage();")
    assert focus_calls == 4, (
        "autofocus must be wired into every boot terminal path "
        f"(PWA fresh, zero-message, restored, no-saved; found {focus_calls})"
    )
