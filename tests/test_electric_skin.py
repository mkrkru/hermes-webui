"""Electric skin registration and electric-blue/lime palette affordances.

The skin mirrors the Hermes Agent site design language
(https://hermes-agent.nousresearch.com/): dark mode is the signature solid
electric-blue canvas (#0000F2) with an acid-lime accent (#EDFF45) and navy
docs surfaces (#0F0F18); light mode is blue-on-paper (#0000F2 accent on white).
"""

from pathlib import Path

REPO = Path(__file__).parent.parent
CSS = (REPO / "static" / "style.css").read_text(encoding="utf-8")
BOOT_JS = (REPO / "static" / "boot.js").read_text(encoding="utf-8")
CONFIG_PY = (REPO / "api" / "config.py").read_text(encoding="utf-8")
INDEX_HTML = (REPO / "static" / "index.html").read_text(encoding="utf-8")
SHARE_HTML = (REPO / "static" / "share.html").read_text(encoding="utf-8")
I18N_JS = (REPO / "static" / "i18n.js").read_text(encoding="utf-8")


def test_electric_skin_is_registered_in_all_files():
    assert "{name:'Electric'" in BOOT_JS
    assert "electric:1" in INDEX_HTML
    assert "electric:1" in SHARE_HTML
    assert '"electric"' in CONFIG_PY


def test_electric_light_variant_is_blue_on_paper():
    assert ':root[data-skin="electric"]{' in CSS
    assert "--bg:#FFFFFF" in CSS
    assert "--accent:#0000F2" in CSS
    assert "--accent-hover:#0029DE" in CSS
    assert "--border:#ECEAF5" in CSS


def test_electric_dark_variant_is_blue_canvas_with_lime_accent():
    assert ':root.dark[data-skin="electric"]{' in CSS
    assert "--bg:#0000F2" in CSS
    assert "--sidebar:#0F0F18" in CSS
    assert "--accent:#EDFF45" in CSS
    assert "--text:#F5F5F5" in CSS


def test_electric_dark_surfaces_override_default_navy_modals():
    assert ':root.dark[data-skin="electric"] .app-dialog' in CSS
    assert ':root.dark[data-skin="electric"] .kanban-modal' in CSS


def test_electric_dark_new_chat_button_is_lime_on_blue():
    assert ':root.dark[data-skin="electric"] .new-chat-btn' in CSS


def test_electric_i18n_lists_skin_in_all_locales():
    # 15 locales: 13 use ASCII closing paren, 2 CJK locales use full-width.
    assert I18N_JS.count("electric/verdigris)") + I18N_JS.count("electric/verdigris）") == 15
