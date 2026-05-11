/**
 * feedback-widget.js v1.2 — drop-in chat-style per-page feedback collector.
 *
 * v1.2 changes (mobile-first):
 *   - Touch-aware element picker: drag highlights, tap selects, scroll allowed,
 *     two-finger tap cancels.
 *   - 44×44 touch targets via @media (pointer: coarse).
 *   - 16px font on textarea + name input on small viewports (suppresses iOS
 *     auto-zoom on focus).
 *   - env(safe-area-inset-bottom) padding so the sheet clears the iOS home
 *     indicator.
 *   - Mobile-flavoured picker banner copy ("Chạm vào chỗ muốn nói").
 *
 * v1.1 changes (richer context for AI agents):
 *   - Tag chips (type + severity).
 *   - Element pointer capture (CSS selector + bbox + html preview).
 *   - Auto context bundle (URL, viewport, last 20 actions, console errors,
 *     app meta via cfg.getContext).
 *   - cfg.fetchHeaders for CSRF tokens / custom auth.
 *
 * Single-file vanilla JS. No dependencies. Embeds CSS via injected <style>.
 * Mounts a floating "💬" button + slide-up bottom sheet on every page.
 *
 * Usage (HTML mockup / static site):
 *   <script>
 *     window.feedbackWidget = {
 *       endpoint: '/feedback',
 *       project: 'my-project-slug',
 *       primaryColor: '#1f3a5f',
 *       fabColor: '#047857'
 *     };
 *   </script>
 *   <script src="feedback-widget.js"></script>
 *
 * Usage (SPA — explicit mount):
 *   import './feedback-widget.js';
 *   FeedbackWidget.mount({endpoint: '/api/feedback', project: 'my-app'});
 *
 * Storage: localStorage key `fbw-{project}` for offline buffer + retry.
 * Server: POST <endpoint> with JSON body { project, screen_id, screen_name,
 *         message, submitter, ts, user_agent }. Server returns 200 on save.
 *
 * License: ISC. See ~/.claude/skills/feedback-widget/SKILL.md.
 */
