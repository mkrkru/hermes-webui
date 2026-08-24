"""Static regressions for slash-command direct execution and all-steer display."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOT_JS = (ROOT / "static" / "boot.js").read_text(encoding="utf-8")
COMMANDS_JS = (ROOT / "static" / "commands.js").read_text(encoding="utf-8")


def test_slash_exact_command_executes_directly_on_enter():
    assert "function _slashCommandNameIsExact(" in COMMANDS_JS
    assert (
        "if(typeof _slashCommandNameIsExact==='function'&&_slashCommandNameIsExact(_cmdText))"
        in BOOT_JS
    )
    # Direct execution must run the command (send) rather than pick from the dropdown.
    assert "hideCmdDropdown();" in BOOT_JS
    assert "send();" in BOOT_JS


def test_steer_indicator_accumulates_not_replaces():
    # The old "remove any existing steer indicator" block is gone, so every steer stacks.
    assert "inner.querySelector('.steer-indicator')" not in COMMANDS_JS


def test_queued_steer_is_surfaced_in_chat():
    # The gateway-queued fallback now renders a visible steer indicator too.
    assert "_showSteerIndicator(_steerIndicatorText(originalMsg,pendingFilesSnapshot))" in COMMANDS_JS
