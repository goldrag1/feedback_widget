"""Tác vụ nền: cầu Error Log → hộp thư · dọn sổ cũ · tổng kết hằng ngày."""

from __future__ import annotations

import json
import re

import frappe
from frappe.utils import add_days, cint, now_datetime, get_datetime

from feedback_widget import notifier
from feedback_widget.cai_dat import cai_dat
from feedback_widget.chu_ky import chu_ky as _tinh_chu_ky
from feedback_widget.chu_ky import chuan_hoa as _chuan_hoa
from feedback_widget.chu_ky import dau_hieu as _tinh_dau_hieu

MOC = "feedback_widget:moc_error_log"        # mốc đã đọc tới đâu (frappe cache/singles)


def _du_an() -> str:
    return (cai_dat().get("project_name") or frappe.local.site or "default")[:80]


def _cau_cuoi(traceback: str) -> str:
    """Câu CUỐI của traceback — thứ nói lỗi là gì; phần trên chỉ là đường đi."""
    dong = [d.strip() for d in (traceback or "").splitlines() if d.strip()]
    for d in reversed(dong):
        if ":" in d and not d.startswith("File "):
            return d[:1000]
    return (dong[-1] if dong else "")[:1000]


# Một dòng Error Log chỉ đáng thành VÉ khi nó là NGOẠI LỆ. Nhiều app dùng
# `frappe.log_error` như nhật ký thông tin ("Repack · [OUTPUT:…] Nhập kho kết quả"),
# và bắc cầu tất cả thì hộp thư ngập thứ không ai phải xử lý — đúng cách để người ta
# ngừng đọc hộp thư. Đo trên site dev: 200 dòng Error Log chỉ có một phần là ngoại lệ.
_NGOAI_LE = re.compile(r"^[A-Za-z_][\w.]*(Error|Exception|Warning)\b")


def _dang_ngoai_le(cau: str) -> bool:
    return bool(_NGOAI_LE.match(cau or "")) or bool(_tinh_dau_hieu(cau or ""))


def _moc_da_doc() -> str:
    v = frappe.db.get_global(MOC)
    if v:
        return v
    # LẦN ĐẦU: đọc từ BÂY GIỜ, không đọc ngược lịch sử. Bật một tính năng ghi sổ không
    # được phép đổ hàng trăm vé cũ vào hộp thư của người đang trực. Muốn khai thác lịch
    # sử thì gọi `khai_thac_lich_su()` có chủ đích, với khoảng ngày tự chọn.
    # PHẢI có phần triệu-giây: cắt tới GIÂY thì mọi lỗi xảy ra trong chính giây đặt mốc
    # đều "không lớn hơn mốc" và bị bỏ qua VĨNH VIỄN — mất dòng mà không ai biết, đúng
    # lớp lỗi mà sổ này sinh ra để chống (bộ test bắt được ngay lượt đầu).
    moc = now_datetime().strftime("%Y-%m-%d %H:%M:%S.%f")
    frappe.db.set_global(MOC, moc)
    return moc


# Ngoại lệ do `frappe.throw` sinh ra là LUẬT NGHIỆP VỤ chạy đúng (chan); mọi lớp lỗi khác
# là phần mềm hỏng (loi). Trộn hai thứ là cách chắc chắn xếp sai thứ tự ưu tiên, nên sổ phải
# phân biệt ngay từ lúc ghi.
_LOI_KHUNG = ("ValidationError", "PermissionError", "MandatoryError", "DuplicateEntryError",
              "LinkValidationError", "LinkExistsError", "InvalidStatusError", "DoesNotExistError")


def _lop_loi(cau: str) -> str:
    """Tên lớp ngoại lệ, đã bỏ tiền tố module: `builtins.TypeError` → `TypeError`.

    Trình duyệt gửi tên TRẦN (`TypeError: …`) còn Error Log ghi cả đường module, nên
    không bỏ tiền tố thì cùng một sự cố ra hai chữ ký và bộ chống trùng bên dưới mù.
    """
    dau = (cau or "").split(":", 1)[0].strip()
    return dau.rsplit(".", 1)[-1] if _NGOAI_LE.match(dau) or "." in dau else ""


def _loai_su_kien(cau: str) -> str:
    lop = _lop_loi(cau)
    if lop in _LOI_KHUNG or (cau or "").startswith("frappe.exceptions."):
        return "chan"
    # KHÔNG có lớp ngoại lệ nào ⇒ đây là dòng NHẬT KÝ mang dấu hiệu máy-đọc (app dùng
    # `log_error` làm sổ tay), không phải phần mềm hỏng. Gọi nó là `loi` thì bảng xếp hạng
    # đẩy một dòng ghi chú lên trên những ca thật.
    return "loi" if lop else "chan"


