/* Thẻ THÔNG BÁO TÍNH NĂNG — phần VẼ của cơ chế `Feedback Notice`.
 *
 * Tệp RIÊNG, cố ý: menu/nút của widget do phiên khác giữ, hai người cùng sửa một tệp là
 * chắc chắn xung đột (đã xảy ra hôm 26/08). Ở đây chỉ khai `window.FeedbackNotices.show`,
 * đúng cái tên mà lối vào "🔔 Thông báo tính năng mới" chờ.
 *
 * Ba luật của cơ chế, cài đặt ngay trong hàm này:
 *  1. CHỈ đánh dấu ĐÃ XEM khi người dùng BẤM (Xem thử / đóng) — thẻ tự ẩn sau vài giây
 *     KHÔNG tính là đã xem, vì thông báo biến mất chỉ vì người ta đang bận thì bằng không
 *     có. Lần mở sau nó vẫn còn.
 *  2. `da_bam = 1` chỉ khi bấm "Xem thử" — chính con số đó trả lời "gửi có trúng không".
 *  3. Có ĐƯỜNG DẪN thì phải bấm được; không có thì không vẽ nút, đừng mời vào ngõ cụt.
 */
(function (global) {
  var TU_AN_MS = 8000;
  var TOI_DA = 3;

  function css(el, o) { for (var k in o) el.style[k] = o[k]; return el; }

  function danhDau(ten, daBam) {
    try {
      global.frappe.call({
        method: "feedback_widget.api.thong_bao.da_xem",
        args: { thong_bao: ten, da_bam: daBam ? 1 : 0 },
        error: function () {},
      });
    } catch (_e) {}
  }

  function khungChua() {
    var id = "fbw-thong-bao-lop";
    var el = document.getElementById(id);
    if (el) return el;
    el = document.createElement("div");
    el.id = id;
    css(el, {
      position: "fixed", right: "18px", bottom: "92px", zIndex: "99998",
      display: "flex", flexDirection: "column", gap: "10px",
      maxWidth: "min(360px, calc(100vw - 36px))",
    });
    document.body.appendChild(el);
    return el;
  }

  function veThe(tb, khung) {
    var the = document.createElement("div");
    css(the, {
      background: "#fff", border: "1px solid #d1d5db", borderLeft: "4px solid #047857",
      borderRadius: "10px", boxShadow: "0 6px 20px rgba(0,0,0,.14)", padding: "12px 14px",
      font: "14px/1.45 system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif", color: "#111827",
    });

    var tieu = document.createElement("div");
    tieu.textContent = "✨ " + (tb.tieu_de || "Có cập nhật mới");
    css(tieu, { fontWeight: "700", marginBottom: "4px" });
    the.appendChild(tieu);

    if (tb.noi_dung) {
      var nd = document.createElement("div");
      nd.textContent = tb.noi_dung;
      css(nd, { color: "#374151", marginBottom: "6px" });
      the.appendChild(nd);
    }

    // Lời cảm ơn đứng RIÊNG một dòng và không bị cắt: nó là lý do người ta gõ vé lần sau.
    if (tb.cam_on_ai) {
      var co = document.createElement("div");
      co.textContent = "🙏 Cảm ơn " + tb.cam_on_ai + " đã báo"
        + (tb.nguon_ve ? " (" + tb.nguon_ve + ")" : "");
      css(co, { color: "#047857", fontWeight: "600", marginBottom: "8px" });
      the.appendChild(co);
    }

    var hang = document.createElement("div");
    css(hang, { display: "flex", gap: "8px", alignItems: "center" });

    if (tb.duong_dan) {
      var xem = document.createElement("button");
      xem.type = "button";
      xem.textContent = "Xem thử →";
      css(xem, {
        background: "#047857", color: "#fff", border: "none", borderRadius: "7px",
        padding: "7px 12px", fontWeight: "700", cursor: "pointer", fontSize: "13.5px",
      });
      xem.onclick = function () {
        danhDau(tb.name, true);
        dong();
        var d = String(tb.duong_dan);
        if (/^https?:/i.test(d)) { global.location.href = d; return; }
        // Đường dẫn trong app là hash route (`#/viec-cua-toi`): gán hash rồi bắn
        // `hashchange` cho SPA nghe — gán không thôi thì màn đứng im khi đã ở cùng trang.
        global.location.hash = d.charAt(0) === "#" ? d.slice(1) : d;
        try { global.dispatchEvent(new HashChangeEvent("hashchange")); } catch (_e) {}
      };
      hang.appendChild(xem);
    }

    var dongNut = document.createElement("button");
    dongNut.type = "button";
    dongNut.textContent = "Đóng";
    css(dongNut, {
      background: "transparent", color: "#6b7280", border: "1px solid #d1d5db",
      borderRadius: "7px", padding: "7px 12px", cursor: "pointer", fontSize: "13.5px",
    });
    dongNut.onclick = function () { danhDau(tb.name, false); dong(); };
    hang.appendChild(dongNut);
    the.appendChild(hang);

    var hen = null;
    function dong() {
      if (hen) { clearTimeout(hen); hen = null; }
      if (the.parentNode) the.parentNode.removeChild(the);
      if (!khung.childNodes.length && khung.parentNode) khung.parentNode.removeChild(khung);
    }
    // Tự ẩn: KHÔNG gọi `da_xem` — xem mục 1 ở đầu tệp.
    hen = setTimeout(function () { if (the.parentNode) the.parentNode.removeChild(the); }, TU_AN_MS);
    the.onmouseenter = function () { if (hen) { clearTimeout(hen); hen = null; } };

    khung.appendChild(the);
  }

  global.FeedbackNotices = {
    show: function (ds) {
      var list = (ds || []).slice(0, TOI_DA);
      if (!list.length) return 0;
      var khung = khungChua();
      list.forEach(function (tb) { veThe(tb, khung); });
      return list.length;
    },
  };
})(window);
