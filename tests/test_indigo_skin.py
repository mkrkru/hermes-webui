"""Indigo skin registration and soft deep-blue palette affordances."""

from pathlib import Path

REPO = Path(__file__).parent.parent
CSS = (REPO / "static" / "style.css").read_text(encoding="utf-8")
BOOT_JS = (REPO / "static" / "boot.js").read_text(encoding="utf-8")
CONFIG_PY = (REPO / "api" / "config.py").read_text(encoding="utf-8")
INDEX_HTML = (REPO / "static" / "index.html").read_text(encoding="utf-8")
SHARE_HTML = (REPO / "static" / "share.html").read_text(encoding="utf-8")


def test_indigo_skin_is_registered_in_all_files():
    assert "{name:'Indigo'" in BOOT_JS
    assert "indigo:1" in INDEX_HTML
    assert "indigo:1" in SHARE_HTML
    assert '"indigo"' in CONFIG_PY


def test_indigo_has_light_and_dark_variants():
    assert ':root[data-skin="indigo"]{' in CSS
    assert ':root.dark[data-skin="indigo"]{' in CSS


def test_indigo_dark_palette_is_soft_navy():
    assert "--bg:#0E1224" in CSS
    assert "--sidebar:#161B33" in CSS
    assert "--border:#2A3152" in CSS


def test_indigo_accent_is_softened_ultramarine():
    # Light variant: deeper for contrast on light surfaces.
    assert "--accent:#4653D8" in CSS
    assert "--accent-hover:#3743C0" in CSS
    # Dark variant: lighter, muted ultramarine instead of the raw #0100F2.
    assert "--accent:#6676E8" in CSS
    assert "--focus-ring:rgba(102,118,232,0.32)" in CSS


def test_indigo_primary_buttons_keep_white_text_in_dark_mode():
    assert (
        ':root.dark[data-skin="indigo"] .clarify-submit{color:#fff!important;}'
        in CSS
    )


def test_terracotta_block_is_unaffected():
    assert ':root[data-skin="terracotta"]{' in CSS
    assert "--accent:#D97757" in CSS
