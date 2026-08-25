"""Phân tích sổ chặn → Markdown xếp hạng sẵn, cho người đọc lẫn coding agent.

Dùng:
    bench --site <site> execute feedback_widget.phan_tich.bao_cao --kwargs "{'so_ngay': 7}"

Mọi con số ở đây đều đi kèm MẪU SỐ hoặc SỐ NGƯỜI: "5 lần bị chặn" không nói được gì nếu
không biết 5 trên bao nhiêu lượt, và một lỗi cản 5 người khác hẳn một người vấp 5 lần.
"""

from __future__ import annotations

import json

import frappe
from frappe.utils import add_days, cint, now_datetime


def _rows(sql, tham=None):
    return frappe.db.sql(sql, tham or {}, as_dict=True)


def chu_ky_moi(gio: int = 24) -> list[dict]:
    """Chữ ký XUẤT HIỆN LẦN ĐẦU trong `gio` giờ qua — thứ vừa hỏng, thường do bản mới."""
    return _rows("""
        SELECT signature, MIN(ts) lan_dau, COUNT(*) so_lan, COUNT(DISTINCT user) so_nguoi,
               MAX(message) thong_diep, MAX(screen_name) man, MAX(endpoint) endpoint
          FROM `tabFeedback Event`
         WHERE kind IN ('chan','loi') AND IFNULL(signature,'') <> ''
         GROUP BY signature
        HAVING MIN(ts) > %(moc)s
         ORDER BY so_nguoi DESC, so_lan DESC LIMIT 20
    """, {"moc": add_days(now_datetime(), -max(1, cint(gio)) / 24.0)})


def dang_ket(phut: int = 15, nguong: int = 3) -> list[dict]:
    """Ai ĐANG kẹt: cùng người + cùng chữ ký ≥ `nguong` lần trong `phut` phút gần đây."""
    return _rows("""
        SELECT user, signature, COUNT(*) so_lan, MAX(screen_name) man, MAX(message) thong_diep,
               MIN(ts) tu, MAX(ts) den
          FROM `tabFeedback Event`
         WHERE kind IN ('chan','loi') AND ts > %(moc)s AND IFNULL(signature,'') <> ''
         GROUP BY user, signature HAVING so_lan >= %(nguong)s
         ORDER BY so_lan DESC LIMIT 20
    """, {"moc": add_days(now_datetime(), -max(1, cint(phut)) / 1440.0), "nguong": cint(nguong)})


def bo_cuoc(so_ngay: int = 7) -> list[dict]:
    """Chuỗi bị chặn mà SAU ĐÓ không có lần thành công nào trong 30 phút.

    Đây là chỗ công việc thật sự không hoàn thành — khác hẳn "bị chặn rồi làm lại được".
    """
    tu = add_days(now_datetime(), -cint(so_ngay))
    chan = _rows("""SELECT name, user, ts, signature, screen_name, message
                      FROM `tabFeedback Event`
                     WHERE kind IN ('chan','loi') AND ts > %(tu)s
                     ORDER BY ts""", {"tu": tu})
    ra = []
    for c in chan:
        co = frappe.db.sql("""SELECT 1 FROM `tabFeedback Event`
                               WHERE user=%s AND kind='dung' AND outcome='ok'
                                 AND ts > %s AND ts < DATE_ADD(%s, INTERVAL 30 MINUTE) LIMIT 1""",
                           (c.user, c.ts, c.ts))
        if not co:
            ra.append(c)
    return ra[:20]


def khong_ai_dung(so_ngay: int = 30) -> dict:
    tu = add_days(now_datetime(), -cint(so_ngay))
    dung_man = {r[0] for r in frappe.db.sql(
        "SELECT DISTINCT screen_id FROM `tabFeedback Event` WHERE ts > %s", tu)}
    dung_nut = {r[0] for r in frappe.db.sql(
        "SELECT DISTINCT action_id FROM `tabFeedback Event` WHERE ts > %s AND IFNULL(action_id,'')<>''", tu)}
    man = _rows("SELECT item_id, item_name, section_hint FROM `tabFeedback Manifest Item` "
                "WHERE kind='screen' AND con_dung=1 ORDER BY item_name")
    nut = _rows("SELECT item_id, item_name, screen_id FROM `tabFeedback Manifest Item` "
                "WHERE kind='action' AND con_dung=1 ORDER BY screen_id, item_name")
    return {
        "man_khong_ai_vao": [m for m in man if m["item_id"] not in dung_man],
        "nut_khong_ai_bam": [n for n in nut if n["item_id"] not in dung_nut],
        "tong_man": len(man), "tong_nut": len(nut),
    }


def hoi_quy() -> list[dict]:
    """Chữ ký tái xuất SAU khi vé của nó đã đóng — bản vá không tới nơi, hoặc sai nguyên nhân."""
    return _rows("""
        SELECT c.name ve, c.signature, c.status, c.status_changed_at, COUNT(e.name) so_lan_sau,
               MAX(e.ts) gan_nhat, MAX(e.message) thong_diep
          FROM `tabFeedback Comment` c
          JOIN `tabFeedback Event` e ON e.signature = c.signature
         WHERE c.status IN ('Resolved','Wontfix') AND IFNULL(c.signature,'') <> ''
           AND e.ts > IFNULL(c.status_changed_at, c.modified)
         GROUP BY c.name ORDER BY so_lan_sau DESC LIMIT 20
    """)