def _ghi_su_kien_nen(r, cau: str, du_an: str) -> int:
    """Cầu Error Log cũng phải ghi vào SỔ THÔ, không chỉ đẻ vé.

    VÌ SAO: widget chỉ ghi sự kiện ở tầng fetch của trình duyệt, mà việc NỀN trả HTTP 200
    rồi mới báo hỏng qua thanh tiến độ. Đo prod 25-26/08: 15 lần xưởng bị chặn ở việc nền
    (lệnh chưa duyệt, [THIEUCAN], [XINDUYET], thiếu kho vai) — 0 dòng `Feedback Event`, nên
    mọi bảng xếp hạng (chỗ tắc · kẹt lặp · bỏ cuộc · % chặn) đọc bằng 0 trong khi xưởng đứng
    hình. Vé thì có, nhưng vé không đếm được nhịp và không dựng được chuỗi thao tác.

    KHÔNG gọi `su_kien.ghi_lo`: hàm đó là endpoint HTTP, đóng dấu `frappe.session.user` +
    `now_datetime()` — ở đây danh tính là CHỦ dòng Error Log và thời điểm là lúc nó xảy ra.
    Phần dùng chung thật sự (chữ ký, dấu hiệu) vẫn chỉ có một định nghĩa: `chu_ky.py`.
    """
    loai = _loai_su_kien(cau)
    ck = _tinh_chu_ky(cau, (r.method or "")[:200], loai)
    # Lỗi 500 của đường ĐỒNG BỘ vào Error Log *và* được widget báo từ trình duyệt. Ghi cả
    # hai là một sự cố hoá hai dòng, và "bao nhiêu lần" phồng theo hướng nguy hiểm nhất.
    # So bằng chữ ký thôi thì KHÔNG bắt được: hai bên khai `endpoint` khác nhau (trình duyệt
    # biết tên endpoint, Error Log chỉ có tiêu đề dòng log) và câu của Error Log mang thêm
    # tiền tố module. Nên so thêm bằng CÂU đã chuẩn hoá, khớp một đầu là đủ.
    # (a) CHÍNH dòng log này đã vào sổ rồi (chạy lại cầu, nạp bù lịch sử) — khoá theo tên
    # dòng log, KHÔNG theo chữ ký: hai lượt bấm cách nhau 38 giây có cùng chữ ký và đó là
    # tín hiệu "kẹt lặp" (người ta đang đứng đó thử lại), nuốt nó là xoá đúng thứ cần đo.
    if frappe.db.sql("""SELECT name FROM `tabFeedback Event`
         WHERE screen_id='viec-nen' AND context LIKE %s LIMIT 1""",
         (f'%"error_log": "{r.name}"%',)):
        return 0
    # (b) Cùng sự cố mà TRÌNH DUYỆT đã báo (500 của đường đồng bộ vào cả hai nơi). Chữ ký
    # không khớp được: hai bên khai `endpoint` khác nhau và câu của Error Log mang thêm tiền
    # tố module — nên so bằng CÂU đã chuẩn hoá, khớp một đầu là đủ. Chỉ soi dòng KHÔNG do cầu
    # ghi, để cầu không tự bịt miệng mình.
    cua_toi = _chuan_hoa(cau)
    cu = frappe.db.sql("""SELECT signature, message FROM `tabFeedback Event`
         WHERE kind IN ('chan','loi') AND IFNULL(screen_id,'') <> 'viec-nen'
           AND ts BETWEEN %s - INTERVAL 120 SECOND AND %s + INTERVAL 120 SECOND""",
         (r.creation, r.creation))
    for sig_cu, msg_cu in cu:
        if sig_cu == ck:
            return 0
        khac = _chuan_hoa(msg_cu or "")
        if khac and (khac.endswith(cua_toi) or cua_toi.endswith(khac)):
            return 0
    nguoi = r.owner or "Administrator"
    vai = ", ".join(sorted(x for x in (frappe.get_roles(nguoi) or []) if x not in ("All", "Guest")))[:500]
    frappe.get_doc({
        "doctype": "Feedback Event",
        "project": du_an,
        "kind": loai,
        "ts": r.creation,
        "user": nguoi,
        "user_roles": vai,
        "screen_id": "viec-nen",
        "screen_name": f"Việc nền · {(r.method or '')[:60]}",
        "endpoint": (r.method or "")[:200],
        "outcome": loai,
        "signature": ck,
        "marker": _tinh_dau_hieu(cau) or None,
        "message": cau[:1000],
        "context": json.dumps({"app": {"nguon": "error_log", "error_log": r.name}},
                              ensure_ascii=False),
    }).insert(ignore_permissions=True)
    return 1


