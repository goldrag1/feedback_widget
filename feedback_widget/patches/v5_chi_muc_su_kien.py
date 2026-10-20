"""Chỉ mục cho sổ sự kiện — kịch bản màn chấm theo (người, thời gian) và (màn, thời gian).

Đo prod 20/10/2026: `tabFeedback Event` 611.658 dòng, chỉ có chỉ mục `name` + `creation`,
nên mọi câu "người X đã làm gì trên màn Y từ mốc Z" quét cả bảng. Chạy lại vô hại.
"""

import frappe


def execute():
	frappe.db.add_index("Feedback Event", ["user", "ts"], index_name="fbw_user_ts")
	frappe.db.add_index("Feedback Event", ["screen_id", "ts"], index_name="fbw_screen_ts")
