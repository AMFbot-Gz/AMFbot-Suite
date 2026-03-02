/* ═══════════════════════════════════════════════════════════
   JARVIS ANTIGRAVITY — Frontend Logic
   ═══════════════════════════════════════════════════════════ */

'use strict';

// ── Tab switching ──────────────────────────────────────────
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + target)?.classList.add('active');

    // Lazy-load on first switch
    if (target === 'dashboard') loadDashboard();
    if (target === 'skills') loadSkills();
    if (target === 'settings') loadConfig();
  });
});

// ── Utility ────────────────────────────────────────────────
function escHtml(s) {
  return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val ?? '—';
}

// ── Status ─────────────────────────────────────────────────
const STATE_COLORS = {
  IDLE:       '#4adf8a',
  LISTENING:  '#4a8fff',
  PROCESSING: '#f0c040',
  SPEAKING:   '#a78fff',
  EXECUTING:  '#4a8fff',
  CONFIRMING: '#f0c040',
  ERROR:      '#ff4a6a',
  SHUTDOWN:   '#888',
  UNKNOWN:    '#888',
};

async function loadStatus() {
  try {
    const r = await fetch('/api/status');
    if (!r.ok) return;
    const d = await r.json();

    const state = d.status || 'UNKNOWN';
    setEl('state', state);
    setEl('state-badge', state);
    setEl('skills-count', d.skills_count);
    setEl('history-count', d.history_count);
    setEl('start-time', (d.start_time || '').slice(0, 16).replace('T', ' '));

    // Status dot color
    const dot = document.getElementById('dot');
    const badge = document.getElementById('state-badge');
    const col = STATE_COLORS[state] || '#888';
    if (dot)   { dot.style.background = col; dot.style.boxShadow = `0 0 10px ${col}`; }
    if (badge) { badge.style.color = col; }

    // Cache stats
    const c = d.cache || {};
    setEl('cache-size', c.size);
    setEl('cache-max', c.max_size);
    setEl('cache-hit', c.hit_rate != null ? c.hit_rate + '%' : '—');
    setEl('cache-hits', c.hits);
    setEl('cache-misses', c.misses);
    setEl('cache-evictions', c.evictions);
    setEl('cache-ttl', c.ttl_seconds != null ? c.ttl_seconds + 's' : '—');

    const pct = (c.size && c.max_size) ? (c.size / c.max_size * 100).toFixed(1) : 0;
    const fill = document.getElementById('cache-bar-fill');
    if (fill) fill.style.width = pct + '%';

    // Last update
    setEl('last-update', new Date().toLocaleTimeString());
  } catch (e) {
    console.warn('[JARVIS] status error:', e);
  }
}

// ── History ────────────────────────────────────────────────
async function loadHistory() {
  try {
    const r = await fetch('/api/history');
    if (!r.ok) return;
    const d = await r.json();
    const el = document.getElementById('history-list');
    if (!el) return;
    if (!d.history?.length) { el.textContent = 'Aucune interaction encore.'; return; }
    el.innerHTML = [...d.history].reverse().map(h => `
      <div class="history-item">
        <div class="ts">${escHtml(h.ts)}</div>
        <div class="user">▶ ${escHtml(h.user_input)}</div>
        <div class="response">${escHtml((h.response || '').slice(0, 200))}</div>
      </div>
    `).join('');
  } catch (e) {
    console.warn('[JARVIS] history error:', e);
  }
}

async function loadDashboard() {
  await Promise.all([loadStatus(), loadHistory()]);
}

// ── Skills ─────────────────────────────────────────────────
let _allSkills = [];

async function loadSkills() {
  try {
    const r = await fetch('/api/skills');
    if (!r.ok) return;
    const d = await r.json();
    _allSkills = d.skills || [];
    setEl('skills-total', d.count ?? _allSkills.length);
    renderSkills(_allSkills);
  } catch (e) {
    console.warn('[JARVIS] skills error:', e);
  }
}

function renderSkills(skills) {
  const el = document.getElementById('skills-list');
  if (!el) return;
  if (!skills.length) { el.textContent = 'Aucun skill trouvé.'; return; }
  el.innerHTML = `<div class="skills-table-wrap">${skills.map(s => `
    <div class="skill-row">
      <div class="skill-info">
        <div class="skill-name">${escHtml(s.name)}</div>
        <div class="skill-desc">${escHtml(s.description)}</div>
      </div>
      <span class="badge badge-${escHtml(s.risk_level)}">${escHtml(s.risk_level)}</span>
    </div>
  `).join('')}</div>`;
}

// Skills search filter
document.getElementById('skills-search')?.addEventListener('input', function () {
  const q = this.value.toLowerCase();
  renderSkills(_allSkills.filter(s =>
    s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q)
  ));
});

// ── Config ─────────────────────────────────────────────────
async function loadConfig() {
  try {
    const r = await fetch('/api/config');
    if (!r.ok) return;
    const d = await r.json();
    const llm = document.getElementById('cfg-llm');
    const voice = document.getElementById('cfg-tts-voice');
    const speed = document.getElementById('cfg-tts-speed');
    if (llm && d.llm) llm.value = d.llm.model || '';
    if (voice && d.tts) voice.value = d.tts.voice || '';
    if (speed && d.tts) speed.value = d.tts.speed || 1.0;
  } catch (e) { /* config might not be available yet */ }
}

async function saveConfig() {
  const payload = {
    llm_model: document.getElementById('cfg-llm')?.value || null,
    tts_voice: document.getElementById('cfg-tts-voice')?.value || null,
    tts_speed: parseFloat(document.getElementById('cfg-tts-speed')?.value) || null,
  };
  try {
    const r = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (r.ok) {
      const msg = document.getElementById('save-msg');
      if (msg) { msg.style.display = 'block'; setTimeout(() => msg.style.display = 'none', 3000); }
    }
  } catch (e) { alert('Erreur lors de la sauvegarde : ' + e); }
}

// ── Cache ──────────────────────────────────────────────────
async function clearCache() {
  if (!confirm('Vider le cache LRU ?')) return;
  await fetch('/api/cache', { method: 'DELETE' });
  await loadStatus();
}

// ── Chat scroll ────────────────────────────────────────────
function scrollChatToBottom() {
  const chat = document.getElementById('chat-messages');
  if (chat) chat.scrollTop = chat.scrollHeight;
}

// HTMX: scroll after chat response is inserted
document.body.addEventListener('htmx:afterSwap', evt => {
  if (evt.detail.target?.id === 'chat-messages') {
    scrollChatToBottom();
  }
});

// Chat input: submit on Enter
document.querySelector('.chat-input')?.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    e.target.closest('form')?.dispatchEvent(new Event('submit', { bubbles: true }));
  }
});

// ── Init ───────────────────────────────────────────────────
loadStatus();

// Auto-refresh status every 5s
setInterval(loadStatus, 5000);

// Auto-refresh history every 15s (only when dashboard tab is visible)
setInterval(() => {
  const dashTab = document.getElementById('tab-dashboard');
  if (dashTab?.classList.contains('active')) loadHistory();
}, 15000);