def _bang(tieu_de, rows, cot):
    if not rows:
        return [f"### {tieu_de}", "", "_không có_", ""]
    ra = [f"### {tieu_de}", "", "| " + " | ".join(n for n, _ in cot) + " |",
          "|" + "---|" * len(cot)]
    for r in rows:
        o = []
        for _, k in cot:
            v = r.get(k) if isinstance(r, dict) else getattr(r, k, "")
            o.append(str(v if v is not None else "").replace("|", "/").replace("\n", " ")[:90])
        ra.append("| " + " | ".join(o) + " |")
    ra.append("")
    return ra


def bao_cao(so_ngay: int = 7, in_ra: int = 1) -> str:
    """Báo cáo Markdown đầy đủ. `in_ra=0` để lấy chuỗi mà không in."""
    so_ngay = cint(so_ngay) or 7
    tu = add_days(now_datetime(), -so_ngay)
    tong = frappe.db.sql("""SELECT SUM(kind='dung') luot, SUM(kind='chan') chan, SUM(kind='loi') loi,
                                   COUNT(DISTINCT user) nguoi
                              FROM `tabFeedback Event` WHERE ts > %s""", tu, as_dict=True)[0]
    mau_so = (tong.luot or 0) + (tong.chan or 0) + (tong.loi or 0)
    ti_le = round(100.0 * ((tong.chan or 0) + (tong.loi or 0)) / mau_so, 1) if mau_so else 0

    d = [f"# Sổ chặn — {so_ngay} ngày qua", "",
         f"**{tong.chan or 0} lần bị chặn · {tong.loi or 0} lỗi · {tong.luot or 0} thao tác "
         f"thành công · {tong.nguoi or 0} người** — tỉ lệ chặn/lỗi **{ti_le}%**", ""]

    d += _bang("Chữ ký MỚI trong 24h (sửa trước)", chu_ky_moi(24), [
        ("Người", "so_nguoi"), ("Lần", "so_lan"), ("Màn", "man"),
        ("Thông điệp", "thong_diep"), ("Endpoint", "endpoint"), ("Lần đầu", "lan_dau")])

    top = _rows("""SELECT signature, COUNT(*) so_lan, COUNT(DISTINCT user) so_nguoi,
                          MAX(marker) marker, MAX(screen_name) man, MAX(message) thong_diep,
                          GROUP_CONCAT(DISTINCT user SEPARATOR ', ') ai
                     FROM `tabFeedback Event`
                    WHERE kind IN ('chan','loi') AND ts > %(tu)s AND IFNULL(signature,'') <> ''
                    GROUP BY signature ORDER BY so_nguoi DESC, so_lan DESC LIMIT 15""", {"tu": tu})
    d += _bang("Chỗ tắc — xếp theo SỐ NGƯỜI", top, [
        ("Người", "so_nguoi"), ("Lần", "so_lan"), ("Dấu hiệu", "marker"), ("Màn", "man"),
        ("Thông điệp", "thong_diep"), ("Ai", "ai")])

    d += _bang("Đang kẹt ngay lúc này (lặp ≥3 trong 15 phút)", dang_ket(), [
        ("Người", "user"), ("Lần", "so_lan"), ("Màn", "man"), ("Thông điệp", "thong_diep")])

    d += _bang("Bỏ cuộc — bị chặn rồi KHÔNG làm được gì trong 30 phút sau", bo_cuoc(so_ngay), [
        ("Người", "user"), ("Lúc", "ts"), ("Màn", "screen_name"), ("Thông điệp", "message")])

    kad = khong_ai_dung(max(so_ngay, 30))
    d += [f"### Không ai dùng (trong {max(so_ngay, 30)} ngày)", "",
          f"- Màn: **{len(kad['man_khong_ai_vao'])}/{kad['tong_man']}** chưa ai vào",
          f"- Nút: **{len(kad['nut_khong_ai_bam'])}/{kad['tong_nut']}** chưa ai bấm "
          f"(chỉ tính nút đã được kiểm kê trên màn có người mở)", ""]
    d += _bang("Màn chưa ai vào", kad["man_khong_ai_vao"][:20],
               [("Mã", "item_id"), ("Tên", "item_name"), ("Nhóm", "section_hint")])
    d += _bang("Nút chưa ai bấm", kad["nut_khong_ai_bam"][:25],
               [("Nút", "item_name"), ("Ở màn", "screen_id")])

    d += _bang("Hồi quy — vé đã đóng mà lỗi quay lại", hoi_quy(), [
        ("Vé", "ve"), ("Lần sau khi đóng", "so_lan_sau"), ("Gần nhất", "gan_nhat"),
        ("Thông điệp", "thong_diep")])

    ra = "\n".join(d)
    if cint(in_ra):
        # `bench execute` IN LUÔN giá trị trả về, nên trả chuỗi ở đây là in báo cáo hai
        # lần (lần thứ hai dạng escape \u — không ai đọc nổi). In thì thôi trả.
        print(ra)
        return None
    return ra
