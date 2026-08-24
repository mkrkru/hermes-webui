"""Static regressions for composer prompt-history navigation (ArrowUp/ArrowDown)."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOT_JS = (ROOT / "static" / "boot.js").read_text(encoding="utf-8")
MESSAGES_JS = (ROOT / "static" / "messages.js").read_text(encoding="utf-8")


def test_prompt_history_state_and_persistence():
    assert "_PROMPT_HISTORY_KEY='hermes-webui-prompt-history'" in BOOT_JS
    assert "function _recordPromptHistory(" in BOOT_JS
    assert "function _navigatePromptHistory(" in BOOT_JS
    assert "_persistPromptHistory" in BOOT_JS


def test_arrow_keys_navigate_history_when_dropdown_closed():
    assert "if(e.key==='ArrowUp'&&!e.shiftKey&&!e.isComposing&&!_imeComposing)" in BOOT_JS
    assert "_navigatePromptHistory(-1)" in BOOT_JS
    assert "_navigatePromptHistory(1)" in BOOT_JS


def test_caret_line_guards_preserve_multiline_editing():
    assert "function _isCaretOnFirstLine(" in BOOT_JS
    assert "function _isCaretOnLastLine(" in BOOT_JS


def test_send_records_prompt_history():
    assert "_recordPromptHistory(_submittedDraftTextForClear)" in MESSAGES_JS
