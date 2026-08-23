"""White portal figure replaces the caduceus logo on the new-chat page.

The artwork (from the Hermes Agent site footer, web-assets.nousresearch.com)
is preprocessed to white line-art with transparency and ships in all themes.
The original SVG logo stays in the DOM but is hidden via CSS.
"""

from pathlib import Path

REPO = Path(__file__).parent.parent
INDEX_HTML = (REPO / "static" / "index.html").read_text(encoding="utf-8")
CSS = (REPO / "static" / "style.css").read_text(encoding="utf-8")


def test_portal_figure_is_in_the_empty_logo_slot():
    assert '</svg><img class="empty-portal-figure" src="static/portal-figure-white.webp"' in INDEX_HTML, (
        "the white portal figure must sit inside .empty-logo right after the hidden svg"
    )
    assert 'alt="" aria-hidden="true"' in INDEX_HTML


def test_portal_figure_asset_ships_and_is_webp():
    asset = REPO / "static" / "portal-figure-white.webp"
    assert asset.is_file(), "portal figure asset must ship at static/portal-figure-white.webp"
    assert asset.stat().st_size > 100_000, "portal figure asset looks truncated"
    head = asset.read_bytes()[:12]
    assert head[:4] == b"RIFF" and head[8:12] == b"WEBP", "asset must be a valid WEBP"


def test_logo_svg_is_hidden_and_figure_is_styled():
    assert ".empty-logo svg{display:none;}" in CSS, (
        "the caduceus svg must be hidden so the figure replaces it visually"
    )
    assert ".empty-portal-figure{position:relative;z-index:1;display:block;width:96px;height:auto;margin:0 auto;" in CSS, (
        "figure sizing/styling rule missing"
    )
    assert ":root:not(.dark) .empty-portal-figure{filter:drop-shadow(0 0 14px rgba(15,20,40,.30));}" in CSS, (
        "light themes need a soft dark halo so the white figure stays visible on paper"
    )
