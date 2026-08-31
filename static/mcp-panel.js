// ── MCP panel ────────────────────────────────────────────────────────────────
// Read-only listing of the MCP servers configured in the Hermes Agent config
// (via GET /api/mcp/servers) plus an "Add server" form that writes the config
// through PUT /api/mcp/servers/<name> (surgical YAML edit on the backend).
//
// After a successful save the panel simulates the user sending the built-in
// `/reload-mcp` chat command: it routes through the exact same code path used
// by messages.js when the user types /reload-mcp (executeAgentCommand → POST
// /api/commands/exec) and echoes the user/assistant messages into the current
// chat exactly like the built-in command path does.
//
// Loaded as a classic deferred script after messages.js/commands.js, so the
// shared globals (api, t, showToast, S, executeAgentCommand, renderMessages)
// are available at call time. Every cross-module reference is guarded with
// typeof checks so a load-order change can never brick the panel.

const MCP_RELOAD_COMMAND = '/reload-mcp';

let _mcpServers = [];
let _mcpLoadedOnce = false;

function _mcpEscapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function _mcpTr(value) {
  return typeof t === 'function' ? t(value) : '';
}

function _mcpShowStatus(message, kind) {
  const el = document.getElementById('mcpStatus');
  if (!el) return;
  if (!message) { el.style.display = 'none'; el.textContent = ''; return; }
  el.textContent = message;
  el.classList.toggle('mcp-status--error', kind === 'error');
  el.classList.toggle('mcp-status--ok', kind === 'ok');
  el.style.display = '';
}

// Quote-aware tokenizer for the args input: splits on whitespace, honours
// single/double quotes so argument values may contain spaces.
function _mcpSplitArgs(text) {
  const out = [];
  let cur = '';
  let quote = '';
  for (const ch of String(text || '')) {
    if (quote) {
      if (ch === quote) quote = '';
      else cur += ch;
    } else if (ch === '"' || ch === "'") {
      quote = ch;
    } else if (/\s/.test(ch)) {
      if (cur) { out.push(cur); cur = ''; }
    } else {
      cur += ch;
    }
  }
  if (cur) out.push(cur);
  return out;
}

// Parse the optional env textarea: one KEY=VALUE per line.
function _mcpParseEnv(text) {
  const env = {};
  String(text || '').split(/\r?\n/).forEach(line => {
    const trimmed = line.trim();
    if (!trimmed) return;
    const eq = trimmed.indexOf('=');
    if (eq <= 0) return;
    const key = trimmed.slice(0, eq).trim();
    const value = trimmed.slice(eq + 1);
    if (key) env[key] = value;
  });
  return Object.keys(env).length ? env : null;
}

function _mcpFormatServer(srv) {
  const lines = [];
  if (srv.transport === 'http') {
    lines.push('url: ' + (srv.url || ''));
    if (srv.headers && Object.keys(srv.headers).length) {
      lines.push('headers: ' + JSON.stringify(srv.headers));
    }
  } else if (srv.transport === 'stdio') {
    lines.push('command: ' + (srv.command || ''));
    if (Array.isArray(srv.args) && srv.args.length) {
      lines.push('args: ' + JSON.stringify(srv.args));
    }
    if (srv.env && Object.keys(srv.env).length) {
      lines.push('env: ' + JSON.stringify(srv.env));
    }
  } else {
    lines.push(_mcpTr('mcp_invalid_config'));
  }
  return lines.join('\n');
}

function _mcpBadgeClass(status) {
  if (status === 'active') return 'mcp-badge mcp-badge--active';
  if (status === 'disabled') return 'mcp-badge mcp-badge--disabled';
  if (status === 'invalid_config') return 'mcp-badge mcp-badge--invalid';
  return 'mcp-badge';
}

function renderMcpList() {
  const listEl = document.getElementById('mcpServersList');
  const sideEl = document.getElementById('mcpSidebarList');
  if (!listEl && !sideEl) return;
  if (!Array.isArray(_mcpServers) || !_mcpServers.length) {
    const empty = '<div class="mcp-empty" data-i18n="mcp_empty">No MCP servers configured.</div>';
    if (listEl) listEl.innerHTML = empty;
    if (sideEl) sideEl.innerHTML = empty;
    return;
  }
  if (listEl) {
    listEl.innerHTML = _mcpServers.map(srv => (
      '<div class="mcp-row">' +
        '<div class="mcp-row-head">' +
          '<span class="mcp-row-name">' + _mcpEscapeHtml(srv.name) + '</span>' +
          '<span class="' + _mcpBadgeClass(srv.status) + '">' + _mcpEscapeHtml(srv.transport || '?') + '</span>' +
          '<span class="mcp-badge">' + _mcpEscapeHtml(srv.status || '') + '</span>' +
        '</div>' +
        '<div class="mcp-row-detail">' + _mcpEscapeHtml(_mcpFormatServer(srv)) + '</div>' +
      '</div>'
    )).join('');
  }
  if (sideEl) {
    sideEl.innerHTML = _mcpServers.map(srv => {
      const dot = srv.status === 'active' ? 'mcp-side-dot--active'
        : (srv.status === 'disabled' ? 'mcp-side-dot--disabled'
          : (srv.status === 'invalid_config' ? 'mcp-side-dot--invalid' : ''));
      return '<div class="mcp-side-row" title="' + _mcpEscapeHtml(srv.transport || '') + '">' +
        '<span class="mcp-side-dot ' + dot + '"></span>' +
        '<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + _mcpEscapeHtml(srv.name) + '</span>' +
      '</div>';
    }).join('');
  }
}

