/* KỊCH BẢN MÀN — phần VẼ (spec §5, §6). Khai `window.FeedbackPlaybook`.
 *
 * Tệp RIÊNG, theo đúng quy ước của `thong_bao_the.js`: core.js do phiên khác giữ. Ở đây
 * chỉ vẽ; mọi luật (khớp bước, chấm, điểm, nhắc) nằm ở máy chủ (`kich_ban.py`, `diem.py`,
 * `nhac.py`) và đi tới qua `api/kich_ban.cua_toi`. Không chấm gì ở trình duyệt — hai nơi
 * cùng chấm thì sớm muộn lệch nhau, và người dùng thấy ✓ mà không có điểm.
 *
 * Năm thứ được vẽ:
 *  1. Hướng dẫn lần đầu: viền sáng quanh chỗ `chi_vao`, "1/4", Tiếp / Bỏ qua. Không tìm
 *     thấy selector ⇒ thẻ vẫn hiện (giữa màn) và ghi `Feedback Event kind='loi'`
 *     `kich-ban-chi-vao-mat:<KB>:<thu_tu>` — giao diện đổi làm hỏng hướng dẫn thì thành vé
 *     máy, không hỏng im lặng.
 *  2. Thẻ mục tiêu (🎯), Thành tích (🏅), Bảng vàng (🏆): mở từ menu nút 💬.
 *  3. Chúc mừng: gộp mọi dòng điểm/huân chương chưa báo thành MỘT thẻ, rồi `da_bao()`.
 *  4. Hỏi cảm nhận khi vừa xong chặng: 👍 / 👎 + ô gõ không bắt buộc, có "Bỏ qua".
 *  5. Mẹo tại chỗ (bị chặn, xong bước, hướng dẫn bỏ dở): thẻ nhỏ, mỗi mẹo một lần mỗi phiên.
 *
 * Ô bấm ≥ 44px, chạy ở 390px (spec Global Constraints).
 */
