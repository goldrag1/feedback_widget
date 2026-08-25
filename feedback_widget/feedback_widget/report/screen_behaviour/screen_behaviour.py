"""Hành vi theo màn — lượt vào, thao tác, TỈ LỆ BỊ CHẶN, thời gian.

Tỉ lệ mới là thứ so sánh được giữa các màn: một màn 200 lượt/5 lần chặn khoẻ hơn hẳn
một màn 8 lượt/5 lần chặn, dù con số tuyệt đối bằng nhau. Vì vậy mọi cột đếm ở đây đều
đi kèm mẫu số.
"""

import frappe
from frappe.utils import add_days, now_datetime


def execute(filters=None):
    filters = frappe._dict(filters or {})
    ngay = int(filters.get("so_ngay") or 7)
    tu = add_days(now_datetime(), -ngay)
    dk, tham = ["ts > %(tu)s"], {"tu": tu}
    if filters.get("project"):
        dk.append("project = %(project)s"); tham["project"] = filters.project

    rows = frappe.db.sql(f"""
        SELECT screen_id, MAX(screen_name) man,
               SUM(kind='dung') luot,
               SUM(kind='dung' AND IFNULL(action_id,'') <> '') thao_tac,
               SUM(kind='chan') bi_chan,
               SUM(kind='loi') loi,
               COUNT(DISTINCT user) so_nguoi,
               ROUND(AVG(NULLIF(duration_ms,0))) tb_ms
          FROM `tabFeedback Event`
         WHERE {' AND '.join(dk)} AND IFNULL(screen_id,'') <> ''
         GROUP BY screen_id ORDER BY luot DESC LIMIT 200
    """, tham, as_dict=True)

    for r in rows:
        mau_so = (r.luot or 0) + (r.bi_chan or 0) + (r.loi or 0)
        r["ti_le_chan"] = round(100.0 * ((r.bi_chan or 0) + (r.loi or 0)) / mau_so, 1) if mau_so else 0

    cot = [
        {"label": "Màn", "fieldname": "man", "fieldtype": "Data", "width": 230},
        {"label": "Mã màn", "fieldname": "screen_id", "fieldtype": "Data", "width": 200},
        {"label": "Lượt vào", "fieldname": "luot", "fieldtype": "Int", "width": 90},
        {"label": "Thao tác", "fieldname": "thao_tac", "fieldtype": "Int", "width": 90},
        {"label": "Người", "fieldname": "so_nguoi", "fieldtype": "Int", "width": 80},
        {"label": "Bị chặn", "fieldname": "bi_chan", "fieldtype": "Int", "width": 90},
        {"label": "Lỗi", "fieldname": "loi", "fieldtype": "Int", "width": 70},
        {"label": "% chặn/lỗi", "fieldname": "ti_le_chan", "fieldtype": "Float", "precision": 1, "width": 100},
        {"label": "TB (ms)", "fieldname": "tb_ms", "fieldtype": "Int", "width": 90},
    ]
    return cot, rows