(function (global) {
  'use strict';

  if (global.__FBW_LOADED__) return;
  global.__FBW_LOADED__ = true;

  // ---------- Defaults ----------
  const DEFAULTS = {
    endpoint: '/feedback',
    project: 'default',
    mode: 'client',                 // 'client' | 'audit'
    language: 'vi',                 // 'vi' | 'en'
    primaryColor: '#1f3a5f',
    fabColor: '#047857',
    fabIcon: '💬',
    position: 'bottom-right',       // 'bottom-right' | 'bottom-left'
    autoMount: true,
    // v1.1 — feature toggles (all default ON, host can disable per-deploy)
    enableTags: true,               // type + severity chips above textarea
    enablePointer: true,            // 📍 element-pointer button
    enableContext: true,            // auto-capture context bundle on send
    contextHistorySize: 20,         // ring-buffer length for actions + errors
    // v1.1 — host integration callbacks (all optional)
    getScreenId: null,              // () => string  (already in v1.0)
    getScreenName: null,            // () => string  (already in v1.0)
    getContext: null,               // () => object  — merged into ctx.app
    fetchHeaders: null,             // () => object  — extra headers per POST (e.g. CSRF)
  };

  // Tag groups — fixed list. Host should not extend (keeps server queries simple).
  const TAG_GROUPS = {
    vi: {
      type: [
        { v: 'bug',      l: '🐛 Lỗi' },
        { v: 'idea',     l: '💡 Ý tưởng' },
        { v: 'question', l: '❓ Hỏi' },
        { v: 'copy',     l: '✏️ Chữ' },
        { v: 'visual',   l: '🎨 Xấu' },
        { v: 'slow',     l: '🐢 Chậm' },
      ],
      severity: [
        { v: 'blocker',  l: '🔴 Chặn' },
        { v: 'annoying', l: '🟡 Khó chịu' },
        { v: 'nice',     l: '🟢 Có thì hay' },
      ],
    },
    en: {
      type: [
        { v: 'bug',      l: '🐛 Bug' },
        { v: 'idea',     l: '💡 Idea' },
        { v: 'question', l: '❓ Question' },
        { v: 'copy',     l: '✏️ Copy' },
        { v: 'visual',   l: '🎨 Looks off' },
        { v: 'slow',     l: '🐢 Slow' },
      ],
      severity: [
        { v: 'blocker',  l: '🔴 Blocking' },
        { v: 'annoying', l: '🟡 Annoying' },
        { v: 'nice',     l: '🟢 Nice-to-have' },
      ],
    },
  };

  const COPY = {
    vi: {
      fab_title: 'Góp ý cho màn này',
      sheet_eyebrow: 'Góp ý cho màn này',
      sheet_close: 'Đóng',
      empty_emoji: '💭',
      empty_text: 'Anh/chị thấy gì <strong>lạ / sai / thiếu / khó dùng</strong> ở màn này thì gõ vài chữ — em đọc tất.',
      empty_other_screens: 'Anh/chị đã góp ý ở {n} màn khác.',
      name_placeholder: 'Tên anh/chị (chỉ cần điền lần đầu)',
      msg_placeholder: 'Em đang xem màn này — anh/chị thấy gì lạ thì gõ vài chữ...',
      send_aria: 'Gửi',
      sending: 'Đang gửi...',
      sent_ok: '✓ Đã gửi · em sẽ xem',
      net_error: 'Mạng lỗi — đã lưu offline, sẽ gửi lại',
      anon: 'anh/chị',
      not_sent: 'chưa gửi',
      tag_type_eyebrow: 'Loại',
      tag_sev_eyebrow: 'Mức độ',
      pick_btn: '📍 Chỉ vào chỗ đang nói',
      pick_btn_short: '📍',
      pick_active: 'Bấm vào chỗ anh/chị muốn nói. ESC để hủy.',
      pick_active_touch: 'Chạm vào chỗ muốn nói (cuộn nếu cần) · chạm hai ngón để hủy',
      pick_clear_aria: 'Bỏ chọn',
    },
    en: {
      fab_title: 'Leave feedback on this screen',
      sheet_eyebrow: 'Feedback for this screen',
      sheet_close: 'Close',
      empty_emoji: '💭',
      empty_text: 'See anything <strong>odd / wrong / missing / awkward</strong>? Type a few words — I read everything.',
      empty_other_screens: 'You have left comments on {n} other screens.',
      name_placeholder: 'Your name (only on first comment)',
      msg_placeholder: "What's on your mind about this screen?",
      send_aria: 'Send',
      sending: 'Sending...',
      sent_ok: '✓ Sent · seen',
      net_error: 'Network error — saved offline, will retry',
      anon: 'you',
      not_sent: 'not sent yet',
      tag_type_eyebrow: 'Type',
      tag_sev_eyebrow: 'Severity',
      pick_btn: '📍 Point at element',
      pick_btn_short: '📍',
      pick_active: 'Click the element you mean. ESC to cancel.',
      pick_active_touch: 'Tap the element you mean (scroll if needed) · 2-finger tap to cancel',
      pick_clear_aria: 'Clear pick',
    },
  };

  // ---------- CSS (injected once) ----------
  const CSS = `
.fbw-fab {
  position: fixed;
  width: 48px; height: 48px; border-radius: 24px;
  border: 0; cursor: pointer;
  font-size: 22px; line-height: 1;
  color: white;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.25);
  display: flex; align-items: center; justify-content: center;
  z-index: 2147483600;
  transition: transform 0.12s ease;
}
.fbw-fab:active { transform: scale(0.94); }
.fbw-fab[data-pos="bottom-right"] { right: 14px; bottom: 14px; }
.fbw-fab[data-pos="bottom-left"]  { left: 14px;  bottom: 14px; }
.fbw-fab .fbw-dot {
  position: absolute; top: 6px; right: 6px;
  width: 9px; height: 9px;
  background: #ef4444;
  border: 2px solid white;
  border-radius: 5px;
  display: none;
}
.fbw-fab.fbw-has-msgs .fbw-dot { display: block; }

.fbw-backdrop {
  position: fixed; inset: 0;
  background: rgba(15, 23, 42, 0.35);
  display: none;
  z-index: 2147483601;
}
.fbw-backdrop.fbw-open { display: block; }

.fbw-sheet {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  background: white;
  border-radius: 18px 18px 0 0;
  max-height: 75vh; max-height: 75dvh;
  display: none;
  flex-direction: column;
  z-index: 2147483602;
  box-shadow: 0 -10px 32px rgba(0, 0, 0, 0.18);
  font: 14.5px -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", "Roboto", sans-serif;
  color: #1a1a1a;
  -webkit-font-smoothing: antialiased;
}
.fbw-sheet.fbw-open {
  display: flex;
  animation: fbw-slide-up 0.22s ease-out;
}
@keyframes fbw-slide-up { from { transform: translateY(100%); } to { transform: translateY(0); } }
@media (min-width: 720px) {
  .fbw-sheet { left: auto; right: 14px; bottom: 70px; max-width: 420px; max-height: 70vh; border-radius: 12px; }
  .fbw-sheet.fbw-open { animation: fbw-fade-in 0.18s ease-out; }
  @keyframes fbw-fade-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
  .fbw-backdrop.fbw-open { background: rgba(15, 23, 42, 0.18); }
}

.fbw-sheet * { box-sizing: border-box; }

.fbw-header {
  padding: 14px 16px 12px;
  border-bottom: 1px solid #e5e7eb;
  display: flex; align-items: flex-start; gap: 10px;
}
.fbw-title-wrap { flex: 1; min-width: 0; }
.fbw-eyebrow {
  font-size: 11px; color: #6b7280;
  letter-spacing: 0.04em; text-transform: uppercase;
}
.fbw-title {
  font-size: 14.5px; font-weight: 500; margin-top: 2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  color: #1a1a1a;
}
.fbw-close-btn {
  background: #f3f4f6; border: 0;
  width: 30px; height: 30px; border-radius: 15px;
  font-size: 18px; line-height: 1;
  cursor: pointer; color: #6b7280;
  flex-shrink: 0;
}

.fbw-history {
  flex: 1; overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 12px 14px;
  background: #f7f8fa;
}
.fbw-empty {
  text-align: center; color: #6b7280;
  font-size: 13px; padding: 28px 16px; line-height: 1.55;
}
.fbw-empty .fbw-empty-emoji { font-size: 24px; margin-bottom: 8px; }
.fbw-empty-other {
  margin-top: 14px; padding-top: 14px;
  border-top: 1px solid #e5e7eb;
  font-size: 12px; color: #9ca3af;
}

.fbw-msg-row {
  display: flex; flex-direction: column;
  margin-bottom: 8px; align-items: flex-end;
}
.fbw-msg {
  background: var(--fbw-primary, #1f3a5f);
  color: white;
  padding: 8px 12px;
  border-radius: 14px 14px 4px 14px;
  font-size: 13.5px; line-height: 1.4;
  max-width: 85%;
  white-space: pre-wrap; word-wrap: break-word;
}
.fbw-msg-meta {
  font-size: 10.5px; color: #9ca3af;
  margin-top: 2px;
}

.fbw-input-area {
  border-top: 1px solid #e5e7eb;
  background: white;
  padding: 10px 12px 12px;
}
.fbw-name {
  width: 100%;
  padding: 8px 10px;
  margin-bottom: 8px;
  border: 1px solid #e5e7eb; border-radius: 8px;
  font: inherit;
  font-size: 13.5px;
}
.fbw-name:focus { outline: none; border-color: var(--fbw-primary, #1f3a5f); }

.fbw-input-row { display: flex; gap: 8px; align-items: flex-end; }
.fbw-input-row textarea {
  flex: 1;
  padding: 9px 12px;
  border: 1px solid #e5e7eb; border-radius: 16px;
  font: inherit; font-size: 14px;
  resize: none;
  min-height: 38px; max-height: 120px;
  line-height: 1.4;
}
.fbw-input-row textarea:focus { outline: none; border-color: var(--fbw-primary, #1f3a5f); }
.fbw-send {
  background: var(--fbw-primary, #1f3a5f);
  color: white;
  border: 0; padding: 0;
  width: 38px; height: 38px; border-radius: 19px;
  font-size: 16px; line-height: 1;
  cursor: pointer;
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.fbw-send:disabled { background: #e5e7eb; color: #9ca3af; cursor: not-allowed; }
.fbw-status {
  font-size: 11px; color: #9ca3af;
  margin-top: 6px; text-align: right; min-height: 14px;
}
.fbw-status.fbw-ok { color: #047857; }
.fbw-status.fbw-error { color: #b91c1c; }

/* ---- v1.1: tag chips ---- */
.fbw-tags {
  padding: 10px 12px 0;
  background: white;
  border-top: 1px solid #f3f4f6;
}
.fbw-tag-eyebrow {
  font-size: 10.5px; color: #9ca3af;
  letter-spacing: 0.04em; text-transform: uppercase;
  margin: 0 2px 4px;
}
.fbw-chip-row {
  display: flex; flex-wrap: wrap; gap: 5px;
  margin-bottom: 6px;
}
.fbw-chip {
  background: white; color: #4b5563;
  border: 1px solid #e5e7eb;
  padding: 3px 9px; border-radius: 13px;
  font: inherit; font-size: 12px; line-height: 1.4;
  cursor: pointer;
  transition: background 80ms, border-color 80ms, color 80ms;
  user-select: none;
  white-space: nowrap;
}
.fbw-chip:hover { background: #f9fafb; }
.fbw-chip.fbw-on {
  background: var(--fbw-primary, #1f3a5f);
  color: white;
  border-color: var(--fbw-primary, #1f3a5f);
}

/* ---- v1.1: picker button + picked chip ---- */
.fbw-pick-btn {
  background: white; color: #4b5563;
  border: 1px solid #e5e7eb;
  padding: 0; width: 38px; height: 38px;
  border-radius: 19px;
  font: inherit; font-size: 16px; line-height: 1;
  cursor: pointer;
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.fbw-pick-btn:hover { background: #f9fafb; }
.fbw-pick-btn.fbw-on {
  background: #fef3c7; border-color: #fbbf24; color: #92400e;
}
.fbw-picked {
  display: flex; align-items: center; gap: 6px;
  background: #fef3c7;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 5px 8px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #78350f;
  overflow: hidden;
}
.fbw-picked-sel {
  flex: 1; min-width: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11.5px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  color: #78350f;
}
.fbw-picked-clear {
  background: transparent; border: 0; cursor: pointer;
  width: 20px; height: 20px; border-radius: 10px;
  font-size: 14px; line-height: 1;
  color: #92400e;
  flex-shrink: 0;
}
.fbw-picked-clear:hover { background: #fde68a; }

/* ---- v1.1: pointer-mode overlay ---- */
.fbw-picker-banner {
  position: fixed; top: 12px; left: 50%;
  transform: translateX(-50%);
  background: #1f2937; color: white;
  padding: 8px 14px; border-radius: 18px;
  font: 13px -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", "Roboto", sans-serif;
  box-shadow: 0 6px 20px rgba(0,0,0,0.25);
  z-index: 2147483645;
  pointer-events: none;
}
.fbw-picker-highlight {
  position: fixed;
  border: 2px solid #f59e0b;
  background: rgba(251, 191, 36, 0.12);
  border-radius: 3px;
  pointer-events: none;
  z-index: 2147483644;
  transition: all 60ms linear;
}
body.fbw-picking, body.fbw-picking * { cursor: crosshair !important; }

/* ---- v1.2: mobile-first touch ergonomics ---- */
/* iOS Safari auto-zooms inputs whose font-size <16px on focus. Bump to 16px
   on mobile-width viewports so the whole page doesn't jump-scale when the
   user taps the textarea or submitter name field. */
@media (max-width: 720px) {
  .fbw-input-row textarea, .fbw-name { font-size: 16px; }
}

/* iOS home indicator + notch — pad the sheet bottom so the input area
   is not occluded by the indicator strip. dvh on max-height (already set)
   handles the keyboard-pop case. */
.fbw-sheet { padding-bottom: env(safe-area-inset-bottom, 0); }

/* Touch devices need 44×44 minimum touch targets per Apple HIG and ~48dp
   per Material guidelines. Bump all interactive controls — except chips
   and inline icons — when the primary pointer is coarse (finger). */
@media (pointer: coarse) {
  .fbw-fab           { width: 56px; height: 56px; border-radius: 28px; font-size: 26px; }
  .fbw-pick-btn,
  .fbw-send          { width: 44px; height: 44px; border-radius: 22px; font-size: 18px; }
  .fbw-close-btn     { width: 36px; height: 36px; border-radius: 18px; font-size: 22px; }
  .fbw-picked-clear  { width: 28px; height: 28px; border-radius: 14px; font-size: 18px; }
  .fbw-chip          { padding: 6px 12px; font-size: 13px; }
  /* Picker highlight is thicker on touch so it's visible past the user's
     finger. Use a contrasting outer glow as well. */
  .fbw-picker-highlight {
    border-width: 3px;
    box-shadow: 0 0 0 1px rgba(0,0,0,0.4), 0 0 12px rgba(245,158,11,0.55);
  }
  .fbw-picker-banner { font-size: 14px; padding: 10px 16px; max-width: 90vw; }
}
`;

  // ---------- Helpers ----------
  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'
    }[c]));
  }
  // cssEscape polyfill — esbuild bundles can shadow the global CSS object,
  // and older WebKit doesn't ship it. Fall back to the spec's escape rules.
  function cssEscape(s) {
    s = String(s == null ? '' : s);
    if (typeof globalThis.CSS !== 'undefined' && typeof globalThis.cssEscape === 'function') {
      try { return globalThis.cssEscape(s); } catch (_e) { /* fallthrough */ }
    }
    // Minimal escape: backslash anything outside [a-zA-Z0-9_-]
    return s.replace(/[^a-zA-Z0-9_-]/g, ch => '\\' + ch);
  }
  function fmtTime(iso) {
    try { return new Date(iso).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }); }
    catch { return ''; }
  }
  function injectCSSOnce() {
    if (document.getElementById('fbw-style')) return;
    const s = document.createElement('style');
    s.id = 'fbw-style';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  // ---------- Widget class ----------
  class FeedbackWidget {
    constructor(cfg) {
      this.cfg = Object.assign({}, DEFAULTS, cfg || {});
      this.copy = COPY[this.cfg.language] || COPY.en;
      this.tagGroups = TAG_GROUPS[this.cfg.language] || TAG_GROUPS.en;
      this.storageKey = `fbw-${this.cfg.project}`;
      this.open = false;
      this.currentScreen = this._detectScreen();
      this.els = {};
      // v1.1 — selected chips (persists across comments in audit walks)
      this.tags = this._loadTags();
      // v1.1 — picked element (cleared after each send)
      this.pickedElement = null;
      // v1.1 — ring buffers for context bundle (initialised on mount)
      this._recentActions = [];
      this._consoleErrors = [];
      this._pickerActive = false;
      this._pickerCleanup = null;
    }

    _loadTags() {
      try {
        const d = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
        return d.lastTags && typeof d.lastTags === 'object' ? d.lastTags : {};
      } catch { return {}; }
    }
    _persistTags() {
      const d = this._load();
      d.lastTags = this.tags;
      this._save(d);
    }

    // ---------- Screen detection ----------
    _detectScreen() {
      const cfg = this.cfg;
      // Priority: callback → body data attr → hash → pathname
      let id = '';
      let name = '';
      if (typeof cfg.getScreenId === 'function') {
        try { id = cfg.getScreenId() || ''; } catch (e) {}
      }
      if (!id) {
        const body = document.body;
        id = body && body.dataset.fbwScreenId || '';
      }
      if (!id && location.hash && location.hash.length > 1) id = location.hash.slice(1);
      if (!id) id = location.pathname || '/';

      if (typeof cfg.getScreenName === 'function') {
        try { name = cfg.getScreenName() || ''; } catch (e) {}
      }
      if (!name) {
        const body = document.body;
        name = body && body.dataset.fbwScreenName || '';
      }
      if (!name) name = document.title || id;

      return { id: String(id), name: String(name) };
    }

    refreshScreen() {
      this.currentScreen = this._detectScreen();
      if (this.open) this._renderHistory();
    }

    // ---------- Storage ----------
    _load() {
      try { return JSON.parse(localStorage.getItem(this.storageKey) || '{}'); }
      catch { return {}; }
    }
    _save(data) {
      try { localStorage.setItem(this.storageKey, JSON.stringify(data)); } catch (e) {}
    }
    _hasAnyMsgs() {
      const d = this._load();
      return Array.isArray(d.messages) && d.messages.length > 0;
    }

    // ---------- DOM mount ----------
    mount() {
      injectCSSOnce();
      this._mountFab();
      this._mountSheet();
      this._wireEvents();
      this._updateFab();
      if (this.cfg.enableContext) this._initContextCapture();
      // Try to flush pending offline messages on mount
      setTimeout(() => this._resendPending(), 1500);
    }

    _mountFab() {
      const fab = document.createElement('button');
      fab.className = 'fbw-fab';
      fab.id = 'fbw-fab';
      fab.dataset.pos = this.cfg.position;
      fab.title = this.copy.fab_title;
      fab.style.background = this.cfg.fabColor;
      fab.innerHTML = `${this.cfg.fabIcon}<span class="fbw-dot"></span>`;
      fab.addEventListener('click', () => this.toggle());
      document.body.appendChild(fab);
      this.els.fab = fab;
    }

    _mountSheet() {
      const backdrop = document.createElement('div');
      backdrop.className = 'fbw-backdrop';
      backdrop.id = 'fbw-backdrop';
      backdrop.addEventListener('click', () => this.toggle());
      document.body.appendChild(backdrop);
      this.els.backdrop = backdrop;

      const sheet = document.createElement('div');
      sheet.className = 'fbw-sheet';
      sheet.id = 'fbw-sheet';
      sheet.style.setProperty('--fbw-primary', this.cfg.primaryColor);
      const tagsHtml = this.cfg.enableTags ? `
        <div class="fbw-tags" id="fbw-tags">
          <div class="fbw-tag-eyebrow">${escapeHtml(this.copy.tag_type_eyebrow)}</div>
          <div class="fbw-chip-row" data-group="type">
            ${this.tagGroups.type.map(t => `<button class="fbw-chip" type="button" data-group="type" data-value="${escapeHtml(t.v)}">${escapeHtml(t.l)}</button>`).join('')}
          </div>
          <div class="fbw-tag-eyebrow">${escapeHtml(this.copy.tag_sev_eyebrow)}</div>
          <div class="fbw-chip-row" data-group="severity">
            ${this.tagGroups.severity.map(t => `<button class="fbw-chip" type="button" data-group="severity" data-value="${escapeHtml(t.v)}">${escapeHtml(t.l)}</button>`).join('')}
          </div>
        </div>` : '';

      const pickerBtn = this.cfg.enablePointer
        ? `<button class="fbw-pick-btn" type="button" id="fbw-pick" aria-label="${escapeHtml(this.copy.pick_btn)}" title="${escapeHtml(this.copy.pick_btn)}">${escapeHtml(this.copy.pick_btn_short)}</button>`
        : '';

      sheet.innerHTML = `
        <div class="fbw-header">
          <div class="fbw-title-wrap">
            <div class="fbw-eyebrow">${escapeHtml(this.copy.sheet_eyebrow)}</div>
            <div class="fbw-title" id="fbw-screen-name">—</div>
          </div>
          <button class="fbw-close-btn" id="fbw-close" aria-label="${escapeHtml(this.copy.sheet_close)}">×</button>
        </div>
        <div class="fbw-history" id="fbw-history"></div>
        ${tagsHtml}
        <div class="fbw-input-area">
          <input type="text" class="fbw-name" id="fbw-name" placeholder="${escapeHtml(this.copy.name_placeholder)}">
          <div class="fbw-picked" id="fbw-picked" style="display:none">
            <span class="fbw-picked-icon">📍</span>
            <code class="fbw-picked-sel" id="fbw-picked-sel"></code>
            <button class="fbw-picked-clear" id="fbw-picked-clear" type="button" aria-label="${escapeHtml(this.copy.pick_clear_aria)}">×</button>
          </div>
          <div class="fbw-input-row">
            ${pickerBtn}
            <textarea id="fbw-msg" rows="1" placeholder="${escapeHtml(this.copy.msg_placeholder)}"></textarea>
            <button class="fbw-send" id="fbw-send" disabled aria-label="${escapeHtml(this.copy.send_aria)}">➤</button>
          </div>
          <div class="fbw-status" id="fbw-status"></div>
        </div>
      `;
      document.body.appendChild(sheet);
      this.els.sheet = sheet;
      this.els.history = sheet.querySelector('#fbw-history');
      this.els.screenName = sheet.querySelector('#fbw-screen-name');
      this.els.name = sheet.querySelector('#fbw-name');
      this.els.msg = sheet.querySelector('#fbw-msg');
      this.els.send = sheet.querySelector('#fbw-send');
      this.els.status = sheet.querySelector('#fbw-status');
      this.els.close = sheet.querySelector('#fbw-close');
      this.els.tags = sheet.querySelector('#fbw-tags');
      this.els.pick = sheet.querySelector('#fbw-pick');
      this.els.picked = sheet.querySelector('#fbw-picked');
      this.els.pickedSel = sheet.querySelector('#fbw-picked-sel');
      this.els.pickedClear = sheet.querySelector('#fbw-picked-clear');
    }

    _wireEvents() {
      this.els.close.addEventListener('click', () => this.toggle());

      // textarea auto-grow + send-button enable
      this.els.msg.addEventListener('input', () => {
        const ta = this.els.msg;
        ta.style.height = 'auto';
        ta.style.height = Math.min(120, ta.scrollHeight) + 'px';
        this.els.send.disabled = !ta.value.trim();
      });

      // submitter name persistence
      this.els.name.addEventListener('input', e => {
        const v = e.target.value.trim();
        const d = this._load();
        if (v) d.submitter = v; else delete d.submitter;
        this._save(d);
      });

      // send
      this.els.send.addEventListener('click', () => this.send());

      // Enter to send (Shift+Enter for newline)
      this.els.msg.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey) {
          e.preventDefault();
          if (!this.els.send.disabled) this.send();
        }
      });

      // v1.1 — chip toggle (single-select per group)
      if (this.els.tags) {
        this.els.tags.addEventListener('click', e => {
          const btn = e.target.closest('.fbw-chip');
          if (!btn) return;
          const group = btn.dataset.group;
          const value = btn.dataset.value;
          if (this.tags[group] === value) {
            delete this.tags[group];   // re-click clears
          } else {
            this.tags[group] = value;
          }
          this._persistTags();
          this._renderChips();
        });
      }

      // v1.1 — element picker
      if (this.els.pick) {
        this.els.pick.addEventListener('click', () => this._startPointerMode());
      }
      if (this.els.pickedClear) {
        this.els.pickedClear.addEventListener('click', () => {
          this.pickedElement = null;
          this._renderPicked();
        });
      }
    }

    // ---------- Public API ----------
    toggle(forceState) {
      this.open = (forceState === undefined) ? !this.open : !!forceState;
      this.els.sheet.classList.toggle('fbw-open', this.open);
      this.els.backdrop.classList.toggle('fbw-open', this.open);
      if (this.open) {
        this.refreshScreen();
        this._renderChips();
        this._renderPicked();
        setTimeout(() => this.els.msg.focus(), 100);
      }
    }

    _renderHistory() {
      const data = this._load();
      const { id, name } = this.currentScreen;
      this.els.screenName.textContent = name;

      const all = data.messages || [];
      const here = all.filter(m => m.screen_id === id);

      if (here.length === 0) {
        let other = '';
        if (all.length > 0) {
          const n = new Set(all.map(m => m.screen_id)).size;
          other = `<div class="fbw-empty-other">${this.copy.empty_other_screens.replace('{n}', n)}</div>`;
        }
        this.els.history.innerHTML = `
          <div class="fbw-empty">
            <div class="fbw-empty-emoji">${this.copy.empty_emoji}</div>
            ${this.copy.empty_text}
            ${other}
          </div>`;
      } else {
        this.els.history.innerHTML = here.map(m => `
          <div class="fbw-msg-row">
            <div class="fbw-msg">${escapeHtml(m.message)}</div>
            <div class="fbw-msg-meta">${escapeHtml(m.submitter || this.copy.anon)} · ${escapeHtml(fmtTime(m.ts))}${m.sent === false ? ' · ⏳ ' + escapeHtml(this.copy.not_sent) : ''}</div>
          </div>`).join('');
      }

      // submitter input visibility
      if (data.submitter) {
        this.els.name.style.display = 'none';
        this.els.name.value = data.submitter;
      } else {
        this.els.name.style.display = 'block';
        this.els.name.value = '';
      }

      // scroll bottom + clear status
      setTimeout(() => { this.els.history.scrollTop = this.els.history.scrollHeight; }, 30);
      this.els.status.textContent = '';
      this.els.status.className = 'fbw-status';
    }

    async send() {
      const msg = this.els.msg.value.trim();
      if (!msg) return;
      const { id, name } = this.currentScreen;
      const data = this._load();
      const submitter = (data.submitter || this.els.name.value || '').trim() || `(${this.copy.anon})`;
      const entry = {
        project: this.cfg.project,
        screen_id: id,
        screen_name: name,
        message: msg,
        submitter,
        ts: new Date().toISOString(),
        user_agent: (navigator.userAgent || '').slice(0, 160),
        sent: false,
      };
      // v1.1 — attach optional fields if present
      if (Object.keys(this.tags).length) entry.tags = Object.assign({}, this.tags);
      if (this.pickedElement) entry.pointed_element = this.pickedElement;
      if (this.cfg.enableContext) entry.context = this._buildContextBundle();

      // Optimistic local persist BEFORE network
      data.submitter = submitter;
      data.messages = data.messages || [];
      data.messages.push(entry);
      this._save(data);

      // Clear input + picked element (tags stay sticky for audit walks)
      this.els.msg.value = '';
      this.els.msg.style.height = 'auto';
      this.els.send.disabled = true;
      this.pickedElement = null;
      this._renderPicked();
      this._renderHistory();
      this._updateFab();

      // status
      const st = this.els.status;
      st.className = 'fbw-status';
      st.textContent = this.copy.sending;

      try {
        const { sent: _omit, ...payload } = entry;
        const res = await this._post(payload);
        if (!res.ok) throw new Error('http ' + res.status);
        entry.sent = true;
        this._save(data);
        st.className = 'fbw-status fbw-ok';
        st.textContent = this.copy.sent_ok;
        setTimeout(() => { if (st.textContent.startsWith('✓')) st.textContent = ''; }, 2500);
        this._renderHistory();
      } catch (e) {
        st.className = 'fbw-status fbw-error';
        st.textContent = this.copy.net_error;
        setTimeout(() => this._resendPending(), 30000);
      }
    }

    async _post(payload) {
      const headers = { 'Content-Type': 'application/json' };
      if (typeof this.cfg.fetchHeaders === 'function') {
        try {
          const extra = this.cfg.fetchHeaders() || {};
          for (const k in extra) if (extra[k] != null) headers[k] = String(extra[k]);
        } catch (_e) {}
      }
      return fetch(this.cfg.endpoint, {
        method: 'POST',
        headers,
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });
    }

    async _resendPending() {
      const data = this._load();
      const pending = (data.messages || []).filter(m => m.sent === false);
      if (pending.length === 0) return;
      for (const e of pending) {
        try {
          const { sent: _omit, ...payload } = e;
          const res = await this._post(payload);
          if (res.ok) e.sent = true;
        } catch (_e) { /* keep pending */ }
      }
      this._save(data);
      if (this.open) this._renderHistory();
    }

    _updateFab() {
      this.els.fab.classList.toggle('fbw-has-msgs', this._hasAnyMsgs());
    }

    // ---------- v1.1: tag chips ----------
    _renderChips() {
      if (!this.els.tags) return;
      this.els.tags.querySelectorAll('.fbw-chip').forEach(btn => {
        const on = this.tags[btn.dataset.group] === btn.dataset.value;
        btn.classList.toggle('fbw-on', on);
      });
    }

    // ---------- v1.1: picked element ----------
    _renderPicked() {
      if (!this.els.picked) return;
      if (this.pickedElement && this.pickedElement.selector) {
        const sel = this.pickedElement.selector;
        const txt = (this.pickedElement.text || '').trim();
        this.els.pickedSel.textContent = txt ? `${sel} · "${txt.slice(0, 40)}${txt.length > 40 ? '…' : ''}"` : sel;
        this.els.picked.style.display = 'flex';
      } else {
        this.els.picked.style.display = 'none';
      }
    }

    // ---------- v1.1: pointer mode (with v1.2 touch support) ----------
    _startPointerMode() {
      if (this._pickerActive) return;
      this._pickerActive = true;
      // Hide sheet so user can see the page; keep widget instance + state
      this.toggle(false);
      document.body.classList.add('fbw-picking');

      // v1.2 — pick mobile-friendly banner copy when primary pointer is coarse
      const isTouch = (typeof matchMedia === 'function')
        && matchMedia('(pointer: coarse)').matches;
      const banner = document.createElement('div');
      banner.className = 'fbw-picker-banner';
      banner.textContent = isTouch ? this.copy.pick_active_touch : this.copy.pick_active;
      document.body.appendChild(banner);

      const highlight = document.createElement('div');
      highlight.className = 'fbw-picker-highlight';
      document.body.appendChild(highlight);

      const isOurs = (el) => {
        if (!el || !el.closest) return false;
        return !!el.closest('.fbw-fab, .fbw-sheet, .fbw-backdrop, .fbw-picker-banner, .fbw-picker-highlight');
      };
      const elFromPoint = (x, y) => {
        const el = document.elementFromPoint(x, y);
        return el && !isOurs(el) ? el : null;
      };
      const showHighlight = (el) => {
        if (!el) { highlight.style.display = 'none'; return; }
        const r = el.getBoundingClientRect();
        highlight.style.display = 'block';
        highlight.style.left = r.left + 'px';
        highlight.style.top = r.top + 'px';
        highlight.style.width = r.width + 'px';
        highlight.style.height = r.height + 'px';
      };

      // ----- mouse path (desktop) -----
      const onMove = (e) => showHighlight(elFromPoint(e.clientX, e.clientY));
      const onClick = (e) => {
        const t = elFromPoint(e.clientX, e.clientY);
        if (!t) return;
        e.preventDefault(); e.stopPropagation();
        this.pickedElement = this._captureElement(t);
        cleanup(true);
      };
      const onKey = (e) => { if (e.key === 'Escape') cleanup(false); };

      // ----- v1.2 touch path (mobile) -----
      // Single-finger: drag = scroll page + highlight follows finger; lift
      //   without significant movement = pick element under last touch.
      // Two-finger tap: cancel picker mode.
      let touchStartX = 0, touchStartY = 0, touchMoved = false;
      const TOUCH_TAP_THRESHOLD = 10; // px — above this counts as a scroll, not a tap
      const onTouchStart = (e) => {
        if (e.touches.length >= 2) {           // 2-finger tap → cancel
          cleanup(false);
          return;
        }
        const t = e.touches[0];
        touchStartX = t.clientX; touchStartY = t.clientY;
        touchMoved = false;
        showHighlight(elFromPoint(t.clientX, t.clientY));
      };
      const onTouchMove = (e) => {
        if (e.touches.length !== 1) return;
        const t = e.touches[0];
        if (Math.abs(t.clientX - touchStartX) > TOUCH_TAP_THRESHOLD
            || Math.abs(t.clientY - touchStartY) > TOUCH_TAP_THRESHOLD) {
          touchMoved = true;
        }
        showHighlight(elFromPoint(t.clientX, t.clientY));
        // Do NOT preventDefault — we want the page to scroll naturally
      };
      const onTouchEnd = (e) => {
        if (e.changedTouches.length !== 1) return;
        const t = e.changedTouches[0];
        if (touchMoved) {
          // Was a scroll, not a tap — leave highlight where finger lifted
          // so the user sees what's now under it but don't capture
          showHighlight(elFromPoint(t.clientX, t.clientY));
          return;
        }
        const target = elFromPoint(t.clientX, t.clientY);
        if (!target) return;
        e.preventDefault();
        // Block the synthesised click that follows a tap (would re-trigger onClick)
        const blockClick = (ev) => { ev.preventDefault(); ev.stopPropagation(); };
        document.addEventListener('click', blockClick, { capture: true, once: true });
        this.pickedElement = this._captureElement(target);
        cleanup(true);
      };

      const cleanup = (success) => {
        if (!this._pickerActive) return;
        this._pickerActive = false;
        document.body.classList.remove('fbw-picking');
        document.removeEventListener('mousemove', onMove, true);
        document.removeEventListener('click', onClick, true);
        document.removeEventListener('keydown', onKey, true);
        document.removeEventListener('touchstart', onTouchStart, true);
        document.removeEventListener('touchmove', onTouchMove, true);
        document.removeEventListener('touchend', onTouchEnd, true);
        try { highlight.remove(); } catch(_e) {}
        try { banner.remove(); } catch(_e) {}
        this.toggle(true);
        if (success) this._renderPicked();
      };
      this._pickerCleanup = cleanup;

      document.addEventListener('mousemove', onMove, true);
      document.addEventListener('click', onClick, true);
      document.addEventListener('keydown', onKey, true);
      // Touch listeners. touchmove must NOT be passive if we ever want to
      // preventDefault; we don't here, so passive is fine and keeps scroll
      // smoothness on iOS.
      document.addEventListener('touchstart', onTouchStart, { capture: true, passive: true });
      document.addEventListener('touchmove',  onTouchMove,  { capture: true, passive: true });
      document.addEventListener('touchend',   onTouchEnd,   { capture: true, passive: false });
    }

    _captureElement(el) {
      const r = el.getBoundingClientRect();
      return {
        selector: this._buildSelector(el),
        tag: (el.tagName || '').toLowerCase(),
        text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 200),
        html: (el.outerHTML || '').slice(0, 600),
        bbox: { x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) },
        viewport: { w: window.innerWidth, h: window.innerHeight },
        scroll: { x: window.scrollX || 0, y: window.scrollY || 0 },
      };
    }

    _buildSelector(el) {
      // Walk up max 6 levels, prefer id, then data-fieldname/data-doctype, then tag.class
      if (el.id) return '#' + cssEscape(el.id);
      const parts = [];
      let n = el;
      let depth = 0;
      while (n && n.nodeType === 1 && depth < 6) {
        let p = (n.tagName || 'div').toLowerCase();
        if (n.id) { parts.unshift('#' + cssEscape(n.id)); break; }
        if (n.classList && n.classList.length) {
          const cls = [...n.classList].filter(c => c && !c.startsWith('fbw-')).slice(0, 2);
          if (cls.length) p += '.' + cls.map(c => cssEscape(c)).join('.');
        }
        if (n.dataset) {
          if (n.dataset.fieldname) p += `[data-fieldname="${n.dataset.fieldname}"]`;
          else if (n.dataset.doctype) p += `[data-doctype="${n.dataset.doctype}"]`;
          else if (n.dataset.fbwScreenId) p += `[data-fbw-screen-id="${n.dataset.fbwScreenId}"]`;
        }
        parts.unshift(p);
        n = n.parentElement;
        depth++;
      }
      return parts.join(' > ');
    }

    // ---------- v1.1: context capture ----------
    _initContextCapture() {
      const max = Math.max(5, this.cfg.contextHistorySize | 0 || 20);
      // Click trail (passive, capture phase, ignores widget's own elements)
      document.addEventListener('click', (e) => {
        const t = e.target;
        if (!t || !t.closest) return;
        if (t.closest('.fbw-fab, .fbw-sheet, .fbw-backdrop, .fbw-picker-banner, .fbw-picker-highlight')) return;
        this._pushAction({ type: 'click', target: this._terseSelector(t), ts: Date.now() }, max);
      }, true);
      // Console errors (passive)
      window.addEventListener('error', (e) => {
        this._consoleErrors.push({
          type: 'error',
          message: String(e && e.message || '').slice(0, 300),
          source: String(e && e.filename || '').slice(0, 200),
          line: (e && e.lineno) | 0,
          col: (e && e.colno) | 0,
          ts: Date.now(),
        });
        if (this._consoleErrors.length > max) this._consoleErrors.shift();
      });
      window.addEventListener('unhandledrejection', (e) => {
        const reason = e && e.reason;
        const msg = (reason && (reason.message || reason.toString())) || '';
        this._consoleErrors.push({
          type: 'rejection',
          message: String(msg).slice(0, 300),
          ts: Date.now(),
        });
        if (this._consoleErrors.length > max) this._consoleErrors.shift();
      });
      // Frappe route change (only when frappe is present)
      try {
        if (typeof window.frappe !== 'undefined' && window.frappe.router && typeof window.frappe.router.on === 'function') {
          window.frappe.router.on('change', () => {
            const route = (window.frappe.get_route && window.frappe.get_route().join('/')) || location.pathname;
            this._pushAction({ type: 'route', target: route, ts: Date.now() }, max);
          });
        }
      } catch (_e) {}
      // popstate fallback for non-Frappe SPAs
      window.addEventListener('popstate', () => {
        this._pushAction({ type: 'route', target: location.pathname + location.hash, ts: Date.now() }, max);
      });
    }

    _pushAction(a, max) {
      this._recentActions.push(a);
      if (this._recentActions.length > (max || 20)) this._recentActions.shift();
    }

    _terseSelector(el) {
      if (!el) return '?';
      if (el.id) return '#' + el.id;
      const tag = el.tagName ? el.tagName.toLowerCase() : '?';
      let cls = '';
      if (el.classList && el.classList.length) {
        const c = [...el.classList].filter(x => x && !x.startsWith('fbw-')).slice(0, 1);
        if (c.length) cls = '.' + c[0];
      }
      const txt = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 30);
      return tag + cls + (txt ? ` "${txt}${(el.textContent || '').trim().length > 30 ? '…' : ''}"` : '');
    }

    _buildContextBundle() {
      const ctx = {
        url: location.href,
        pathname: location.pathname,
        hash: location.hash,
        viewport: {
          w: window.innerWidth, h: window.innerHeight,
          dpr: window.devicePixelRatio || 1,
        },
        language: navigator.language || '',
        recent_actions: this._recentActions.slice(),
        console_errors: this._consoleErrors.slice(),
      };
      if (typeof this.cfg.getContext === 'function') {
        try {
          const app = this.cfg.getContext();
          if (app && typeof app === 'object') ctx.app = app;
        } catch (_e) {}
      }
      return ctx;
    }
  }

  // ---------- Public API ----------
  global.FeedbackWidget = {
    mount(cfg) {
      const w = new FeedbackWidget(cfg || global.feedbackWidget);
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => w.mount());
      } else {
        w.mount();
      }
      global.__fbw_instance__ = w;
      return w;
    },
    refreshScreen() {
      if (global.__fbw_instance__) global.__fbw_instance__.refreshScreen();
    },
  };

  // ---------- Auto-mount ----------
  if (DEFAULTS.autoMount && global.feedbackWidget) {
    global.FeedbackWidget.mount();
  }
})(typeof window !== 'undefined' ? window : globalThis);