def bac_cau_error_log():
    """Lỗi việc NỀN cũng phải vào cùng hộp thư.

    Vì sao: đường nền không có trình duyệt nào để tự báo, nên nó là điểm mù còn lại sau
    khi widget tự gửi. Đo prod 25/08: 59 lần bị chặn trong 9 ngày nằm im trong Error Log,
    không ai từng đọc — trong đó có 10 lần "kho không đủ nguyên liệu" và 9 lần "lệnh chưa
    phê duyệt", tức xưởng đứng hình mà bên làm phần mềm không biết.

    Mốc đọc lưu bằng `db.set_global`: chạy lại không nhân đôi, và nếu job chết giữa chừng
    thì lần sau đọc lại từ mốc CŨ (thà lặp một vài dòng — `collect` tự gộp theo chữ ký —
    còn hơn nhảy cóc mất dòng).
    """
    ct = cai_dat()
    if not cint(ct.get("bridge_error_log")):
        return {"tat": 1}

    moc = _moc_da_doc()
    rows = frappe.db.sql("""
        SELECT name, creation, method, error FROM `tabError Log`
         WHERE creation > %s ORDER BY creation ASC LIMIT 200
    """, moc, as_dict=True)
    if not rows:
        return {"doc": 0, "ve": 0}

    from feedback_widget.api.feedback import collect

    ve = dong_so = 0
    du_an = _du_an()
    for r in rows:
        cau = _cau_cuoi(r.error)
        if not cau or not _dang_ngoai_le(cau):
            continue
        # "Session Stopped" là tiếng ồn của chính Frappe, không phải việc của ai.
        if "Session Stopped" in (r.method or "") or "Session Stopped" in cau:
            continue
        frappe.set_user("Administrator")
        try:
            collect(**{
                "project": _du_an(),
                "screen_id": "viec-nen",
                "screen_name": f"Việc nền · {(r.method or '')[:80]}",
                "message": cau,
                "source": "auto",
                "submitter": "(máy chủ)",
                "tags": {"type": "bug", "severity": "blocker"},
                # `endpoint` PHẢI có: `collect` tính chữ ký từ (thông điệp, endpoint), nên
                # thiếu nó thì cầu gom một kiểu còn hộp thư gom một kiểu — một sự cố ra
                # hai vé và con số "bao nhiêu lần" sai. Một luật, một khoá.
                "context": {"app": {"nguon": "error_log", "error_log": r.name,
                                    "endpoint": (r.method or "")[:200],
                                    "method": (r.method or "")[:200],
                                    "khi": str(r.creation)}},
            })
            ve += 1
            dong_so += _ghi_su_kien_nen(r, cau, du_an)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "feedback_widget bac_cau_error_log")

    frappe.db.set_global(MOC, str(rows[-1].creation))
    frappe.db.commit()
    return {"doc": len(rows), "ve": ve, "su_kien": dong_so}


def don_so_cu():
    """Xoá sổ thô quá hạn. Vé (Feedback Comment) KHÔNG bị đụng — nó là việc của người."""
    ngay = cint(cai_dat().get("retention_days")) or 90
    cat = add_days(now_datetime(), -ngay)
    n = frappe.db.count("Feedback Event", {"ts": ["<", cat]})
    if n:
        frappe.db.delete("Feedback Event", {"ts": ["<", cat]})
        frappe.db.commit()
    return {"xoa": n, "truoc_ngay": str(cat)}


