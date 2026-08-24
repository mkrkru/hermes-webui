"""Composer focus on session open.

Opening any chat (navigating to a session) must focus the message composer so
the user can type immediately — the same behaviour as the boot-page autofocus.
Same-session refreshes are background/external reconciles and must NOT steal
focus from wherever the user is currently working, so the focus call is gated
on a real cross-session navigation.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SESSIONS_JS = (REPO_ROOT / "static" / "sessions.js").read_text(encoding="utf-8")


def test_load_session_focuses_composer_on_cross_session_navigation():
    assert "function _focusComposerOnChatPage()" in (
        REPO_ROOT / "static" / "boot.js"
    ).read_text(encoding="utf-8"), "boot composer-focus helper missing"
    # The focus is wired into the shared session-open chokepoint.
    assert "typeof _focusComposerOnChatPage === 'function'" in SESSIONS_JS, (
        "loadSession must focus the composer via the shared boot helper"
    )
    # Gated on a real navigation: same-session (background/external) refreshes
    # reuse currentSid and must not steal focus.
    assert "currentSid !== sid && typeof _focusComposerOnChatPage === 'function'" in SESSIONS_JS, (
        "composer autofocus must be gated on cross-session navigation"
    )
