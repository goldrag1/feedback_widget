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
    enableAttach: true,             // 📎 image attachment (file picker + paste)
    contextHistorySize: 20,         // ring-buffer length for actions + errors
    uploadEndpoint: '/api/method/upload_file',  // Frappe-shaped; override for non-Frappe hosts
    uploadFieldName: 'file',        // multipart field name expected by uploadEndpoint
    uploadExtraFields: { is_private: '1', folder: 'Home/Feedback' },  // extra form fields
    uploadIsPrivate: true,          // hint to host (also tells display to use private url)
    maxAttachments: 10,             // Telegram media-group max
    maxAttachmentBytes: 8 * 1024 * 1024,  // 8MB per file (Telegram bot limit is 10MB)
    // v1.1 — host integration callbacks (all optional)
    getScreenId: null,              // () => string  (already in v1.0)
    getScreenName: null,            // () => string  (already in v1.0)
    getContext: null,               // () => object  — merged into ctx.app
    fetchHeaders: null,             // () => object  — extra headers per POST (e.g. CSRF)
    userId: '',                     // host-supplied identifier — scopes FAB position per user
    maxPickedElements: 5,           // v1.4 — cap how many element pins per comment
    statusEndpoint: '',             // v1.4 — GET/POST endpoint for status_for_names; '' = disabled
    statusPollMs: 60000,            // v1.4 — poll cadence while sheet is open
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
      attach_btn: '📎 Đính ảnh',
      attach_btn_short: '📎',
      attach_clear_aria: 'Bỏ ảnh này',
      attach_too_big: 'Ảnh quá lớn (tối đa 8MB) — bỏ qua',
      attach_too_many: 'Đã tới giới hạn 10 ảnh',
      attach_uploading: 'Đang tải ảnh lên...',
      attach_upload_failed: 'Tải ảnh lên thất bại',
      pick_more: 'Chỉ thêm chỗ',
      pick_count_one: 'đã chọn 1 chỗ',
      pick_count_many: 'đã chọn {n} chỗ',
      pick_max_reached: 'Đã đạt giới hạn {n} chỗ',
      status_new: 'Mới gửi',
      status_triaged: '👀 Đã xem',
      status_in_progress: '🔧 Đang xử lý',
      status_resolved: '✅ Đã xử lý',
      status_wontfix: '🚫 Không xử lý',
      status_note_label: 'Lời nhắn',
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
      attach_btn: '📎 Attach image',
      attach_btn_short: '📎',
      attach_clear_aria: 'Remove this image',
      attach_too_big: 'Image too large (max 8MB) — skipped',
      attach_too_many: 'Hit 10-image limit',
      attach_uploading: 'Uploading images...',
      attach_upload_failed: 'Upload failed',
      pick_more: 'Pin another',
      pick_count_one: '1 pinned',
      pick_count_many: '{n} pinned',
      pick_max_reached: 'Max {n} pins reached',
      status_new: 'Submitted',
      status_triaged: '👀 Triaged',
      status_in_progress: '🔧 In progress',
      status_resolved: '✅ Resolved',
      status_wontfix: '🚫 Won\'t fix',
      status_note_label: 'Reply',
    },
  };

  // ---------- CSS (injected once) ----------
  const CSS = `
.fbw-fab {
  position: fixed;
  width: 48px; height: 48px; border-radius: 24px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  cursor: grab;
  font-size: 22px; line-height: 1;
  color: white;
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.08);
  display: flex; align-items: center; justify-content: center;
  z-index: 2147483600;
  transition: transform 0.12s ease;
  touch-action: none;
  user-select: none;
  -webkit-user-select: none;
}
.fbw-fab:active { transform: scale(0.94); }
.fbw-fab.fbw-dragging { cursor: grabbing; transition: none; box-shadow: 0 8px 18px rgba(15, 23, 42, 0.18); }
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
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 18px 18px 0 0;
  max-height: 75vh; max-height: 75dvh;
  display: none;
  flex-direction: column;
  z-index: 2147483602;
  box-shadow: 0 -6px 18px rgba(15, 23, 42, 0.06);
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
  .fbw-attach-btn,
  .fbw-send          { width: 44px; height: 44px; border-radius: 22px; font-size: 18px; }
  .fbw-close-btn     { width: 36px; height: 36px; border-radius: 18px; font-size: 22px; }
  .fbw-picked-clear  { width: 28px; height: 28px; border-radius: 14px; font-size: 18px; }
  .fbw-chip          { padding: 6px 12px; font-size: 13px; }
  .fbw-thumb         { width: 64px; height: 64px; }
  /* Picker highlight is thicker on touch so it's visible past the user's
     finger. Use a contrasting outer glow as well. */
  .fbw-picker-highlight {
    border-width: 3px;
    box-shadow: 0 0 0 1px rgba(0,0,0,0.4), 0 0 12px rgba(245,158,11,0.55);
  }
  .fbw-picker-banner { font-size: 14px; padding: 10px 16px; max-width: 90vw; }
}

/* ---- v1.3: image attachments ---- */
.fbw-attach-btn {
  background: white; color: #4b5563;
  border: 1px solid #e5e7eb;
  padding: 0; width: 38px; height: 38px;
  border-radius: 19px;
  font: inherit; font-size: 16px; line-height: 1;
  cursor: pointer;
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.fbw-attach-btn:hover { background: #f9fafb; }
.fbw-attach-btn[disabled] { opacity: 0.5; cursor: not-allowed; }

.fbw-attached {
  display: flex; flex-wrap: wrap; gap: 6px;
  margin-bottom: 6px;
}
.fbw-thumb {
  position: relative;
  width: 56px; height: 56px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  overflow: visible;
  background: #f3f4f6;
  flex-shrink: 0;
}
.fbw-thumb-img {
  width: 100%; height: 100%;
  border-radius: 8px;
  object-fit: cover;
  display: block;
}
.fbw-thumb-clear {
  position: absolute; top: -6px; right: -6px;
  width: 20px; height: 20px; border-radius: 10px;
  background: #ef4444; color: white; border: 2px solid white;
  font-size: 11px; line-height: 1; cursor: pointer;
  padding: 0;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}
.fbw-thumb.fbw-uploading .fbw-thumb-img { opacity: 0.4; }
.fbw-thumb.fbw-uploading::after {
  content: '↑';
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  color: #1f3a5f; font-size: 18px; font-weight: 600;
  animation: fbw-pulse 1s ease-in-out infinite;
  pointer-events: none;
}
.fbw-thumb.fbw-failed { border-color: #ef4444; }
.fbw-thumb.fbw-failed::after {
  content: '✕';
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  color: #b91c1c; font-size: 16px; font-weight: 600;
  background: rgba(239, 68, 68, 0.15);
  border-radius: 8px;
  pointer-events: none;
}
@keyframes fbw-pulse { 0%, 100% { opacity: 0.6; } 50% { opacity: 1; } }

/* ---- v1.4: multi-pin chip row (above textarea) ---- */
.fbw-picked-list { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
.fbw-picked-list:empty { display: none; }

/* ---- v1.4: history bubble extras — attachments, pins, status ---- */
.fbw-msg-attached {
  display: flex; flex-wrap: wrap; gap: 4px;
  margin-top: 4px;
  max-width: 85%;
  justify-content: flex-end;
}
.fbw-msg-thumb {
  width: 44px; height: 44px; border-radius: 6px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
  background: #f3f4f6;
  cursor: pointer;
  flex-shrink: 0;
  display: block;
}
.fbw-msg-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.fbw-msg-pins {
  display: flex; flex-wrap: wrap; gap: 4px;
  margin-top: 4px;
  max-width: 85%;
  justify-content: flex-end;
}
.fbw-msg-pin {
  background: #fef3c7;
  border: 1px solid #fde68a;
  border-radius: 10px;
  padding: 1px 7px;
  font-size: 11px;
  color: #78350f;
  max-width: 100%;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.fbw-msg-status {
  align-self: flex-end;
  margin-top: 4px;
  padding: 4px 9px;
  border-radius: 12px;
  font-size: 11.5px;
  line-height: 1.35;
  max-width: 85%;
  border: 1px solid transparent;
}
.fbw-msg-status[data-status="Triaged"]     { background: #eff6ff; color: #1e3a8a; border-color: #bfdbfe; }
.fbw-msg-status[data-status="In Progress"] { background: #fff7ed; color: #9a3412; border-color: #fed7aa; }
.fbw-msg-status[data-status="Resolved"]    { background: #ecfdf5; color: #065f46; border-color: #a7f3d0; }
.fbw-msg-status[data-status="Wontfix"]     { background: #f3f4f6; color: #374151; border-color: #d1d5db; }
.fbw-msg-status-note {
  display: block;
  margin-top: 3px;
  font-size: 11px;
  color: inherit;
  opacity: 0.9;
  white-space: pre-wrap; word-wrap: break-word;
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
      // v1.4 — picked elements (array, cleared after each send)
      this.pickedElements = [];
      // v1.3 — attachments [{file, blobUrl, file_url?, file_name, file_size, mime, status}]
      // status: 'pending' | 'uploading' | 'uploaded' | 'failed'
      this.attachments = [];
      this._attachIdCounter = 0;
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
      // v1.4 — pull status updates so prior comments show their current state
      setTimeout(() => this._fetchStatuses(), 2000);
    }

    _mountFab() {
      const fab = document.createElement('button');
      fab.className = 'fbw-fab';
      fab.id = 'fbw-fab';
      fab.dataset.pos = this.cfg.position;
      fab.title = this.copy.fab_title;
      fab.style.background = this.cfg.fabColor;
      fab.innerHTML = `${this.cfg.fabIcon}<span class="fbw-dot"></span>`;
      document.body.appendChild(fab);
      this.els.fab = fab;
      this._setupFabDrag(fab);
      this._restoreFabPosition(fab);
    }

    _fabPositionKey() {
      const u = this.cfg.userId ? `:${this.cfg.userId}` : '';
      return `fbw-fab-pos:${this.cfg.project}${u}`;
    }
    _loadFabPosition() {
      try { return JSON.parse(localStorage.getItem(this._fabPositionKey()) || 'null'); }
      catch { return null; }
    }
    _saveFabPosition(x, y) {
      try { localStorage.setItem(this._fabPositionKey(), JSON.stringify({ x, y })); } catch {}
    }
    _applyFabPosition(fab, x, y) {
      const rect = fab.getBoundingClientRect();
      const w = rect.width || 48;
      const h = rect.height || 48;
      const maxX = Math.max(4, window.innerWidth - w - 4);
      const maxY = Math.max(4, window.innerHeight - h - 4);
      x = Math.max(4, Math.min(x, maxX));
      y = Math.max(4, Math.min(y, maxY));
      fab.style.left = x + 'px';
      fab.style.top = y + 'px';
      fab.style.right = 'auto';
      fab.style.bottom = 'auto';
      return { x, y };
    }
    _restoreFabPosition(fab) {
      const pos = this._loadFabPosition();
      if (pos && typeof pos.x === 'number' && typeof pos.y === 'number') {
        this._applyFabPosition(fab, pos.x, pos.y);
      }
    }
    _setupFabDrag(fab) {
      const THRESHOLD = 5;
      let dragging = false, moved = false, suppressClick = false;
      let startX = 0, startY = 0, offX = 0, offY = 0;

      const onDown = (e) => {
        if (e.button !== undefined && e.button !== 0) return;
        dragging = true; moved = false;
        const rect = fab.getBoundingClientRect();
        startX = e.clientX; startY = e.clientY;
        offX = e.clientX - rect.left; offY = e.clientY - rect.top;
        try { fab.setPointerCapture && fab.setPointerCapture(e.pointerId); } catch {}
      };
      const onMove = (e) => {
        if (!dragging) return;
        const dx = e.clientX - startX, dy = e.clientY - startY;
        if (!moved && (dx * dx + dy * dy) > THRESHOLD * THRESHOLD) {
          moved = true;
          fab.classList.add('fbw-dragging');
        }
        if (moved) this._applyFabPosition(fab, e.clientX - offX, e.clientY - offY);
      };
      const onUp = (e) => {
        if (!dragging) return;
        dragging = false;
        fab.classList.remove('fbw-dragging');
        if (moved) {
          const rect = fab.getBoundingClientRect();
          const clamped = this._applyFabPosition(fab, rect.left, rect.top);
          this._saveFabPosition(clamped.x, clamped.y);
          suppressClick = true;
          setTimeout(() => { suppressClick = false; }, 0);
        }
        try { fab.releasePointerCapture && fab.releasePointerCapture(e.pointerId); } catch {}
      };

      fab.addEventListener('pointerdown', onDown);
      fab.addEventListener('pointermove', onMove);
      fab.addEventListener('pointerup', onUp);
      fab.addEventListener('pointercancel', onUp);
      fab.addEventListener('click', (e) => {
        if (suppressClick) { e.stopPropagation(); e.preventDefault(); return; }
        this.toggle();
      });

      window.addEventListener('resize', () => {
        const pos = this._loadFabPosition();
        if (pos) this._applyFabPosition(fab, pos.x, pos.y);
      });
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
      const attachBtn = this.cfg.enableAttach
        ? `<button class="fbw-attach-btn" type="button" id="fbw-attach" aria-label="${escapeHtml(this.copy.attach_btn)}" title="${escapeHtml(this.copy.attach_btn)}">${escapeHtml(this.copy.attach_btn_short)}</button>
           <input type="file" id="fbw-attach-input" multiple accept="image/*" style="display:none" aria-hidden="true">`
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
          <div class="fbw-picked-list" id="fbw-picked-list"></div>
          <div class="fbw-attached" id="fbw-attached" style="display:none"></div>
          <div class="fbw-input-row">
            ${pickerBtn}
            ${attachBtn}
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
      this.els.pickedList = sheet.querySelector('#fbw-picked-list');
      this.els.attach = sheet.querySelector('#fbw-attach');
      this.els.attachInput = sheet.querySelector('#fbw-attach-input');
      this.els.attached = sheet.querySelector('#fbw-attached');
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

      // v1.1 — element picker (v1.4: multi-pin)
      if (this.els.pick) {
        this.els.pick.addEventListener('click', () => {
          if (this.pickedElements.length >= this.cfg.maxPickedElements) {
            this._showStatus(this.copy.pick_max_reached.replace('{n}', this.cfg.maxPickedElements), 'error');
            return;
          }
          this._startPointerMode();
        });
      }
      if (this.els.pickedList) {
        this.els.pickedList.addEventListener('click', e => {
          const btn = e.target.closest('.fbw-picked-clear');
          if (!btn) return;
          const idx = parseInt(btn.dataset.idx, 10);
          if (!isNaN(idx) && idx >= 0 && idx < this.pickedElements.length) {
            this.pickedElements.splice(idx, 1);
            this._renderPicked();
          }
        });
      }

      // v1.3 — attachments: click 📎 → file picker, change → add files,
      // paste → grab images from clipboard
      if (this.els.attach && this.els.attachInput) {
        this.els.attach.addEventListener('click', () => this.els.attachInput.click());
        this.els.attachInput.addEventListener('change', e => {
          const files = Array.from(e.target.files || []);
          for (const f of files) this._addAttachment(f);
          e.target.value = '';  // allow re-selecting same file later
        });
      }
      if (this.cfg.enableAttach && this.els.msg) {
        this.els.msg.addEventListener('paste', e => {
          const items = (e.clipboardData && e.clipboardData.items) || [];
          let captured = 0;
          for (const it of items) {
            if (it.kind === 'file' && /^image\//.test(it.type)) {
              const f = it.getAsFile();
              if (f) { this._addAttachment(f); captured++; }
            }
          }
          if (captured > 0) e.preventDefault();  // suppress accidental text-paste of binary
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
        this._fetchStatuses();
        this._startStatusPoll();
      } else {
        this._stopStatusPoll();
      }
    }

    // ---------- v1.4: status polling ----------
    _startStatusPoll() {
      if (!this.cfg.statusEndpoint) return;
      this._stopStatusPoll();
      const ms = Math.max(15000, this.cfg.statusPollMs | 0 || 60000);
      this._statusTimer = setInterval(() => {
        if (!this.open) { this._stopStatusPoll(); return; }
        this._fetchStatuses();
      }, ms);
    }
    _stopStatusPoll() {
      if (this._statusTimer) { clearInterval(this._statusTimer); this._statusTimer = null; }
    }
    async _fetchStatuses() {
      if (!this.cfg.statusEndpoint) return;
      const data = this._load();
      const msgs = data.messages || [];
      const names = msgs.map(m => m.server_name).filter(Boolean);
      if (names.length === 0) return;
      const headers = { 'Content-Type': 'application/json' };
      if (typeof this.cfg.fetchHeaders === 'function') {
        try {
          const extra = this.cfg.fetchHeaders() || {};
          for (const k in extra) if (extra[k] != null) headers[k] = String(extra[k]);
        } catch (_e) {}
      }
      let res;
      try {
        res = await fetch(this.cfg.statusEndpoint, {
          method: 'POST',
          headers,
          credentials: 'same-origin',
          body: JSON.stringify({ names, project: this.cfg.project }),
        });
        if (!res.ok) return;
      } catch (_e) { return; }
      let body;
      try { body = await res.json(); } catch (_e) { return; }
      const items = (body && (body.message && body.message.items)) || (body && body.items) || [];
      if (!Array.isArray(items) || items.length === 0) return;
      const byName = {};
      for (const it of items) if (it && it.name) byName[it.name] = it;
      let changed = false;
      for (const m of msgs) {
        const it = byName[m.server_name];
        if (!it) continue;
        if (m.server_status !== it.status
            || m.server_status_note !== (it.status_note || '')
            || m.server_status_changed_at !== (it.status_changed_at || '')) {
          m.server_status = it.status;
          m.server_status_note = it.status_note || '';
          m.server_status_changed_at = it.status_changed_at || '';
          changed = true;
        }
      }
      if (changed) {
        this._save(data);
        if (this.open) this._renderHistory();
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
        this.els.history.innerHTML = here.map(m => this._renderMsgRow(m)).join('');
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

    _renderMsgRow(m) {
      const meta = `${escapeHtml(m.submitter || this.copy.anon)} · ${escapeHtml(fmtTime(m.ts))}${m.sent === false ? ' · ⏳ ' + escapeHtml(this.copy.not_sent) : ''}`;
      // Attachments — clickable thumbs that open the file in a new tab
      let attHtml = '';
      const atts = Array.isArray(m.attachments) ? m.attachments : [];
      if (atts.length) {
        attHtml = `<div class="fbw-msg-attached">${atts.map(a => {
          const url = (a && a.file_url) || '';
          const name = (a && a.file_name) || '';
          if (!url) return '';
          return `<a class="fbw-msg-thumb" href="${escapeHtml(url)}" target="_blank" rel="noopener" title="${escapeHtml(name)}"><img src="${escapeHtml(url)}" alt="${escapeHtml(name)}"></a>`;
        }).join('')}</div>`;
      }
      // Pins — show selector + element text (if any)
      let pins = [];
      if (Array.isArray(m.pointed_elements) && m.pointed_elements.length) {
        pins = m.pointed_elements;
      } else if (m.pointed_element && typeof m.pointed_element === 'object') {
        pins = [m.pointed_element];
      }
      let pinHtml = '';
      if (pins.length) {
        pinHtml = `<div class="fbw-msg-pins">${pins.map(p => {
          const sel = (p && p.selector) || '';
          const txt = ((p && p.text) || '').trim();
          const short = txt ? `${txt.slice(0, 40)}${txt.length > 40 ? '…' : ''}` : sel;
          return `<span class="fbw-msg-pin" title="${escapeHtml(sel)}">📍 ${escapeHtml(short)}</span>`;
        }).join('')}</div>`;
      }
      // Status — only show once team has moved it past 'New'
      const statusHtml = this._renderStatusBadge(m);
      return `
        <div class="fbw-msg-row">
          <div class="fbw-msg">${escapeHtml(m.message)}</div>
          ${attHtml}
          ${pinHtml}
          <div class="fbw-msg-meta">${meta}</div>
          ${statusHtml}
        </div>`;
    }

    _statusLabel(s) {
      switch (s) {
        case 'Triaged':     return this.copy.status_triaged;
        case 'In Progress': return this.copy.status_in_progress;
        case 'Resolved':    return this.copy.status_resolved;
        case 'Wontfix':     return this.copy.status_wontfix;
        default:            return '';
      }
    }

    _renderStatusBadge(m) {
      const s = m && m.server_status;
      if (!s || s === 'New') return '';
      const label = this._statusLabel(s);
      if (!label) return '';
      const note = (m.server_status_note || '').trim();
      return `<div class="fbw-msg-status" data-status="${escapeHtml(s)}">
        ${escapeHtml(label)}${note ? `<span class="fbw-msg-status-note">${escapeHtml(this.copy.status_note_label)}: ${escapeHtml(note)}</span>` : ''}
      </div>`;
    }

    async send() {
      const msg = this.els.msg.value.trim();
      if (!msg) return;

      // v1.3 — upload any pending image attachments BEFORE building the
      // payload. If any fail, we still send the comment (text + uploaded
      // ones); the failed thumbs stay visible with a red mark so the user
      // can retry by removing + re-attaching.
      this.els.send.disabled = true;
      if (this.attachments.length > 0) {
        await this._uploadAllPending();
      }

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
      // v1.4 — array of pinned elements; mirror first one into pointed_element
      // for older servers / data consumers that still expect single-object shape.
      if (this.pickedElements && this.pickedElements.length) {
        entry.pointed_elements = this.pickedElements.slice();
        entry.pointed_element = this.pickedElements[0];
      }
      if (this.cfg.enableContext) entry.context = this._buildContextBundle();
      // v1.3 — only include successfully-uploaded attachments in the payload
      const uploaded = this.attachments.filter(a => a.status === 'uploaded' && a.file_url);
      if (uploaded.length) {
        entry.attachments = uploaded.map(a => ({
          file_url: a.file_url, file_name: a.file_name,
          file_size: a.file_size, mime: a.mime,
        }));
      }

      // Optimistic local persist BEFORE network
      data.submitter = submitter;
      data.messages = data.messages || [];
      data.messages.push(entry);
      this._save(data);

      // Clear input + picked element + attachments (tags stay sticky for
      // audit walks)
      this.els.msg.value = '';
      this.els.msg.style.height = 'auto';
      this.els.send.disabled = true;
      this.pickedElements = [];
      // Revoke object URLs for uploaded attachments + drop the array
      for (const a of this.attachments) {
        if (a.blobUrl) { try { URL.revokeObjectURL(a.blobUrl); } catch (_e) {} }
      }
      this.attachments = this.attachments.filter(a => a.status === 'failed');  // keep failures visible
      this._renderPicked();
      this._renderAttached();
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
        try {
          const j = await res.clone().json();
          const m = (j && j.message) || j;
          if (m && m.name) entry.server_name = String(m.name);
        } catch (_e) {}
        this._save(data);
        st.className = 'fbw-status fbw-ok';
        st.textContent = this.copy.sent_ok;
        setTimeout(() => { if (st.textContent.startsWith('✓')) st.textContent = ''; }, 2500);
        this._renderHistory();
        this._fetchStatuses();  // immediate first pull so user sees the row
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
          if (res.ok) {
            e.sent = true;
            try {
              const j = await res.clone().json();
              const m = (j && j.message) || j;
              if (m && m.name) e.server_name = String(m.name);
            } catch (_e) {}
          }
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

    // ---------- v1.4: picked elements (multi-pin) ----------
    _renderPicked() {
      if (!this.els.pickedList) return;
      const arr = this.pickedElements || [];
      if (arr.length === 0) {
        this.els.pickedList.innerHTML = '';
        return;
      }
      this.els.pickedList.innerHTML = arr.map((p, i) => {
        const sel = p.selector || '';
        const txt = (p.text || '').trim();
        const label = txt ? `${sel} · "${txt.slice(0, 40)}${txt.length > 40 ? '…' : ''}"` : sel;
        return `
          <div class="fbw-picked" title="${escapeHtml(sel)}">
            <span class="fbw-picked-icon">📍</span>
            <code class="fbw-picked-sel">${escapeHtml(label)}</code>
            <button class="fbw-picked-clear" type="button" data-idx="${i}" aria-label="${escapeHtml(this.copy.pick_clear_aria)}">×</button>
          </div>`;
      }).join('');
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
        this.pickedElements.push(this._captureElement(t));
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
        this.pickedElements.push(this._captureElement(target));
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
      const pushErr = (entry) => {
        this._consoleErrors.push(entry);
        if (this._consoleErrors.length > max) this._consoleErrors.shift();
      };
      // Click trail (passive, capture phase, ignores widget's own elements)
      document.addEventListener('click', (e) => {
        const t = e.target;
        if (!t || !t.closest) return;
        if (t.closest('.fbw-fab, .fbw-sheet, .fbw-backdrop, .fbw-picker-banner, .fbw-picker-highlight')) return;
        this._pushAction({ type: 'click', target: this._terseSelector(t), ts: Date.now() }, max);
      }, true);

      // Uncaught script errors — bubble up to window (passive)
      window.addEventListener('error', (e) => {
        pushErr({
          type: 'error',
          message: String(e && e.message || '').slice(0, 300),
          source: String(e && e.filename || '').slice(0, 200),
          line: (e && e.lineno) | 0,
          col: (e && e.colno) | 0,
          ts: Date.now(),
        });
      });
      // Unhandled promise rejections (no .catch, no await in catch context)
      window.addEventListener('unhandledrejection', (e) => {
        const reason = e && e.reason;
        const msg = (reason && (reason.message || reason.toString())) || '';
        pushErr({
          type: 'rejection',
          message: String(msg).slice(0, 300),
          ts: Date.now(),
        });
      });

      // v1.4 — explicit console.error / console.warn calls.
      // Window's 'error' event does NOT fire for these — modern browsers
      // route console.* directly to DevTools without dispatching events.
      // Monkey-patch to push to the ring buffer, then forward to the
      // original so DevTools still shows everything in its native form.
      const formatArg = (a) => {
        if (a == null) return String(a);
        if (typeof a === 'string') return a;
        if (a instanceof Error) return a.stack || a.message || String(a);
        try { return JSON.stringify(a); }
        catch (_e) { return String(a); }
      };
      const formatArgs = (args) => Array.prototype.map.call(args, formatArg).join(' ').slice(0, 500);

      if (typeof console !== 'undefined') {
        const origError = console.error && console.error.bind(console);
        if (origError && !console.__fbwPatched) {
          console.error = function () {
            try {
              pushErr({
                type: 'console.error',
                message: formatArgs(arguments),
                ts: Date.now(),
              });
            } catch (_e) {}
            return origError.apply(console, arguments);
          };
        }
        const origWarn = console.warn && console.warn.bind(console);
        if (origWarn && !console.__fbwPatched) {
          console.warn = function () {
            try {
              pushErr({
                type: 'console.warn',
                message: formatArgs(arguments),
                ts: Date.now(),
              });
            } catch (_e) {}
            return origWarn.apply(console, arguments);
          };
        }
        // Idempotency flag — prevents double-patching if widget remounts
        try { console.__fbwPatched = true; } catch (_e) {}
      }
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

    // ---------- v1.3: attachments ----------
    _addAttachment(file) {
      if (!file || !/^image\//.test(file.type)) return;
      if (this.attachments.length >= this.cfg.maxAttachments) {
        this._showStatus(this.copy.attach_too_many, 'error');
        return;
      }
      if (file.size > this.cfg.maxAttachmentBytes) {
        this._showStatus(this.copy.attach_too_big, 'error');
        return;
      }
      const att = {
        id: ++this._attachIdCounter,
        file: file,
        blobUrl: URL.createObjectURL(file),
        file_name: file.name || `pasted-${Date.now()}.png`,
        file_size: file.size,
        mime: file.type,
        status: 'pending',          // 'pending' | 'uploading' | 'uploaded' | 'failed'
        file_url: null,             // populated after upload
      };
      this.attachments.push(att);
      this._renderAttached();
    }

    _removeAttachment(id) {
      const idx = this.attachments.findIndex(a => a.id === id);
      if (idx < 0) return;
      const a = this.attachments[idx];
      if (a.blobUrl) { try { URL.revokeObjectURL(a.blobUrl); } catch (_e) {} }
      this.attachments.splice(idx, 1);
      this._renderAttached();
    }

    _renderAttached() {
      if (!this.els.attached) return;
      if (this.attachments.length === 0) {
        this.els.attached.style.display = 'none';
        this.els.attached.innerHTML = '';
        return;
      }
      this.els.attached.style.display = 'flex';
      this.els.attached.innerHTML = this.attachments.map(a => `
        <div class="fbw-thumb ${a.status === 'uploading' ? 'fbw-uploading' : ''} ${a.status === 'failed' ? 'fbw-failed' : ''}" data-attid="${a.id}" title="${escapeHtml(a.file_name)}">
          <img class="fbw-thumb-img" src="${a.blobUrl}" alt="">
          <button class="fbw-thumb-clear" type="button" aria-label="${escapeHtml(this.copy.attach_clear_aria)}" data-clear="${a.id}">×</button>
        </div>
      `).join('');
      // Wire clear buttons (delegate to avoid memory leaks across renders)
      this.els.attached.querySelectorAll('.fbw-thumb-clear').forEach(btn => {
        btn.addEventListener('click', () => this._removeAttachment(parseInt(btn.dataset.clear, 10)));
      });
    }

    async _uploadAttachment(att) {
      const fd = new FormData();
      fd.append(this.cfg.uploadFieldName || 'file', att.file, att.file_name);
      const extra = this.cfg.uploadExtraFields || {};
      for (const k in extra) fd.append(k, extra[k]);
      const headers = {};
      if (typeof this.cfg.fetchHeaders === 'function') {
        try {
          const xtra = this.cfg.fetchHeaders() || {};
          for (const k in xtra) if (xtra[k] != null) headers[k] = String(xtra[k]);
        } catch (_e) {}
      }
      // NOTE: do NOT set Content-Type — browser must set it with boundary
      const res = await fetch(this.cfg.uploadEndpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers,
        body: fd,
      });
      if (!res.ok) throw new Error('upload http ' + res.status);
      const j = await res.json().catch(() => ({}));
      // Frappe shape: { message: { file_url, file_name, ... } }
      // Generic shape: { file_url, file_name, ... }
      const m = (j && j.message) || j || {};
      if (!m.file_url) throw new Error('upload no file_url');
      return {
        file_url: m.file_url,
        file_name: m.file_name || att.file_name,
        file_size: m.file_size || att.file_size,
        mime: att.mime,
      };
    }

    async _uploadAllPending() {
      const pending = this.attachments.filter(a => a.status !== 'uploaded');
      if (pending.length === 0) return true;
      this._showStatus(this.copy.attach_uploading, '');
      let allOk = true;
      for (const att of pending) {
        att.status = 'uploading';
        this._renderAttached();
        try {
          const meta = await this._uploadAttachment(att);
          Object.assign(att, meta);
          att.status = 'uploaded';
        } catch (e) {
          att.status = 'failed';
          allOk = false;
        }
        this._renderAttached();
      }
      return allOk;
    }

    _showStatus(text, kind) {
      const st = this.els.status;
      if (!st) return;
      st.textContent = text || '';
      st.className = 'fbw-status' + (kind === 'ok' ? ' fbw-ok' : kind === 'error' ? ' fbw-error' : '');
    }

    _detectFormFactor() {
      // Prefer User-Agent Client Hints (more reliable than width on tablets
      // that fake desktop UA, and on dev tools "responsive" mode).
      try {
        if (navigator.userAgentData && typeof navigator.userAgentData.mobile === 'boolean') {
          if (navigator.userAgentData.mobile) return 'mobile';
        }
      } catch (_e) {}
      // Fallback: viewport width thresholds aligned with our @media (max-width: 720px)
      // mobile rules + Tailwind/Material/Bootstrap tablet bands.
      const w = window.innerWidth || 0;
      if (w < 768)  return 'mobile';
      if (w < 1024) return 'tablet';
      return 'desktop';
    }

    _buildContextBundle() {
      const w = window.innerWidth || 0;
      const h = window.innerHeight || 0;
      const isTouch = (typeof matchMedia === 'function')
        ? matchMedia('(pointer: coarse)').matches : false;
      const ctx = {
        url: location.href,
        pathname: location.pathname,
        hash: location.hash,
        viewport: {
          w: w, h: h,
          dpr: window.devicePixelRatio || 1,
          // v1.5 — explicit form-factor classification so triage doesn't have
          // to derive from UA + width every time.
          form_factor: this._detectFormFactor(),
          orientation: w > h ? 'landscape' : 'portrait',
          touch: isTouch,
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
