from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
STYLE_CSS = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
PANELS_JS = (ROOT / "static" / "panels.js").read_text(encoding="utf-8")
UI_JS = (ROOT / "static" / "ui.js").read_text(encoding="utf-8")


def test_app_titlebar_no_longer_contains_tps_chip():
    assert 'id="tpsStat"' not in INDEX_HTML


def test_app_titlebar_returns_to_centered_desktop_layout():
    assert ".app-titlebar{display:flex;align-items:center;justify-content:center;" in STYLE_CSS
    assert ".app-titlebar-inner{display:flex;align-items:center;gap:8px;min-width:0;max-width:100%;justify-content:center;}" in STYLE_CSS


def test_app_titlebar_hidden_on_desktop_kept_on_mobile():
    """Top bar removed on desktop (rail is the nav there); phone titlebar stays for the hamburger."""
    idx_media = STYLE_CSS.index("@media(min-width:641px){")
    idx_hide = STYLE_CSS.index(".app-titlebar{display:none;}", idx_media)
    assert idx_hide > idx_media, "desktop hide rule must live inside the min-width:641px block"
    # The base (mobile) titlebar rule must remain for the <641px hamburger.
    assert ".app-titlebar{display:flex;align-items:center;justify-content:center;" in STYLE_CSS


def test_app_titlebar_subtitle_shows_message_count_again():
    assert "subText = String(vis.length);" in PANELS_JS


def test_queue_updates_do_not_hijack_app_titlebar_subtitle():
    assert "_syncQueueTitlebar" not in UI_JS