async function loadMcpPanel(force) {
  if (!force && _mcpLoadedOnce) { renderMcpList(); return; }
  try {
    const data = await api('/api/mcp/servers');
    _mcpServers = Array.isArray(data && data.servers) ? data.servers : [];
    _mcpLoadedOnce = true;
    _mcpShowStatus('');
    renderMcpList();
  } catch (e) {
    const listEl = document.getElementById('mcpServersList');
    if (listEl) listEl.innerHTML = '<div class="mcp-empty">' +
      _mcpEscapeHtml(_mcpTr('mcp_load_failed') + (e && e.message ? ': ' + e.message : '')) + '</div>';
  }
}

// Reveal the add form in the main view (used by the sidebar "Add server" button).
function openMcpAddForm() {
  if (typeof switchPanel === 'function') switchPanel('mcp');
  const form = document.getElementById('mcpAddForm');
  if (!form) return;
  form.scrollIntoView({ behavior: 'smooth', block: 'start' });
  const name = document.getElementById('mcpFormName');
  if (name) name.focus();
}

async function submitMcpAddForm(event) {
  if (event && typeof event.preventDefault === 'function') event.preventDefault();
  const nameEl = document.getElementById('mcpFormName');
  const commandEl = document.getElementById('mcpFormCommand');
  const argsEl = document.getElementById('mcpFormArgs');
  const envEl = document.getElementById('mcpFormEnv');
  const submitBtn = document.getElementById('mcpFormSubmit');
  if (!nameEl || !commandEl) return false;
  const name = String(nameEl.value || '').trim();
  const command = String(commandEl.value || '').trim();
  if (!name || !command) return false;
  // The backend PUT overwrites an existing server with the same name — confirm
  // so the "Add" form never silently replaces a configured server.
  if (_mcpServers.some(s => s && s.name === name) && typeof window !== 'undefined'
      && typeof window.confirm === 'function'
      && !window.confirm(_mcpTr('mcp_overwrite_confirm') + ' "' + name + '"?')) {
    return false;
  }
  const body = { command };
  const args = _mcpSplitArgs(argsEl && argsEl.value);
  if (args.length) body.args = args;
  const env = _mcpParseEnv(envEl && envEl.value);
  if (env && Object.keys(env).length) body.env = env;
  if (submitBtn) submitBtn.disabled = true;
  try {
    await api('/api/mcp/servers/' + encodeURIComponent(name), {
      method: 'PUT',
      body: JSON.stringify(body),
    });
    nameEl.value = ''; commandEl.value = '';
    if (argsEl) argsEl.value = '';
    if (envEl) envEl.value = '';
    await loadMcpPanel(true);
    _mcpShowStatus(_mcpTr('mcp_saved_reload'), 'ok');
    // Config changed on disk — make the running agent pick it up by simulating
    // the user sending the built-in /reload-mcp command in the current chat.
    await _triggerMcpReload();
    return true;
  } catch (e) {
    _mcpShowStatus(_mcpTr('mcp_save_failed') + (e && e.message ? ': ' + e.message : ''), 'error');
    return false;
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

// Simulate the user typing `/reload-mcp` in the current chat. This mirrors the
// built-in dispatch path in messages.js (_AGENT_COMMANDS_RUN_ON_WEBUI →
// executeAgentCommand → POST /api/commands/exec) including the user/assistant
// chat echo, so the reload behaves exactly as if the user had typed it.
async function _triggerMcpReload() {
  const text = MCP_RELOAD_COMMAND;
  try {
    if (typeof S !== 'undefined' && S && Array.isArray(S.messages)) {
      if (!S.session && typeof newSession === 'function') {
        try { await newSession(); } catch (_e) { /* fall through with no session */ }
      }
      S.messages.push({ role: 'user', content: text, _ts: Date.now() / 1000 });
    }
    let output;
    if (typeof executeAgentCommand === 'function') {
      // Same code path the built-in /reload-mcp command uses when the user
      // types it in the composer.
      output = await executeAgentCommand(text, { name: 'reload-mcp' });
    } else {
      // Fallback: identical transport to _runAgentCommandTransport.
      const data = await api('/api/commands/exec', {
        method: 'POST',
        body: JSON.stringify({ command: text }),
      });
      output = String((data && data.output) || '(no output)');
    }
    if (typeof S !== 'undefined' && S && Array.isArray(S.messages)) {
      S.messages.push({ role: 'assistant', content: String(output || '(no output)'), _ts: Date.now() / 1000 });
      if (typeof renderMessages === 'function') renderMessages();
    }
  } catch (e) {
    _mcpShowStatus(_mcpTr('mcp_reload_failed') + (e && e.message ? ': ' + e.message : ''), 'error');
    if (typeof S !== 'undefined' && S && Array.isArray(S.messages)) {
      S.messages.push({ role: 'assistant', content: String(_mcpTr('mcp_reload_failed')) + (e && e.message ? ': ' + e.message : ''), _ts: Date.now() / 1000 });
      if (typeof renderMessages === 'function') renderMessages();
    }
  }
}
