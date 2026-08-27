"""Regression coverage for the Activity (running-chats) panel.

Covers two behaviors: (1) the per-poll grid reconcile must NOT wipe/re-append
cards when the running set is unchanged (that reset every card's scroll to the
top every 2s), and (2) the "show details" toggle hides the gray supporting text
(tool results / thinking / system) while keeping the rectangular tool-call
plaques, with state persisted across reloads.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANELS_JS = ROOT / "static" / "panels.js"
STYLE_CSS = ROOT / "static" / "style.css"
INDEX_HTML = ROOT / "static" / "index.html"
I18N_JS = ROOT / "static" / "i18n.js"


def _panels() -> str:
    return PANELS_JS.read_text(encoding="utf-8")


def test_activity_grid_reconciles_without_resetting_scroll():
    js = _panels()
    # Stable set/order must skip the DOM rebuild entirely (no grid.textContent=''
    # on every poll), which was snapping every card back to the transcript top.
    assert "const orderSig = running.map(s => s.session_id).join('|');" in js
    assert "if (grid.dataset.orderSig === orderSig)" in js
    # On structural change, rebuild but preserve each surviving card's scroll.
    assert "const scrollBySid = new Map();" in js
    assert "for (const [sid, top] of scrollBySid)" in js
    assert "st.body.scrollTop = top" in js


def test_activity_show_details_toggle_persists():
    js = _panels()
    assert "ACTIVITY_SHOW_DETAILS_STORAGE_KEY" in js
    assert "function _restoreActivityShowDetails()" in js
    assert "function _applyActivityShowDetails()" in js
    assert "function toggleActivityDetails()" in js
    assert "_restoreActivityShowDetails();" in js
    assert "_applyActivityShowDetails();" in js
    # Hide gray supporting text, keep the rectangular tool-call plaques.
    assert "grid.classList.toggle('hide-details', !_activityShowDetails);" in js


def test_activity_toggle_wiring_and_css():
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert ".activity-grid.hide-details .activity-msg-other{display:none;}" in css
    assert ".activity-details-toggle" in css

    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="activityDetailsToggle"' in html
    assert 'onclick="toggleActivityDetails()"' in html

    i18n = I18N_JS.read_text(encoding="utf-8")
    assert "activity_toggle_details" in i18n


def test_activity_cards_layout_as_horizontal_columns():
    css = STYLE_CSS.read_text(encoding="utf-8")
    # Cards run left-to-right as fixed-width columns; when they no longer fit
    # (~4-5 on screen) the grid scrolls horizontally instead of wrapping.
    assert ".activity-grid{flex:1;min-height:0;display:flex;flex-direction:row" in css
    assert "flex-wrap:nowrap" in css
    assert "overflow-x:auto" in css
    assert ".activity-card{flex:0 0 300px" in css
