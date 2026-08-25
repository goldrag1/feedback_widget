"""Chỗ tắc — mỗi dòng là MỘT LOẠI sự cố, không phải một lần xảy ra.

Xếp theo SỐ NGƯỜI dính trước, rồi mới tới số lần: một lỗi cản 5 người mỗi người 1 lần
đáng sửa hơn một lỗi mà một người vấp 40 lần (người kia có thể đang thử nghiệm).
Cột "lần đầu / gần nhất" để phân biệt việc đang chảy máu với việc đã tự hết.
"""

import frappe
from frappe.utils import add_days, now_datetime


def execute(filters=None):
    filters = frappe._dict(filters or {})
    ngay = int(filters.get("so_ngay") or 7)
    tu = add_days(now_datetime(), -ngay)
    dieu_kien = ["e.ts > %(tu)s", "e.kind IN ('chan','loi')"]
    tham = {"tu": tu}
    if filters.get("project"):
        dieu_kien.append("e.project = %(project)s"); tham["project"] = filters.project
    if filters.get("chi_moi"):
        # "mới" = chữ ký chưa từng thấy trước khoảng đang xét
        pass

    rows = frappe.db.sql(f"""
        SELECT e.signature, MAX(e.marker) marker,
               COUNT(*) so_lan, COUNT(DISTINCT e.user) so_nguoi,
               COUNT(DISTINCT e.screen_id) so_man,
               MIN(e.ts) lan_dau, MAX(e.ts) gan_nhat,
               MAX(e.screen_name) man, MAX(e.endpoint) endpoint, MAX(e.message) thong_diep,
               GROUP_CONCAT(DISTINCT e.user ORDER BY e.user SEPARATOR ', ') nguoi
          FROM `tabFeedback Event` e
         WHERE {' AND '.join(dieu_kien)}
         GROUP BY e.signature
         ORDER BY so_nguoi DESC, so_lan DESC
         LIMIT 200
    """, tham, as_dict=True)

    # Vé tương ứng (nếu có) để bấm thẳng sang chỗ xử lý
    ve = {}
    if rows:
        for v in frappe.get_all("Feedback Comment",
                                filters={"signature": ["in", [r.signature for r in rows]]},
                                fields=["name", "signature", "status"]):
            ve.setdefault(v.signature, v)
    for r in rows:
        v = ve.get(r.signature)
        r["ve"] = v.name if v else None
        r["trang_thai_ve"] = v.status if v else None
        r["nguoi"] = (r.get("nguoi") or "")[:200]

    cot = [
        {"label": "Vé", "fieldname": "ve", "fieldtype": "Link", "options": "Feedback Comment", "width": 130},
        {"label": "Trạng thái", "fieldname": "trang_thai_ve", "fieldtype": "Data", "width": 95},
        {"label": "Người dính", "fieldname": "so_nguoi", "fieldtype": "Int", "width": 90},
        {"label": "Số lần", "fieldname": "so_lan", "fieldtype": "Int", "width": 80},
        {"label": "Màn", "fieldname": "man", "fieldtype": "Data", "width": 170},
        {"label": "Dấu hiệu", "fieldname": "marker", "fieldtype": "Data", "width": 110},
        {"label": "Thông điệp", "fieldname": "thong_diep", "fieldtype": "Data", "width": 420},
        {"label": "Ai", "fieldname": "nguoi", "fieldtype": "Data", "width": 200},
        {"label": "Lần đầu", "fieldname": "lan_dau", "fieldtype": "Datetime", "width": 150},
        {"label": "Gần nhất", "fieldname": "gan_nhat", "fieldtype": "Datetime", "width": 150},
        {"label": "Endpoint", "fieldname": "endpoint", "fieldtype": "Data", "width": 220},
        {"label": "Chữ ký", "fieldname": "signature", "fieldtype": "Data", "width": 110},
    ]
    return cot, rows
