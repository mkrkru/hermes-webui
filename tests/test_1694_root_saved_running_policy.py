"""Regression tests for #1694 root boot policy around saved running sessions.

The active pane is only a projection. A root `/` tab must never project into
a saved session: boot restores ONLY a session explicitly present in the URL
(``/session/<sid>`` or ``?session=``). The ``hermes-webui-session``
localStorage key stays a write-through record so the ``storage`` event can
refresh the sidebar in other tabs, but it is no longer a boot restore source.

Explicit ``/session/<sid>`` reload still restores and reattaches to the
requested session, including running ones.
"""

from pathlib import Path


REPO = Path(__file__).parent.parent
BOOT_JS = (REPO / "static" / "boot.js").read_text(encoding="utf-8")
SESSIONS_JS = (REPO / "static" / "sessions.js").read_text(encoding="utf-8")


def _boot_saved_session_block() -> str:
    marker = "const urlSession="
    start = BOOT_JS.find(marker)
    assert start > 0, "boot saved-session restore block not found"
    end_marker = "// no saved session"
    end = BOOT_JS.find(end_marker, start)
    assert end > start, "no-saved-session marker not found after restore block"
    return BOOT_JS[start:end]


def test_root_boot_restores_only_url_sessions():
    """Root `/` boot must not consult localStorage for a session to restore."""
    block = _boot_saved_session_block()
    compact = block.replace(" ", "")
    assert "constsaved=urlSession;" in compact, (
        "boot must restore only a session explicitly present in the URL "
        "(/session/<id> or ?session=), never the last localStorage session"
    )
    assert "urlSession||savedLocal" not in compact, (
        "localStorage must not be a fallback restore source on boot"
    )


def test_explicit_session_url_still_restores_via_load_session():
    """`/session/<sid>` reload must still project the requested session."""
    block = _boot_saved_session_block()
    saved_pos = block.find("const saved=urlSession;")
    load_pos = block.find("await loadSession(saved, {preserveActiveInput:true})")
    assert saved_pos >= 0, "URL-only restore decision not found"
    assert load_pos > saved_pos, "restore must run after the URL-only decision"


def test_saved_running_metadata_helper_removed_from_boot():
    """The archived/running saved-session helper is obsolete and must be gone."""
    assert "_savedSessionSidebarOnlyState" not in BOOT_JS, (
        "the saved-running sidebar-only helper no longer exists: root boot "
        "never restores a saved session, so there is nothing to check"
    )
    assert "!urlSession&&savedLocal" not in BOOT_JS, (
        "no root-path branch may depend on the saved localStorage session"
    )


def test_localstorage_key_remains_write_through_for_cross_tab_sync():
    """Session switches must keep writing the key for the `storage` event."""
    assert "localStorage.setItem('hermes-webui-session',S.session.session_id)" in SESSIONS_JS
    assert "_handleActiveSessionStorageEvent" in SESSIONS_JS


def test_root_saved_session_lands_on_empty_state_without_restore():
    """Root boot with a stale saved pointer must still land on the new chat."""
    no_saved = BOOT_JS.find("// no saved session")
    assert no_saved > 0, "no-saved-session boot branch not found"
    empty_pos = BOOT_JS.find("$('emptyState').style.display=''", no_saved)
    render_pos = BOOT_JS.find("await renderSessionList()", no_saved)
    assert empty_pos > no_saved, "root boot must show the empty new-chat state"
    assert render_pos > no_saved, "root boot must still render the session sidebar"