(function (global) {
  var API = "feedback_widget.api.kich_ban.";
  var st = { du: null, man: null, tour: null, daTuBat: {}, daBaoLoi: {} };

  // ---------- tiện ích ----------
  function goi(ham, args, cb) {
    try {
      global.frappe.call({
        method: API + ham, args: args || {}, type: "POST",
        error: function () { if (cb) cb(null); },
        callback: function (r) { if (cb) cb(r ? r.message : null); },
      });
    } catch (_e) { if (cb) cb(null); }
  }

  function el(tag, cls, chu) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (chu !== undefined && chu !== null) e.textContent = chu;
    return e;
  }

  function nut(chu, kieu, onclick) {
    var b = el("button", "fbw-kb-nut" + (kieu ? " fbw-kb-nut-" + kieu : ""), chu);
    b.type = "button";
    b.onclick = onclick;
    return b;
  }

  // Mỗi mẹo / câu hỏi chỉ hiện MỘT lần mỗi phiên trình duyệt: `cua_toi` được gọi lại mỗi
  // lần đổi route, mà một mẹo bật lại sau mỗi cú bấm là đúng loại tiếng ồn khiến người ta
  // tắt hết thẻ của widget.
  function daHien(khoa) {
    try {
      var k = "fbw_kb_hien";
      var m = JSON.parse(sessionStorage.getItem(k) || "{}");
      if (m[khoa]) return true;
      m[khoa] = 1;
      sessionStorage.setItem(k, JSON.stringify(m));
      return false;
    } catch (_e) {
      st._hien = st._hien || {};
      if (st._hien[khoa]) return true;
      st._hien[khoa] = 1;
      return false;
    }
  }

  function hep() {
    try { return global.matchMedia("(max-width: 480px)").matches; } catch (_e) { return false; }
  }

  var CSS = [
    ".fbw-kb-nen{position:fixed;inset:0;background:rgba(17,24,39,.45);z-index:100000;display:flex;align-items:center;justify-content:center;padding:12px}",
    ".fbw-kb-khay{background:#fff;color:#111827;border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.25);width:min(460px,100%);max-height:calc(100vh - 24px);overflow:auto;font:14px/1.5 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}",
    "@media (max-width:480px){.fbw-kb-nen{align-items:flex-end;padding:0}.fbw-kb-khay{width:100%;border-radius:14px 14px 0 0;max-height:88vh}}",
    ".fbw-kb-dau{display:flex;align-items:flex-start;gap:8px;padding:14px 14px 6px 16px}",
    ".fbw-kb-tieu{font-weight:700;font-size:16px;flex:1}",
    ".fbw-kb-phu{color:#6b7280;font-size:13px;padding:0 16px 8px}",
    ".fbw-kb-than{padding:4px 16px 12px}",
    ".fbw-kb-chan{display:flex;flex-wrap:wrap;gap:8px;padding:10px 16px 16px;border-top:1px solid #f3f4f6}",
    ".fbw-kb-nut{min-height:44px;min-width:44px;padding:8px 14px;border-radius:9px;border:1px solid #d1d5db;background:#fff;color:#374151;font:600 14px system-ui,sans-serif;cursor:pointer}",
    ".fbw-kb-nut-chinh{background:#047857;border-color:#047857;color:#fff}",
    ".fbw-kb-nut-dong{border:none;background:transparent;font-size:20px;color:#6b7280;padding:4px 10px}",
    ".fbw-kb-buoc{display:flex;gap:10px;align-items:flex-start;padding:9px 6px;border-radius:8px;min-height:44px;box-sizing:border-box}",
    ".fbw-kb-buoc.fbw-kb-sang{background:#fef3c7;outline:2px solid #f59e0b}",
    ".fbw-kb-buoc.fbw-kb-bam{cursor:pointer}",
    ".fbw-kb-dau-buoc{width:22px;flex:none;text-align:center;font-weight:700}",
    ".fbw-kb-mota{flex:1}",
    ".fbw-kb-diem{color:#047857;font-weight:700;white-space:nowrap}",
    ".fbw-kb-chang-ds{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 8px}",
    ".fbw-kb-chip{border:1px solid #e5e7eb;border-radius:999px;padding:3px 10px;font-size:12.5px;color:#4b5563;background:#f9fafb}",
    ".fbw-kb-chip.fbw-kb-xong{background:#ecfdf5;border-color:#a7f3d0;color:#047857}",
    ".fbw-kb-chip.fbw-kb-nay{background:#eff6ff;border-color:#93c5fd;color:#1d4ed8;font-weight:700}",
    ".fbw-kb-thanh{height:10px;background:#e5e7eb;border-radius:999px;overflow:hidden;margin:6px 0 4px}",
    ".fbw-kb-thanh>div{height:100%;background:#047857}",
    ".fbw-kb-bang{width:100%;border-collapse:collapse;font-size:13.5px}",
    ".fbw-kb-bang td,.fbw-kb-bang th{padding:8px 6px;border-bottom:1px solid #f3f4f6;text-align:left}",
    ".fbw-kb-bang tr.fbw-kb-toi td{background:#ecfdf5;font-weight:700}",
    ".fbw-kb-tab{display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;align-items:center}",
    ".fbw-kb-tab .fbw-kb-nut.fbw-kb-on{background:#1f3a5f;border-color:#1f3a5f;color:#fff}",
    ".fbw-kb-tab select{min-height:44px;border:1px solid #d1d5db;border-radius:9px;padding:0 8px;font:14px system-ui,sans-serif;max-width:100%}",
    ".fbw-kb-chong{position:fixed;right:18px;bottom:92px;z-index:99998;display:flex;flex-direction:column;gap:10px;max-width:min(360px,calc(100vw - 36px));max-height:calc(100vh - 150px);overflow-y:auto}",
    "@media (max-width:480px){.fbw-kb-chong{left:12px;right:12px;bottom:76px;max-width:none}}",
    ".fbw-kb-the{background:#fff;border:1px solid #d1d5db;border-left:4px solid #f59e0b;border-radius:10px;box-shadow:0 6px 20px rgba(0,0,0,.14);padding:12px 14px;font:14px/1.45 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;color:#111827}",
    ".fbw-kb-the.fbw-kb-mung{border-left-color:#047857}",
    ".fbw-kb-the .fbw-kb-hang{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}",
    ".fbw-kb-the textarea{width:100%;box-sizing:border-box;min-height:56px;margin-top:8px;border:1px solid #d1d5db;border-radius:8px;padding:6px 8px;font:14px system-ui,sans-serif}",
    ".fbw-kb-vien{position:fixed;z-index:100001;border-radius:8px;box-shadow:0 0 0 3px #fbbf24,0 0 0 9999px rgba(17,24,39,.5),0 0 18px 6px rgba(251,191,36,.8);pointer-events:none;transition:all .18s ease}",
    ".fbw-kb-man-toi{position:fixed;inset:0;z-index:100001;background:rgba(17,24,39,.5)}",
    ".fbw-kb-hd{position:fixed;z-index:100002;background:#fff;color:#111827;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,.3);padding:14px 16px;width:min(340px,calc(100vw - 24px));box-sizing:border-box;font:14px/1.5 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}",
    ".fbw-kb-hd .fbw-kb-so{color:#6b7280;font-size:12.5px;font-weight:600}",
  ].join("\n");

  function napCss() {
    if (document.getElementById("fbw-kb-css")) return;
    var s = el("style");
    s.id = "fbw-kb-css";
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  // ---------- khay (hộp thoại giữa màn / tấm trượt trên điện thoại) ----------
  function moKhay(tieuDe, phu) {
    napCss();
    dongKhay();
    var nen = el("div", "fbw-kb-nen");
    nen.id = "fbw-kb-khay";
    var khay = el("div", "fbw-kb-khay");
    khay.setAttribute("role", "dialog");
    var dau = el("div", "fbw-kb-dau");
    dau.appendChild(el("div", "fbw-kb-tieu", tieuDe));
    var x = nut("✕", "dong", dongKhay);
    x.setAttribute("aria-label", "Đóng");
    dau.appendChild(x);
    khay.appendChild(dau);
    if (phu) khay.appendChild(el("div", "fbw-kb-phu", phu));
    var than = el("div", "fbw-kb-than");
    var chan = el("div", "fbw-kb-chan");
    khay.appendChild(than);
    khay.appendChild(chan);
    nen.appendChild(khay);
    nen.addEventListener("click", function (e) { if (e.target === nen) dongKhay(); });
    document.body.appendChild(nen);
    return { than: than, chan: chan, khay: khay };
  }

  function dongKhay() {
    var c = document.getElementById("fbw-kb-khay");
    if (c && c.parentNode) c.parentNode.removeChild(c);
  }

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (st.tour) { st.tour.dong("Đang xem"); return; }
    dongKhay();
  });

  // ---------- chồng thẻ nhỏ (mẹo, chúc mừng, hỏi cảm nhận) ----------
  // DÙNG CHUNG một chồng với thẻ thông báo (`thong_bao_the.js`, cùng id): hai chồng riêng nằm
  // đúng một góc thì chồng sau che nút của chồng trước — đo trong Chrome, nút "Để mai" của thẻ
  // nhắc bị thẻ chúc mừng đè, bấm không tới. Bên nào tạo trước thì bên kia nhận lại theo id.
  function chong() {
    napCss();
    var c = document.getElementById("fbw-thong-bao-lop");
    if (c) return c;
    c = el("div", "fbw-kb-chong");
    c.id = "fbw-thong-bao-lop";
    document.body.appendChild(c);
    return c;
  }

  function theNho(cls) {
    var c = chong();
    var t = el("div", "fbw-kb-the" + (cls ? " " + cls : ""));
    t.dong = function () {
      if (t.parentNode) t.parentNode.removeChild(t);
      if (!c.childNodes.length && c.parentNode) c.parentNode.removeChild(c);
    };
    c.appendChild(t);
    return t;
  }

  // ---------- tìm chỗ chỉ vào ----------
  function hienThi(e) {
    try {
      if (!e || !e.getClientRects().length) return false;
      var r = e.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return false;
      var cs = global.getComputedStyle(e);
      return cs.visibility !== "hidden" && cs.display !== "none" && Number(cs.opacity) > 0.05;
    } catch (_e) { return false; }
  }

  /** Thử từng selector trong `chi_vao` (tách `;`), lấy phần tử HIỂN THỊ đầu tiên. Selector
   *  sai cú pháp không được làm vỡ cả hướng dẫn — coi như không tìm thấy. */
  function timCho(chiVao) {
    var ds = String(chiVao || "").split(";");
    for (var i = 0; i < ds.length; i++) {
      var s = ds[i].trim();
      if (!s) continue;
      var cac;
      try { cac = document.querySelectorAll(s); } catch (_e) { continue; }
      for (var j = 0; j < cac.length; j++) if (hienThi(cac[j])) return cac[j];
    }
    return null;
  }

  function baoChiVaoMat(kb, thuTu) {
    var k = kb + ":" + thuTu;
    if (st.daBaoLoi[k]) return;
    st.daBaoLoi[k] = 1;
    // Đẩy thẳng vào SỔ của widget (cùng lô với các sự kiện khác), không mở vé riêng: chữ
    // ký cố định nên vé máy tự gom theo kịch bản + thẻ.
    try {
      var w = global.__fbw_instance__;
      if (w && typeof w._pushEvent === "function") {
        w._pushEvent({ kind: "loi", message: "kich-ban-chi-vao-mat:" + k });
        if (typeof w._flushEvents === "function") w._flushEvents();
      }
    } catch (_e) {}
  }

  // ---------- 1. hướng dẫn lần đầu ----------
  function moHuongDan(tuDau) {
    var du = st.du;
    if (!du || !du.kich_ban || !du.huong_dan || !(du.huong_dan.cac_the || []).length) return false;
    if (st.tour) st.tour.dong(null);
    dongKhay();
    napCss();
    var cacThe = du.huong_dan.cac_the;
    var kb = du.kich_ban;
    var i = tuDau ? 0 : Math.min(Math.max(du.huong_dan.the || 0, 0), cacThe.length - 1);
    var vien = null, toi = null, the = null, cho = null;

    function luu(trangThai, so) {
      goi("huong_dan", { kich_ban: kb, trang_thai: trangThai, the: so });
      if (st.du && st.du.kich_ban === kb) {
        st.du.huong_dan.trang_thai = trangThai;
        st.du.huong_dan.the = so;
      }
    }

    function go() {
      [vien, toi, the].forEach(function (x) { if (x && x.parentNode) x.parentNode.removeChild(x); });
      vien = toi = the = null;
    }

    function datViTri() {
      if (!the) return;
      var w = the.offsetWidth, h = the.offsetHeight;
      var W = global.innerWidth, H = global.innerHeight;
      if (!cho || !vien) {
        the.style.left = Math.max(12, (W - w) / 2) + "px";
        the.style.top = Math.max(12, (H - h) / 2) + "px";
        return;
      }
      var r = cho.getBoundingClientRect();
      var p = 6;
      vien.style.left = r.left - p + "px";
      vien.style.top = r.top - p + "px";
      vien.style.width = r.width + 2 * p + "px";
      vien.style.height = r.height + 2 * p + "px";
      var viTri = (cacThe[i].vi_tri || "tự động");
      var duoi = r.bottom + 14, tren = r.top - h - 14;
      var top;
      if (viTri === "trên") top = tren >= 8 ? tren : duoi;
      else if (viTri === "dưới") top = duoi + h <= H - 8 ? duoi : tren;
      else top = duoi + h <= H - 8 ? duoi : (tren >= 8 ? tren : H - h - 12);
      var left = Math.min(Math.max(12, r.left + r.width / 2 - w / 2), W - w - 12);
      the.style.top = Math.max(8, top) + "px";
      the.style.left = left + "px";
    }

    function ve() {
      go();
      var t = cacThe[i];
      cho = t.chi_vao ? timCho(t.chi_vao) : null;
      if (t.chi_vao && !cho) baoChiVaoMat(kb, i + 1);
      if (cho) {
        try { cho.scrollIntoView({ block: "center", inline: "nearest" }); } catch (_e) {}
        vien = el("div", "fbw-kb-vien");
        document.body.appendChild(vien);
      } else {
        toi = el("div", "fbw-kb-man-toi");
        document.body.appendChild(toi);
      }
      the = el("div", "fbw-kb-hd");
      the.setAttribute("role", "dialog");
      the.setAttribute("data-kb-the", String(i + 1));
      the.appendChild(el("div", "fbw-kb-so", (i + 1) + "/" + cacThe.length + " · " + (du.ten || "Hướng dẫn")));
      var tieu = el("div", null, t.tieu_de || "");
      tieu.style.cssText = "font-weight:700;font-size:15.5px;margin:2px 0 4px";
      the.appendChild(tieu);
      if (t.noi_dung) {
        var nd = el("div", null, t.noi_dung);
        nd.style.cssText = "color:#374151;white-space:pre-line";
        the.appendChild(nd);
      }
      var hang = el("div");
      hang.style.cssText = "display:flex;gap:8px;margin-top:12px;flex-wrap:wrap";
      hang.appendChild(nut("Bỏ qua", null, function () { dong("Bỏ qua"); }));
      if (i > 0) hang.appendChild(nut("‹ Trước", null, function () { i -= 1; luu("Đang xem", i); ve(); }));
      var cuoi = i === cacThe.length - 1;
      var tiep = nut(cuoi ? "Xong ✓" : "Tiếp ›", "chinh", function () {
        if (cuoi) { dong("Đã xem"); return; }
        i += 1;
        luu("Đang xem", i);
        ve();
      });
      tiep.style.marginLeft = "auto";
      hang.appendChild(tiep);
      the.appendChild(hang);
      document.body.appendChild(the);
      datViTri();
      // Cuộn mượt xong thì vị trí đổi: đặt lại một nhịp sau.
      global.setTimeout(datViTri, 260);
    }

    function dong(trangThai) {
      go();
      global.removeEventListener("resize", datViTri);
      global.removeEventListener("scroll", datViTri, true);
      st.tour = null;
      if (trangThai === "Đã xem") luu("Đã xem", cacThe.length);
      else if (trangThai) luu(trangThai, i);
      if (trangThai) global.setTimeout(veCacThe, 300);
    }

    st.tour = { dong: dong };
    global.addEventListener("resize", datViTri);
    global.addEventListener("scroll", datViTri, true);
    luu("Đang xem", i);
    ve();
    return true;
  }

  // ---------- 2a. thẻ mục tiêu ----------
  function changHienTai(du) {
    var ds = du.chang || [];
    return ds.filter(function (c) { return c.hien_tai; })[0]
      || ds.filter(function (c) { return !c.xong; })[0]
      || ds[ds.length - 1] || null;
  }

  function soBuocCon() {
    var du = st.du;
    if (!du || !du.kich_ban) return 0;
    var c = changHienTai(du);
    if (!c) return 0;
    return (c.buoc || []).filter(function (b) { return !b.xong; }).length;
  }

  function demChu(b) {
    if (b.xong) return "";
    if (b.can_ngay > 1) return " (" + Math.min(b.so_ngay, b.can_ngay) + "/" + b.can_ngay + " ngày)";
    if (b.can_lan > 1) return " (" + Math.min(b.so_lan, b.can_lan) + "/" + b.can_lan + ")";
    return "";
  }

  function laGopY(b) { return b.loai === "Góp ý trên màn"; }

  function moGopY() {
    dongKhay();
    try {
      if (global.FeedbackWidget && global.FeedbackWidget.openComposer) {
        global.FeedbackWidget.openComposer({});
        return;
      }
    } catch (_e) {}
    try { global.__fbw_instance__.toggle(true); } catch (_e) {}
  }

  function moMucTieu() {
    var du = st.du;
    if (!du || !du.kich_ban) return false;
    var c = changHienTai(du);
    var k = moKhay("🎯 " + (du.ten || "Mục tiêu") + (c ? " — chặng " + c.ten : ""), du.ly_do || "");
    k.khay.setAttribute("data-kb", "muc-tieu");

    var ds = el("div", "fbw-kb-chang-ds");
    (du.chang || []).forEach(function (x) {
      ds.appendChild(el("span", "fbw-kb-chip" + (x === c ? " fbw-kb-nay" : x.xong ? " fbw-kb-xong" : ""),
        (x.xong && x.loai === "Một lần" ? "✓ " : "") + x.ten));
    });
    k.than.appendChild(ds);

    var hangBuoc = [];
    (c ? c.buoc : []).forEach(function (b) {
      var dang = !b.xong && (b.so_lan > 0 || b.so_ngay > 0);
      var r = el("div", "fbw-kb-buoc" + (laGopY(b) && !b.xong ? " fbw-kb-bam" : ""));
      r.setAttribute("data-xong", b.xong ? "1" : "0");
      r.appendChild(el("span", "fbw-kb-dau-buoc", b.xong ? "✓" : dang ? "◐" : "○"));
      r.firstChild.style.color = b.xong ? "#047857" : dang ? "#d97706" : "#9ca3af";
      r.appendChild(el("span", "fbw-kb-mota", (b.mo_ta || "") + demChu(b)));
      r.appendChild(el("span", "fbw-kb-diem", "+" + (b.diem || 0)));
      if (laGopY(b) && !b.xong) {
        r.title = "Bấm để gửi một góp ý ngay trên màn này";
        r.onclick = moGopY;
      }
      k.than.appendChild(r);
      hangBuoc.push({ b: b, r: r });
    });

    var cuoi = [];
    if (c) {
      if (c.loai === "Duy trì") {
        if (c.hom_nay_nghi) cuoi.push("Hôm nay nghỉ — không tính kỳ");
        else if (c.dat_ky_nay) cuoi.push("Kỳ này đã đạt ✓");
        else if (c.han_hom_nay) cuoi.push("Hạn hôm nay " + c.han_hom_nay);
        if (c.chuoi > 0) cuoi.push("Chuỗi " + c.chuoi);
        else if (c.chuoi_dai_nhat > 0) cuoi.push("Bắt đầu lại chuỗi (dài nhất " + c.chuoi_dai_nhat + ")");
        cuoi.push("Mỗi kỳ đạt: +" + (c.diem || 0));
      } else {
        cuoi.push(c.xong ? "Đã xong chặng ✓" : "Xong chặng: +" + (c.diem || 0));
      }
    }
    var nv = du.nhiem_vu;
    if (nv && nv.con_ngay !== null && nv.con_ngay !== undefined && nv.trang_thai !== "Đạt") {
      cuoi.push(nv.con_ngay > 0 ? "Hạn giao: còn " + nv.con_ngay + " ngày" : "Hạn giao: hôm nay");
    }
    if (cuoi.length) {
      var f = el("div", null, cuoi.join(" · "));
      f.style.cssText = "color:#4b5563;font-size:13px;margin-top:8px";
      k.than.appendChild(f);
    }

    var con = hangBuoc.filter(function (x) { return !x.b.xong; });
    if (con.length) {
      k.chan.appendChild(nut("Bước tiếp", "chinh", function () {
        var x = con[0];
        if (laGopY(x.b)) { moGopY(); return; }
        hangBuoc.forEach(function (y) { y.r.classList.remove("fbw-kb-sang"); });
        x.r.classList.add("fbw-kb-sang");
        try { x.r.scrollIntoView({ block: "nearest" }); } catch (_e) {}
      }));
    }
    if ((du.huong_dan && du.huong_dan.cac_the || []).length) {
      k.chan.appendChild(nut("Xem lại hướng dẫn", null, function () { moHuongDan(true); }));
    }
    return true;
  }

  // ---------- 2b. thành tích của tôi ----------
  function hcChu(ds) {
    return (ds || []).map(function (h) { return h.ten + (h.so_lan > 1 ? " ×" + h.so_lan : ""); }).join("  ");
  }

  function moThanhTich() {
    var k = moKhay("🏅 Thành tích của tôi");
    k.khay.setAttribute("data-kb", "thanh-tich");
    k.than.appendChild(el("div", null, "Đang tải…"));
    goi("thanh_tich", {}, function (r) {
      k.than.innerHTML = "";
      if (!r) { k.than.appendChild(el("div", null, "Chưa tải được, thử lại sau.")); return; }
      var cap = el("div", null, (r.ten || "") + " — " + r.cap);
      cap.style.cssText = "font-weight:700;font-size:15px";
      k.than.appendChild(cap);
      var thanh = el("div", "fbw-kb-thanh");
      var o = el("div");
      var pct = r.nguong_ke ? Math.min(100, Math.round(100 * r.tong / r.nguong_ke)) : 100;
      o.style.width = pct + "%";
      thanh.appendChild(o);
      k.than.appendChild(thanh);
      k.than.appendChild(el("div", "fbw-kb-phu",
        r.tong + " điểm" + (r.nguong_ke ? " · còn " + (r.nguong_ke - r.tong) + " điểm tới cấp kế" : " · cấp cao nhất")));
      k.than.lastChild.style.padding = "0 0 8px";
      if ((r.huan_chuong || []).length) {
        var hc = el("div", null, hcChu(r.huan_chuong));
        hc.style.cssText = "margin:4px 0 10px;font-size:14.5px";
        k.than.appendChild(hc);
      }
      if ((r.kich_ban || []).length) {
        var b = el("table", "fbw-kb-bang");
        b.innerHTML = "<thead><tr><th>Màn</th><th>Chặng</th><th>Chuỗi dài nhất</th></tr></thead>";
        var tb = el("tbody");
        r.kich_ban.forEach(function (x) {
          var tr = el("tr");
          tr.appendChild(el("td", null, x.ten));
          tr.appendChild(el("td", null, x.chang_xong + "/" + x.so_chang + (x.chang_hien_tai ? " · đang " + x.chang_hien_tai : "")));
          tr.appendChild(el("td", null, x.chuoi_dai_nhat ? String(x.chuoi_dai_nhat) : "—"));
          tb.appendChild(tr);
        });
        b.appendChild(tb);
        k.than.appendChild(b);
      } else {
        k.than.appendChild(el("div", "fbw-kb-phu", "Chưa có màn nào được giao. Mở một màn có 🎯 để bắt đầu."));
      }
    });
    k.chan.appendChild(nut("🏆 Bảng vàng", null, function () { moBangVang(); }));
    return true;
  }

  // ---------- 2c. bảng vàng ----------
  function moBangVang(ky, congTy) {
    ky = ky || "thang";
    var k = moKhay("🏆 Bảng vàng");
    k.khay.setAttribute("data-kb", "bang-vang");
    var tab = el("div", "fbw-kb-tab");
    [["thang", "Tháng này"], ["tat_ca", "Từ trước tới nay"]].forEach(function (x) {
      var b = nut(x[1], null, function () { moBangVang(x[0], sel ? sel.value : congTy); });
      if (x[0] === ky) b.classList.add("fbw-kb-on");
      tab.appendChild(b);
    });
    var sel = null;
    k.than.appendChild(tab);
    var noi = el("div", null, "Đang tải…");
    k.than.appendChild(noi);
    var args = { ky: ky };
    if (congTy !== undefined && congTy !== null) args.cong_ty = congTy;
    goi("bang_vang", args, function (r) {
      noi.innerHTML = "";
      if (!r) { noi.textContent = "Chưa tải được, thử lại sau."; return; }
      if ((r.cac_cong_ty || []).length > 1 || r.cong_ty_cua_toi) {
        sel = el("select");
        sel.setAttribute("aria-label", "Công ty");
        var tc = el("option", null, "Tất cả công ty");
        tc.value = "__all__";
        sel.appendChild(tc);
        (r.cac_cong_ty || []).forEach(function (c) {
          var o = el("option", null, c);
          o.value = c;
          sel.appendChild(o);
        });
        sel.value = r.cong_ty || "__all__";
        sel.onchange = function () { moBangVang(ky, sel.value); };
        tab.appendChild(sel);
      }
      if (!(r.hang || []).length) {
        noi.appendChild(el("div", "fbw-kb-phu", "Chưa ai có điểm trong kỳ này."));
        noi.lastChild.style.padding = "8px 0";
        return;
      }
      var b = el("table", "fbw-kb-bang");
      b.innerHTML = "<thead><tr><th>#</th><th>Tên</th><th>Cấp</th><th>Điểm</th><th></th></tr></thead>";
      var tb = el("tbody");
      r.hang.forEach(function (h) {
        var tr = el("tr", h.la_toi ? "fbw-kb-toi" : null);
        tr.appendChild(el("td", null, h.hang <= 3 ? ["🥇", "🥈", "🥉"][h.hang - 1] : String(h.hang)));
        tr.appendChild(el("td", null, h.ten));
        tr.appendChild(el("td", null, h.cap));
        tr.appendChild(el("td", null, String(h.diem)));
        // Trên điện thoại chỉ để biểu tượng: tên huân chương dài làm bảng tràn ngang.
        tr.appendChild(el("td", null, (h.huan_chuong || []).map(function (x) {
          return (hep() ? x.ten.split(" ")[0] : x.ten) + (x.so_lan > 1 ? "×" + x.so_lan : "");
        }).join(" ")));
        tb.appendChild(tr);
      });
      b.appendChild(tb);
      noi.appendChild(b);
    });
    return true;
  }

  // ---------- 3. chúc mừng ----------
  function chucMung(cb) {
    if (!cb) return;
    var ds = cb.diem || [], hc = cb.huan_chuong || [];
    if (!ds.length && !hc.length) return;
    var t = theNho("fbw-kb-mung");
    t.setAttribute("data-kb", "chuc-mung");
    var tong = ds.reduce(function (a, d) { return a + (d.diem || 0); }, 0);
    var tieu = el("div", null, "🎉 " + (tong > 0 ? "+" + tong + " điểm" : "Có tin vui"));
    tieu.style.cssText = "font-weight:700;margin-bottom:4px";
    t.appendChild(tieu);
    // Gộp theo lý do: 6 bước xong một lúc thành MỘT dòng "+60 — Bước ×6", không phải 6 dòng.
    var gop = {}, thuTu = [];
    ds.forEach(function (d) {
      var k = d.ly_do || "Điểm";
      if (!gop[k]) { gop[k] = { diem: 0, n: 0 }; thuTu.push(k); }
      gop[k].diem += d.diem || 0;
      gop[k].n += 1;
    });
    thuTu.forEach(function (k) {
      var g = gop[k];
      t.appendChild(el("div", null, (g.diem >= 0 ? "+" : "") + g.diem + " — " + k + (g.n > 1 ? " ×" + g.n : "")));
    });
    hc.forEach(function (h) {
      var d = el("div", null, h.ten);
      d.style.fontWeight = "700";
      t.appendChild(d);
    });
    if (cb.cap_truoc && cb.cap_sau && cb.cap_truoc !== cb.cap_sau) {
      var c = el("div", null, "⬆️ Lên cấp " + cb.cap_sau);
      c.style.cssText = "font-weight:700;color:#047857;margin-top:4px";
      t.appendChild(c);
    }
    var hang = el("div", "fbw-kb-hang");
    hang.appendChild(nut("🏅 Thành tích", null, function () { t.dong(); moThanhTich(); }));
    hang.appendChild(nut("Đóng", null, function () { t.dong(); }));
    t.appendChild(hang);
    // Đã HIỆN là đã báo: thẻ chúc mừng không phải việc cần làm, không chờ người ta bấm.
    goi("da_bao", {});
  }

  // ---------- 4. hỏi cảm nhận ----------
  function hoiCamNhan(du, h) {
    var khoa = "cn:" + du.kich_ban + ":" + h.chang;
    if (daHien(khoa)) return;
    var t = theNho("fbw-kb-mung");
    t.setAttribute("data-kb", "cam-nhan");
    var tieu = el("div", null, "Màn «" + (du.ten || "") + "» dùng thấy sao?");
    tieu.style.fontWeight = "700";
    t.appendChild(tieu);
    t.appendChild(el("div", "fbw-kb-phu", "Vừa xong chặng " + (h.ten_chang || "") + ". Một cú chạm là đủ."));
    t.lastChild.style.padding = "0";
    var o = el("textarea");
    o.placeholder = "Muốn nói thêm (không bắt buộc)";
    t.appendChild(o);
    var hang = el("div", "fbw-kb-hang");
    function gui(y) {
      goi("cam_nhan", { kich_ban: du.kich_ban, chang: h.chang, y: y, chu: o.value || "", screen_id: st.man || "" },
        function () { if (y !== "bo_qua") global.setTimeout(function () { if (global.FeedbackPlaybook) global.FeedbackPlaybook.lamMoi(); }, 600); });
      t.dong();
    }
    hang.appendChild(nut("👍", "chinh", function () { gui("👍"); }));
    hang.appendChild(nut("👎", null, function () { gui("👎"); }));
    var bq = nut("Bỏ qua", null, function () { gui("bo_qua"); });
    bq.style.marginLeft = "auto";
    hang.appendChild(bq);
    t.appendChild(hang);
  }

  // ---------- 5. mẹo tại chỗ ----------
  function chiVao(chiVaoSel) {
    var c = timCho(chiVaoSel);
    if (!c) return false;
    napCss();
    try { c.scrollIntoView({ block: "center" }); } catch (_e) {}
    var v = el("div", "fbw-kb-vien");
    document.body.appendChild(v);
    function dat() {
      var r = c.getBoundingClientRect();
      v.style.left = r.left - 6 + "px"; v.style.top = r.top - 6 + "px";
      v.style.width = r.width + 12 + "px"; v.style.height = r.height + 12 + "px";
    }
    dat();
    global.setTimeout(dat, 260);
    function bo() { if (v.parentNode) v.parentNode.removeChild(v); document.removeEventListener("click", bo, true); }
    global.setTimeout(function () { document.addEventListener("click", bo, true); }, 50);
    global.setTimeout(bo, 4000);
    return true;
  }

  function veMeo(du, m) {
    var khoa = "meo:" + du.kich_ban + ":" + (m.loai || "") + ":" + (m.khoa || m.noi_dung || "");
    if (daHien(khoa)) return;
    var t = theNho();
    t.setAttribute("data-kb", "meo");
    t.setAttribute("data-loai", m.loai || "");
    t.appendChild(el("div", null, "💡 " + (m.noi_dung || "")));
    var hang = el("div", "fbw-kb-hang");
    if (m.hanh_dong === "gop_y") hang.appendChild(nut("Gửi góp ý", "chinh", function () { t.dong(); moGopY(); }));
    else if (m.hanh_dong === "huong_dan") hang.appendChild(nut("Xem tiếp", "chinh", function () { t.dong(); moHuongDan(false); }));
    else if (m.chi_vao) hang.appendChild(nut("Chỉ cho tôi", "chinh", function () {
      if (!chiVao(m.chi_vao)) baoChiVaoMat(du.kich_ban, "meo-" + (m.khoa || ""));
    }));
    hang.appendChild(nut("Đóng", null, function () { t.dong(); }));
    t.appendChild(hang);
  }

  // ---------- nạp dữ liệu từ `cua_toi` ----------
  function veCacThe() {
    var du = st.du;
    if (!du || st.tour) return;
    if (du.kich_ban) {
      (du.meo || []).forEach(function (m) {
        // N7 "Xem tiếp hướng dẫn?" vô nghĩa khi hướng dẫn vừa tự bật hoặc đã xem xong.
        if (m.hanh_dong === "huong_dan" && du.huong_dan && du.huong_dan.trang_thai !== "Đang xem") return;
        veMeo(du, m);
      });
      (du.hoi_cam_nhan || []).forEach(function (h) { hoiCamNhan(du, h); });
    }
  }

  function nap(du, man) {
    st.du = du || null;
    st.man = man || null;
    if (!du) return;
    chucMung(du.chua_bao);
    if (!du.kich_ban) return;
    if (du.huong_dan && du.huong_dan.tu_bat && !st.daTuBat[du.kich_ban]) {
      st.daTuBat[du.kich_ban] = 1;
      // Một nhịp để màn của app vẽ xong — chỉ vào một chỗ chưa có thì thành "chỉ vào mất".
      global.setTimeout(function () {
        if (st.du && st.du.kich_ban === du.kich_ban && !moHuongDan(true)) veCacThe();
      }, 900);
      return;
    }
    veCacThe();
  }

  global.FeedbackPlaybook = {
    nap: nap,
    moMucTieu: moMucTieu,
    moHuongDan: moHuongDan,
    moThanhTich: moThanhTich,
    moBangVang: function () { return moBangVang(); },
    coKichBan: function () { return !!(st.du && st.du.kich_ban); },
    soBuocCon: soBuocCon,
    // Bundle thay hàm này bằng lượt hỏi lại máy chủ (bỏ qua nhịp chờ 30 giây).
    lamMoi: function () {},
    _st: st,
  };
})(window);
