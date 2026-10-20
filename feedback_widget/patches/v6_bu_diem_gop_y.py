"""Kịch bản màn — bù điểm MỘT lần cho góp ý người gõ đã Resolved trước ngày bật (spec §8.2).

Người góp ý sớm có điểm ngay ngày đầu. Chỉ bật `co_ich` (không bật `thanh_cai_tien` —
việc đó cần người phân loại). Chạy lại vô hại: điểm có khoá unique.
"""

import frappe

from feedback_widget.diem import theo_gop_y


def execute(chi_ve=None):
	loc = {"source": "user", "status": "Resolved", "submitter_user": ["is", "set"]}
	if chi_ve:   # test chỉ chạm vé của nó, không đụng sổ thật của site
		loc["name"] = ["in", chi_ve]
	for ten in frappe.get_all("Feedback Comment", filters=loc, pluck="name"):
		ve = frappe.get_doc("Feedback Comment", ten)
		if not int(ve.co_ich or 0):
			ve.db_set("co_ich", 1, update_modified=False)
		theo_gop_y(ve)
