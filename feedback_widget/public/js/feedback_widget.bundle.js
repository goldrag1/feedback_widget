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
    try {
      const r = window.frappe.get_route ? window.frappe.get_route() : [];
      return Array.isArray(r) ? r.join("/") : String(r || "");
    } catch (_e) { return location.pathname.replace(/^\/app\/?/, ""); }
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

  function init() {
    if (window.__FBW_FRAPPE_MOUNTED__) return;
    window.__FBW_FRAPPE_MOUNTED__ = true;

    // Project slug — same site can host multiple Frappe apps; tag by sitename
    // so multiple demos at different bench ports stay separate in localStorage.
    const project = ("dcnet-" + siteSlug()).replace(/[^a-zA-Z0-9_.-]/g, "_").slice(0, 80);

    window.FeedbackWidget.mount({
      endpoint: "/api/method/feedback_widget.api.feedback.collect",
      project: project,
      language: "vi",
      primaryColor: "#1f3a5f",
      fabColor: "#047857",
      getScreenId: currentRoute,
      getScreenName: currentRouteName,
      getContext: getContext,
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
