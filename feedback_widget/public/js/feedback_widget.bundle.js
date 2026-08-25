/**
 * feedback_widget.bundle.js — Frappe-aware mount of the feedback widget.
 *
 * Loaded on every desk page via `app_include_js` in hooks.py.
 * The widget core (./feedback_widget_core.js) self-registers
 * `window.FeedbackWidget` on import. We then call .mount() with config that
 * teaches it about the current Frappe route, doctype/docname, user, and CSRF.
 */
import "./feedback_widget_core.js";

(function () {
  if (window.__FBW_FRAPPE_MOUNTED__) return;

  // Frappe loads bundles before frappe.boot is fully initialised on first paint.
  // Wait for `frappe.boot` + `frappe.router` to exist, then mount once.
  function ready() {
    return typeof window.frappe !== "undefined"
      && window.frappe.boot
      && window.frappe.router
      && typeof window.FeedbackWidget !== "undefined";
  }

  function siteSlug() {
    try { return (window.frappe.boot && window.frappe.boot.sitename) || location.hostname; }
    catch (_e) { return location.hostname; }
  }

  function currentRoute() {
    // PHẢI kèm hash: app một-trang (steel_app, mọi SPA cắm vào desk) điều hướng bằng
    // `#/...` trong khi `frappe.get_route()` chỉ trả tên TRANG ("steel-app"). Thiếu hash
    // thì 58 màn gộp thành MỘT dòng trong sổ và mọi câu hỏi "màn nào" mất nghĩa —
    // đo trong trình duyệt 25/08: 100% sự kiện rơi vào screen_id "steel-app".
    let goc = "";
    try {
      const r = window.frappe.get_route ? window.frappe.get_route() : [];
      goc = Array.isArray(r) ? r.join("/") : String(r || "");
    } catch (_e) { goc = location.pathname.replace(/^\/app\/?/, ""); }
    const h = (location.hash || "").split("?")[0];
    return h && h.length > 1 ? goc + h : goc;
  }

  function currentRouteName() {
    try {
      const r = window.frappe.get_route ? window.frappe.get_route() : [];
      if (!Array.isArray(r) || r.length === 0) return document.title || "Desk";
      // Pretty-format common shapes: ["Form","Sales Invoice","SI-001"] → "Sales Invoice · SI-001"
      if (r[0] === "Form" && r.length >= 3) return `${r[1]} · ${r[2]}`;
      if (r[0] === "List" && r.length >= 2) return `${r[1]} (List)`;
      if (r[0] === "Tree" && r.length >= 2) return `${r[1]} (Tree)`;
      if (r[0] === "Report" && r.length >= 2) return `${r[1]} (Report)`;
      if (r[0] === "Workspaces" && r.length >= 2) return `${r[1]} (Workspace)`;
      if (r[0] === "query-report" && r.length >= 2) return `${r[1]} (Query Report)`;
      return r.join(" · ");
    } catch (_e) { return document.title || ""; }
  }

  function getContext() {
    const ctx = { route: currentRoute() };
    try {
      // Identify Frappe app version when available
      if (window.frappe.boot && window.frappe.boot.versions) {
        const v = window.frappe.boot.versions;
        ctx.versions = {
          frappe: v.frappe || "",
          erpnext: v.erpnext || "",
        };
      }
      const u = window.frappe.session && window.frappe.session.user;
      if (u) ctx.user = u;
      const ud = window.frappe.boot && window.frappe.boot.user;
      if (ud) {
        if (ud.full_name) ctx.user_full_name = ud.full_name;
        if (Array.isArray(ud.roles)) ctx.roles = ud.roles.slice(0, 12);
      }
      // If we're on a form route, capture the doctype/docname/docstatus
      const r = window.frappe.get_route ? window.frappe.get_route() : [];
      if (Array.isArray(r) && r[0] === "Form" && r[1]) {
        ctx.doctype = r[1];
        if (r[2]) ctx.docname = r[2];
        try {
          const cur = window.cur_frm;
          if (cur && cur.doc && cur.doc.name === r[2]) {
            ctx.docstatus = cur.doc.docstatus;
            if (cur.doc.workflow_state) ctx.workflow_state = cur.doc.workflow_state;
          }
        } catch (_e) {}
      } else if (Array.isArray(r) && (r[0] === "List" || r[0] === "Tree" || r[0] === "Report") && r[1]) {
        ctx.doctype = r[1];
      }
    } catch (_e) {}
    return ctx;
  }

  function shouldMount() {
    const boot = window.frappe && window.frappe.boot;
    if (!boot) return false;
    const settings = boot.feedback_widget_settings;
    if (!settings) return true; // fallback if bootinfo extension not loaded
    return Boolean(settings.is_eligible);
  }

  function init() {
    if (!shouldMount()) return;
    if (window.__FBW_FRAPPE_MOUNTED__) return;
    window.__FBW_FRAPPE_MOUNTED__ = true;

    const boot = window.frappe && window.frappe.boot;
    const settings = (boot && boot.feedback_widget_settings) || {};

    // Project slug — allow override from Feedback Settings, fallback to site-derived slug
    const customProject = (settings.project_name || "").trim();
    const project = customProject || ("tamdinh-" + siteSlug()).replace(/[^a-zA-Z0-9_.-]/g, "_").slice(0, 80);

    const userId = (window.frappe.session && window.frappe.session.user) || "";

    // v1.6 — cài đặt do MÁY CHỦ quyết (Feedback Widget Settings), đi kèm boot nên
    // không tốn thêm một vòng mạng. Site chưa migrate → boot rỗng → mặc định an toàn:
    // hiện nút như cũ, KHÔNG tự thu (không bao giờ bật một thứ ghi dữ liệu bằng suy đoán).
    const ct = (window.frappe.boot && window.frappe.boot.feedback_widget) || {};

    window.FeedbackWidget.mount({
      endpoint: "/api/method/feedback_widget.api.feedback.collect",
      statusEndpoint: "/api/method/feedback_widget.api.feedback.status_for_names",
      eventEndpoint: "/api/method/feedback_widget.api.su_kien.ghi_lo",
      inventoryEndpoint: "/api/method/feedback_widget.api.su_kien.kiem_ke_giao_dien",
      project: (ct.project || project),
      showWidget: ct.show_widget === undefined ? true : !!ct.show_widget,
      autoReport: !!ct.auto_report,
      collectUsage: !!ct.collect_usage,
      usageSamplePct: ct.usage_sample_pct === undefined ? 100 : ct.usage_sample_pct,
      throttleMinutes: ct.throttle_minutes === undefined ? 10 : ct.throttle_minutes,
      maxEventsPerMinute: ct.max_events_per_minute === undefined ? 120 : ct.max_events_per_minute,
      redactKeys: Array.isArray(ct.redact_keys) ? ct.redact_keys : undefined,
      userId: userId,
      language: "vi",
      primaryColor: settings.primary_color || "#1f3a5f",
      fabColor: settings.fab_color || "#047857",
      getScreenId: currentRoute,
      getScreenName: currentRouteName,
      getContext: getContext,
      // v1.3 — image attachments go through Frappe's standard upload_file
      // endpoint. is_private=1 keeps screenshots off the public web; folder
      // omitted so Frappe uses its default 'Home/Attachments' (always exists).
      uploadEndpoint: "/api/method/upload_file",
      uploadExtraFields: { is_private: "1" },
      fetchHeaders: function () {
        const t = (window.frappe && window.frappe.csrf_token) || "";
        return t ? { "X-Frappe-CSRF-Token": t } : {};
      },
    });

    // Refresh widget's idea of the current screen on every Frappe route change
    try {
      window.frappe.router.on("change", function () {
        if (window.FeedbackWidget && window.FeedbackWidget.refreshScreen) {
          window.FeedbackWidget.refreshScreen();
        }
      });
    } catch (_e) {}
  }

  // Poll for frappe.boot — desk init is async; bail after 30s of no boot
  let tries = 0;
  const maxTries = 60;  // 60 × 500ms = 30s
  const tick = setInterval(function () {
    tries++;
    if (ready()) { clearInterval(tick); init(); return; }
    if (tries >= maxTries) clearInterval(tick);
  }, 500);
})();