def tong_ket_ngay():
    """Tổng kết 5 chỗ tắc nhiều nhất trong ngày, đẩy Telegram MỘT tin.

    Tin theo từng sự kiện chỉ hợp với lỗi LẦN ĐẦU; phần còn lại gộp vào đây, nếu không
    người nhận sẽ tắt thông báo và mất cả hai.
    """
    ct = cai_dat()
    gio = cint(ct.get("digest_hour"))
    if gio < 0:
        return {"tat": 1}
    if now_datetime().hour != gio:
        return {"bo_qua": "chưa tới giờ"}

    tu = add_days(now_datetime(), -1)
    rows = frappe.db.sql("""
        SELECT signature, MAX(message) msg, COUNT(*) n,
               COUNT(DISTINCT user) so_nguoi, MAX(screen_name) man
          FROM `tabFeedback Event`
         WHERE ts > %s AND kind IN ('chan','loi') AND IFNULL(signature,'') <> ''
         GROUP BY signature ORDER BY n DESC LIMIT 5
    """, tu, as_dict=True)
    tong = frappe.db.count("Feedback Event", {"ts": [">", tu], "kind": ["in", ("chan", "loi")]})
    if not rows:
        return {"khong_co": 1}

    # `send_message` mặc định parse_mode=HTML, mà câu lỗi của Frappe CÓ thẻ HTML thật
    # (`<strong>`, `<a href>`): gửi thô thì Telegram từ chối cả tin, và tổng kết im lặng
    # biến mất đúng như thứ nó sinh ra để chống.
    import html as _html

    dong = [f"📊 Tổng kết 24h — {tong} lần bị chặn/lỗi", ""]
    for i, r in enumerate(rows, 1):
        dong.append(f"{i}. {r.n} lần · {r.so_nguoi} người · {_html.escape((r.man or '')[:40])}")
        dong.append(f"   {_html.escape((r.msg or '')[:160])}")
    try:
        if notifier.is_configured():
            notifier.send_message("\n".join(dong))
    except Exception:
        frappe.log_error(frappe.get_traceback(), "feedback_widget tong_ket_ngay")
    return {"tong": tong, "nhom": len(rows)}


@frappe.whitelist()
def khai_thac_lich_su(so_ngay: int = 30, that_su: int = 0):
    """Đọc NGƯỢC Error Log để dựng bức tranh chỗ tắc đã qua — chạy có chủ đích.

    Mặc định CHẠY THỬ (`that_su=0`): chỉ đếm và in ra sẽ sinh bao nhiêu vé, gom theo
    chữ ký. Một trình khai thác lịch sử mà mặc định GHI là cách tạo ra 200 vé trong hộp
    thư của người khác trước khi họ kịp hiểu chuyện gì.
    """
    frappe.only_for(("System Manager", "Administrator"))
    tu = add_days(now_datetime(), -cint(so_ngay))
    rows = frappe.db.sql("""SELECT name, creation, method, error FROM `tabError Log`
                             WHERE creation > %s ORDER BY creation ASC""", tu, as_dict=True)
    nhom = {}
    for r in rows:
        cau = _cau_cuoi(r.error)
        if not cau or not _dang_ngoai_le(cau):
            continue
        if "Session Stopped" in (r.method or "") or "Session Stopped" in cau:
            continue
        ck = _tinh_chu_ky(cau, r.method or "", "chan")
        g = nhom.setdefault(ck, {"so_lan": 0, "cau": cau, "method": r.method,
                                 "dau": str(r.creation), "cuoi": str(r.creation)})
        g["so_lan"] += 1
        g["cuoi"] = str(r.creation)

    ket = {"doc": len(rows), "nhom": len(nhom), "chay_thu": not cint(that_su),
           "top": sorted(nhom.values(), key=lambda x: -x["so_lan"])[:10]}
    if not cint(that_su):
        return ket

    from feedback_widget.api.feedback import collect

    ve = 0
    for ck, g in nhom.items():
        try:
            kq = collect(**{
                "project": _du_an(), "screen_id": "viec-nen",
                "screen_name": f"Việc nền · {(g['method'] or '')[:80]}",
                "message": g["cau"], "source": "auto", "submitter": "(khai thác lịch sử)",
                "tags": {"type": "bug", "severity": "blocker"},
                "context": {"app": {"nguon": "error_log_lich_su", "so_lan": g["so_lan"],
                                    "endpoint": (g["method"] or "")[:200],
                                    "tu": g["dau"], "den": g["cuoi"]}},
            })
            # Dán ĐÚNG số lần lịch sử lên vé. `collect` đếm theo lượt nạp này (1), nên để
            # nguyên thì vé nói "1 lần" cho một sự cố đã xảy ra 18 lần — con số sai theo
            # hướng làm người xử lý hạ ưu tiên đúng thứ đáng sửa nhất.
            if kq and kq.get("name"):
                frappe.db.set_value("Feedback Comment", kq["name"], {
                    "occurrences": g["so_lan"], "last_seen": g["cuoi"]}, update_modified=False)
            ve += 1
        except Exception:
            frappe.log_error(frappe.get_traceback(), "feedback_widget khai_thac_lich_su")
    frappe.db.commit()
    ket["ve"] = ve
    return ket
