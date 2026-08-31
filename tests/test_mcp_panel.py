"""String-pin tests for the MCP panel (WebUI tab for managing MCP servers).

Pins:
1. Backend endpoint registration in api/routes.py — GET /api/mcp/servers
   (list) and PUT /api/mcp/servers/<name> (add/update, surgical YAML save).
2. The reload-mcp trigger in static/mcp-panel.js — after a successful save the
   panel must route through the same code path the built-in /reload-mcp chat
   command uses (executeAgentCommand → POST /api/commands/exec with
   command '/reload-mcp').
3. Panel registration touchpoints (nav tabs, main-view visibility, panels.js
   registry, i18n keys) so a partial revert cannot go unnoticed.
"""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).parent.parent
ROUTES = ROOT / "api" / "routes.py"
INDEX = ROOT / "static" / "index.html"
PANELS = ROOT / "static" / "panels.js"
MCP_PANEL_JS = ROOT / "static" / "mcp-panel.js"
MCP_PANEL_CSS = ROOT / "static" / "mcp-panel.css"
I18N = ROOT / "static" / "i18n.js"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# ── 1. Backend endpoint registration ─────────────────────────────────────────


def test_get_mcp_servers_route_registered():
    src = _read(ROUTES)
    assert 'if parsed.path == "/api/mcp/servers":' in src
    assert "return _handle_mcp_servers_list(handler)" in src


def test_put_mcp_server_update_route_registered():
    src = _read(ROUTES)
    assert 'if parsed.path.startswith("/api/mcp/servers/"):' in src
    assert "return _handle_mcp_server_update(handler, name, body)" in src


def test_mcp_update_saves_surgically_and_reloads_config():
    """The add/update handler must save via the surgical YAML writer and reload."""
    src = _read(ROUTES)
    assert "_save_yaml_config_file(_get_config_path(), cfg)" in src
    assert "reload_config()" in src


# ── 2. reload-mcp trigger after save ─────────────────────────────────────────


def test_mcp_panel_saves_via_put_endpoint():
    js = _read(MCP_PANEL_JS)
    assert "api('/api/mcp/servers/' + encodeURIComponent(name)" in js
    assert "method: 'PUT'" in js


def test_mcp_panel_triggers_reload_after_save():
    js = _read(MCP_PANEL_JS)
    # The save flow calls the reload simulation after a successful save.
    assert "await _triggerMcpReload();" in js
    # The reload routes through the built-in /reload-mcp command path.
    assert "const MCP_RELOAD_COMMAND = '/reload-mcp';" in js
    assert "await executeAgentCommand(text, { name: 'reload-mcp' });" in js


def test_mcp_panel_reload_fallback_matches_command_transport():
    """Without executeAgentCommand the fallback must hit /api/commands/exec."""
    js = _read(MCP_PANEL_JS)
    assert "api('/api/commands/exec', {" in js
    assert "body: JSON.stringify({ command: text })" in js


def test_mcp_panel_echoes_reload_as_chat_messages():
    """The simulated command echoes user/assistant messages like the real path."""
    js = _read(MCP_PANEL_JS)
    assert "S.messages.push({ role: 'user', content: text" in js
    assert "S.messages.push({ role: 'assistant', content: String(output || '(no output)')" in js


# ── 3. Panel registration touchpoints ────────────────────────────────────────


def test_index_html_registers_both_nav_tabs():
    html = _read(INDEX)
    assert html.count('data-panel="mcp"') >= 2, "rail and sidebar-nav tabs required"
    assert "switchPanel('mcp',{fromRailClick:true})" in html
    assert 'id="panelMcp"' in html
    assert 'id="mainMcp"' in html


def test_index_html_links_panel_assets():
    html = _read(INDEX)
    assert 'href="static/mcp-panel.css' in html
    assert 'src="static/mcp-panel.js' in html


def test_panels_js_registers_mcp_panel():
    js = _read(PANELS)
    assert "'mcp','plugin'" in js  # MAIN_VIEW_PANELS entry
    assert "mcp: 'tab_mcp'" in js  # APP_TITLEBAR_KEYS entry
    assert "if (nextPanel === 'mcp' && typeof loadMcpPanel === 'function') await loadMcpPanel();" in js
    assert "new Set(['chat','settings','mcp'])" in js  # _ALWAYS_VISIBLE_TABS


def test_main_view_visibility_rules_present():
    css = _read(MCP_PANEL_CSS)
    assert "main.main > #mainMcp{display:none;}" in css
    assert ":not(.showing-mcp) > #mainChat{display:flex;}" in css
    assert "main.main.showing-mcp > #mainMcp{display:flex;}" in css


def test_i18n_keys_present_in_en_and_ru():
    src = _read(I18N)
    for key in ("tab_mcp", "mcp_title", "mcp_add", "mcp_form_command"):
        assert f"{key}:" in src
    assert "mcp_title: 'MCP Servers'" in src
    assert "mcp_title: 'MCP-серверы'" in src
