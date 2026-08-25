"""Màn và nút ÍT/KHÔNG được dùng — danh mục TRỪ ĐI thực dùng.

Sổ chỉ thấy thứ được bấm; muốn thấy thứ KHÔNG ai bấm thì phải có danh mục đầy đủ
(`Feedback Manifest Item`, do app chủ khai lúc migrate) rồi trừ đi. Không có danh mục
thì nút chết là vô hình — đây chính là lý do nhiều tính năng "đã làm xong" mà không ai
biết chưa từng có người dùng.
"""

import frappe
from frappe.utils import add_days, now_datetime


def execute(filters=None):
    filters = frappe._dict(filters or {})
    ngay = int(filters.get("so_ngay") or 30)
    tu = add_days(now_datetime(), -ngay)

    dk = ["con_dung = 1"]
    tham = {}
    if filters.get("project"):
        dk.append("project = %(project)s"); tham["project"] = filters.project
    danh_muc = frappe.db.sql(f"""SELECT project, kind, item_id, item_name, screen_id, section_hint
                                   FROM `tabFeedback Manifest Item` WHERE {' AND '.join(dk)}""",
                             tham, as_dict=True)

    dung_man = {r[0]: (r[1], r[2]) for r in frappe.db.sql("""
        SELECT screen_id, COUNT(*), COUNT(DISTINCT user) FROM `tabFeedback Event`
         WHERE ts > %s AND IFNULL(screen_id,'') <> '' GROUP BY screen_id""", tu)}
    dung_nut = {r[0]: (r[1], r[2]) for r in frappe.db.sql("""
        SELECT action_id, COUNT(*), COUNT(DISTINCT user) FROM `tabFeedback Event`
         WHERE ts > %s AND IFNULL(action_id,'') <> '' GROUP BY action_id""", tu)}

    rows = []
    for m in danh_muc:
        bang = dung_man if m.kind == "screen" else dung_nut
        so_lan, so_nguoi = bang.get(m.item_id, (0, 0))
        rows.append({
            "kind": "Màn" if m.kind == "screen" else "Nút",
            "item_id": m.item_id, "item_name": m.item_name, "screen_id": m.screen_id,
            "section_hint": m.section_hint, "so_lan": so_lan, "so_nguoi": so_nguoi,
            "danh_gia": "CHƯA AI DÙNG" if so_lan == 0 else ("hiếm" if so_lan < 3 else ""),
        })
    rows.sort(key=lambda r: (r["so_lan"], r["kind"], r["item_id"]))

    cot = [
        {"label": "Loại", "fieldname": "kind", "fieldtype": "Data", "width": 70},
        {"label": "Đánh giá", "fieldname": "danh_gia", "fieldtype": "Data", "width": 130},
        {"label": "Lượt dùng", "fieldname": "so_lan", "fieldtype": "Int", "width": 100},
        {"label": "Người dùng", "fieldname": "so_nguoi", "fieldtype": "Int", "width": 100},
        {"label": "Tên", "fieldname": "item_name", "fieldtype": "Data", "width": 260},
        {"label": "Mã", "fieldname": "item_id", "fieldtype": "Data", "width": 260},
        {"label": "Thuộc màn", "fieldname": "screen_id", "fieldtype": "Data", "width": 200},
        {"label": "Nhóm", "fieldname": "section_hint", "fieldtype": "Data", "width": 140},
    ]
    return cot, rows
