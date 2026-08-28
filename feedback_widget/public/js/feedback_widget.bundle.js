/**
 * feedback_widget.bundle.js — Frappe-aware mount of the feedback widget.
 *
 * Loaded on every desk page via `app_include_js` in hooks.py.
 * The widget core (./feedback_widget_core.js) self-registers
 * `window.FeedbackWidget` on import. We then call .mount() with config that
 * teaches it about the current Frappe route, doctype/docname, user, and CSRF.
 */
import "./feedback_widget_core.js";
import "./thong_bao_the.js";   // khai `window.FeedbackNotices.show` cho lối vào 🔔

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
    // Trả CHÍNH cái hash khi có: danh mục màn của app chủ khai theo `#/lsx`, còn sự kiện
    // mà ghi "steel-app#/lsx" thì hai bên KHÔNG khớp — báo cáo nói "56/56 màn chưa ai vào"
    // trong khi người ta đang dùng. Đo trên prod 25/08 ngay lượt dữ liệu thật đầu tiên.
    const h = (location.hash || "").split("?")[0];
    return h && h.length > 1 ? h : goc;
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
    const ct = boot.feedback_widget || {};
    if (!settings) return true; // chưa có bootinfo mở rộng → giữ nếp cũ
    // GẮN kể cả khi người này không được thấy nút: hiện nút và THU là hai việc khác nhau.
    // Bản 24/08 trả false ở đây, nên bật "ẩn nút" là mất luôn sổ chặn — mà ẩn nút cho công
    // nhân đúng là ca dùng chính của nó.
    return Boolean(settings.is_eligible) || Boolean(ct.auto_report) || Boolean(ct.collect_usage);
  }

  function init() {
    if (!shouldMount()) return;
    if (window.__FBW_FRAPPE_MOUNTED__) return;
    window.__FBW_FRAPPE_MOUNTED__ = true;

    const boot = window.frappe && window.frappe.boot;
    const settings = (boot && boot.feedback_widget_settings) || {};

    // Project slug — allow override from Feedback Settings, fallback to site-derived slug
    const customProject = (settings.project_name || "").trim();
    // KHÔNG ghim tiền tố thương hiệu vào đây. Nhánh dự phòng này từng là "dcnet-" rồi
    // thành "tamdinh-" tuỳ ai cài app sau cùng, nên cùng MỘT site sinh ra nhiều tên dự án
    // khác nhau theo thời gian: đo 26/08 trên ducan có ba giá trị cùng tồn tại —
    // `dcnet-ducan…` (183 vé), `ducan…` (22), `tamdinh-ducan…` (1, sinh tối đó). Sổ gom
    // theo dự án nên ba tên = ba hộp thư, và tin nhắn Telegram gọi khách này bằng tên
    // khách khác. Tên site đã đủ nhận dạng; muốn khác thì khai `project_name` trong Cài đặt.
    const project = customProject || siteSlug().replace(/[^a-zA-Z0-9_.-]/g, "_").slice(0, 80);

    const userId = (window.frappe.session && window.frappe.session.user) || "";

    // v1.6 — cài đặt do MÁY CHỦ quyết (Feedback Settings), đi kèm boot nên
    // không tốn thêm một vòng mạng. Site chưa migrate → boot rỗng → mặc định an toàn:
    // hiện nút như cũ, KHÔNG tự thu (không bao giờ bật một thứ ghi dữ liệu bằng suy đoán).
    const ct = (window.frappe.boot && window.frappe.boot.feedback_widget) || {};

    window.FeedbackWidget.mount({
      endpoint: "/api/method/feedback_widget.api.feedback.collect",
      statusEndpoint: "/api/method/feedback_widget.api.feedback.status_for_names",
      eventEndpoint: "/api/method/feedback_widget.api.su_kien.ghi_lo",
      inventoryEndpoint: "/api/method/feedback_widget.api.su_kien.kiem_ke_giao_dien",
      project: (ct.project || project),
      // Ai được THẤY nút: máy chủ đã suy sẵn (bật/tắt + desk + phạm vi vai trò) ở
      // `ct.show_widget`. Không hỏi lại `settings.is_eligible` — hai nguồn cho một câu
      // hỏi thì sớm muộn lệch nhau.
      showWidget: ct.show_widget === undefined ? Boolean(settings.is_eligible !== false) : !!ct.show_widget,
      autoReport: !!ct.auto_report,
      collectUsage: !!ct.collect_usage,
      usageSamplePct: ct.usage_sample_pct === undefined ? 100 : ct.usage_sample_pct,
      throttleMinutes: ct.throttle_minutes === undefined ? 10 : ct.throttle_minutes,
      maxEventsPerMinute: ct.max_events_per_minute === undefined ? 120 : ct.max_events_per_minute,
      redactKeys: Array.isArray(ct.redact_keys) ? ct.redact_keys : undefined,
      userId: userId,
      // v1.7 — khung góp ý gọn lại theo SỐ ĐO, không theo cảm giác: 164 vé do người
      // bấm trên prod 26/08 — ghim 139 (84%), ảnh 8 (4%), phân loại 3 (2%), mức độ 1.
      // Hai ô phân loại mặc định TẮT; ai cần thì bật ở Cài đặt, không phải sửa mã.
      enableTags: !!ct.hien_tag,
      enableAttach: ct.cho_dinh_anh === undefined ? true : !!ct.cho_dinh_anh,
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

    // v1.7 — lối vào "Thông báo tính năng mới". Máy chủ (`api.thong_bao`) và phần vẽ
    // thẻ thông báo (`window.FeedbackNotices`) do bản cập nhật tính năng cung cấp;
    // THIẾU cái nào thì lối này không hiện — không bao giờ mời người dùng vào ngõ cụt.
    dangKyLoiThongBao();

    // Refresh widget's idea of the current screen on every Frappe route change
    try {
      window.frappe.router.on("change", function () {
        if (window.FeedbackWidget && window.FeedbackWidget.refreshScreen) {
          window.FeedbackWidget.refreshScreen();
        }
      });
    } catch (_e) {}
  }

  // ---------- v1.7: lối vào thông báo tính năng ----------
  // Tên sự kiện realtime PHẢI khớp `feedback_widget.api.thong_bao.SU_KIEN` — một test đọc
  // hằng số bên Python rồi soi chính tệp này, nên hai bên không thể trôi lệch trong im lặng
  // (đổi tên một bên = thông báo lại chỉ tới sau F5, đúng bệnh đang chữa, và không có lỗi).
  var SU_KIEN_THONG_BAO = "fbw_thong_bao_moi";
  var NHIP_MAT_SOCKET_S = 90;    // socket chết → hỏi lại mỗi 90 giây
  var NHIP_LUOI_AN_TOAN_S = 900; // socket sống → vẫn hỏi lại 15 phút/lần, phòng khi rơi phao
  var NHIP_QUAY_LAI_TAB_S = 60;  // quay lại tab sau ≥60 giây → hỏi lại luôn
  // Cắm tai nghe realtime phải THỬ LẠI: `frappe.realtime` (và cả `.on`) có mặt SỚM HƠN cái
  // socket nó ghi vào — đo trên prod 28/08: `frappe.realtime.on` có ở giây 1,95, widget gọi
  // `on()` ở giây 2,60, socket mãi giây 3,13 mới dựng xong. `RealTimeClient.on()` của Frappe
  // là `if (this.socket) { … }`: KHÔNG có socket thì nó lặng lẽ không đăng ký gì, không ném
  // lỗi, không trả giá trị nào — nên bản trước tưởng cắm được rồi và không bao giờ thử lại
  // (đo: `socket.listeners("fbw_thong_bao_moi").length` = 0 trên mọi máy đang mở).
  var NHIP_THU_NGHE_MS = 500;    // 500ms × 120 = 60 giây, thừa sức cho máy xưởng chậm
  var SO_LAN_THU_NGHE = 120;

  function dangKyLoiThongBao() {
    // `sanSang` = MÁY CHỦ đã trả lời được, KHÔNG phải "mã vẽ thẻ đã có": hai thứ lên
    // theo hai nhịp khác nhau (phần vẽ nằm trong bundle, endpoint đi theo migrate).
    // Hỏi máy chủ, tối đa 2 lần rồi rút — một tính năng phụ không được quyền đổ
    // traceback 417 vào console của MỌI màn, console đỏ làm người sau bỏ qua cả lỗi thật.
    var chuaXem = 0, daHoi = false, sanSang = false, daDay = {}, soLanLoi = 0;
    // Mốc lần hỏi gần nhất + cờ đang-hỏi: hai nhịp (phao realtime + nhịp dự phòng) có thể
    // gọi trùng nhau, không có cờ này thì một thông báo "Tất cả" đẻ ra chùm request.
    var lanCuoi = 0, dangHoi = false;
    function coVeThe() {
      return !!(window.FeedbackNotices && window.FeedbackNotices.show);
    }
    function dem() {
      if (!coVeThe() || soLanLoi >= 2 || dangHoi) return;
      daHoi = true;
      dangHoi = true;
      window.frappe.call({
        method: "feedback_widget.api.thong_bao.cua_toi",
        error: function () { dangHoi = false; lanCuoi = Date.now(); soLanLoi += 1; sanSang = false; },
        callback: function (r) {
          var ds = (r && r.message) || [];
          dangHoi = false;
          lanCuoi = Date.now();
          sanSang = true;
          chuaXem = ds.length;
          window.__fbw_thong_bao__ = ds;
          dayCaiRieng(ds);
        },
      });
    }
    /**
     * ĐẨY thẳng thành thẻ, nhưng CHỈ với thông báo gửi riêng cho một người: đó là
     * người đã báo vé, và cả lý do tính năng này tồn tại là để họ biết việc mình báo
     * đã được sửa (đo prod 26/08: 74 vé Resolved, 0 lượt báo ngược). Thông báo gửi cả
     * nhà chỉ hiện chấm đỏ trên nút — đẩy mọi thứ như nhau thì cái loa sẽ bị tắt, và
     * lúc đó cái ĐÁNG đẩy cũng chết theo. Mỗi thông báo đẩy đúng một lần mỗi lần tải trang.
     */
    function dayCaiRieng(ds) {
      var rieng = (ds || []).filter(function (tb) {
        return tb.pham_vi === "Một người" && !daDay[tb.name];
      });
      if (!rieng.length) return;
      // KHÔNG chặn số thẻ: chủ đầu tư chốt 26/08 "cần gửi bao nhiêu cứ gửi". Chồng thẻ
      // tự cuộn được (xem `thong_bao_the.js`) nên nhiều thẻ không khoá màn hình.
      rieng.forEach(function (tb) { daDay[tb.name] = 1; });
      window.FeedbackNotices.show(rieng);
    }

    window.FeedbackWidget.registerAction({
      id: "thong-bao",
      icon: "🔔",
      label: "Thông báo tính năng mới",
      order: 30,
      // `enabled` được gọi mỗi lần mở menu ⇒ cũng là nhịp hỏi số chưa xem lần đầu,
      // sau khi bản cập nhật lên mà không cần nạp lại trang.
      enabled: function () {
        if (!daHoi) dem();
        return sanSang;      // chỉ hiện khi máy chủ ĐÃ trả lời được
      },
      badge: function () { return chuaXem || 0; },
      onClick: function () {
        window.FeedbackNotices.show(window.__fbw_thong_bao__ || []);
        // Người dùng vừa xem xong: đếm lại để badge không nói dối ở lần mở sau.
        window.setTimeout(dem, 1500);
      },
    });
    dem();

    // ---------- v1.8: thông báo tới NGAY, không chờ tải lại trang ----------
    // Trước bản này, thông báo chỉ được hỏi đúng MỘT lần mỗi lần tải trang (ở `dem()` phía
    // trên) — gửi xong thì người dùng phải F5 mới thấy. Hai đường, CẢ HAI đều cần:
    //   (a) phao realtime của Frappe (socket.io) — tới trong khoảng một giây;
    //   (b) nhịp hỏi lại dự phòng — socket có thể chết mà trang vẫn chạy bình thường
    //       (`RealTimeClient` chỉ thử nối lại 3 lần rồi bỏ cuộc, không một dòng lỗi), và
    //       có site tắt hẳn async. Không có (b) thì "tới ngay" lặng lẽ thành "không bao
    //       giờ tới" ở đúng chỗ khó phát hiện nhất.
    function socketSong() {
      try {
        var s = window.frappe && window.frappe.realtime && window.frappe.realtime.socket;
        return !!(s && s.connected);
      } catch (_e) { return false; }
    }
    // Chốt chống đăng ký hai lần: giữ CHÍNH cái socket đã cắm, không giữ một cờ boolean —
    // cờ boolean không phân biệt được "đã cắm rồi" với "socket đã bị thay". Cắm trùng thì
    // mỗi phao đẻ ra N lượt hỏi máy chủ và N chồng thẻ.
    var socketDangNghe = null;
    function ngheRealtime() {
      try {
        var rt = window.frappe && window.frappe.realtime;
        if (!rt || typeof rt.on !== "function") return false;
        // ĐIỀU KIỆN THẬT là `rt.socket`, không phải `rt.on`: `on()` chỉ đăng ký khi socket
        // đã dựng, còn không thì nó im lặng bỏ qua. Site tắt async (`boot.disable_async`)
        // thì socket KHÔNG BAO GIỜ có — vòng thử lại tự hết hạn và nhịp hỏi lại dự phòng
        // bên dưới gánh, đúng như trước.
        var s = rt.socket;
        if (!s) return false;
        if (socketDangNghe === s) return true;   // đã cắm đúng socket này rồi
        socketDangNghe = s;
        rt.on(SU_KIEN_THONG_BAO, function () {
          // Rải 0-1,5 giây: một thông báo "Tất cả" đánh thức MỌI máy đang mở cùng lúc.
          window.setTimeout(dem, Math.floor(Math.random() * 1500));
        });
        // Socket rớt rồi nối lại: tai nghe socket.io còn nguyên (cùng một đối tượng
        // `Socket`), nhưng phao bắn TRONG lúc rớt thì mất hẳn — hỏi lại một nhịp khi nối
        // lại. Cắm trong nhánh đã chống trùng nên không đẻ thêm tai nghe `connect`.
        if (typeof s.on === "function") {
          s.on("connect", function () { window.setTimeout(dem, 500); });
        }
        return true;
      } catch (_e) { return false; }
    }
    if (!ngheRealtime()) {
      // Chưa cắm được thì thử lại theo nhịp ngắn, có TRẦN: một tính năng phụ không được
      // quyền để lại một `setInterval` chạy mãi trên mọi màn.
      try {
        var lanThuNghe = 0;
        var nhipNghe = window.setInterval(function () {
          lanThuNghe += 1;
          if (ngheRealtime() || lanThuNghe >= SO_LAN_THU_NGHE) window.clearInterval(nhipNghe);
        }, NHIP_THU_NGHE_MS);
      } catch (_e) {}
    }
    try {
      window.setInterval(function () {
        // Vòng thử lại phía trên có trần 60 giây; nhịp này gánh nốt hai ca hiếm: socket
        // dựng muộn hơn thế, và socket bị thay bằng đối tượng khác. Hàm đã chống trùng
        // nên gọi lại là vô hại.
        ngheRealtime();
        // Tab ẩn thì không hỏi: người ta không nhìn, mà thông báo vẫn còn nguyên khi
        // họ quay lại (máy chủ chỉ bỏ nó đi khi người dùng BẤM).
        if (document.hidden) return;
        var cach = (Date.now() - lanCuoi) / 1000;
        if (cach >= (socketSong() ? NHIP_LUOI_AN_TOAN_S : NHIP_MAT_SOCKET_S)) dem();
      }, 15000);
      document.addEventListener("visibilitychange", function () {
        if (document.hidden) return;
        if ((Date.now() - lanCuoi) / 1000 >= NHIP_QUAY_LAI_TAB_S) dem();
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
