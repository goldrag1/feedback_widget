"""Màn chưa ai dùng (spec §6.7): kịch bản đang bật × số người đạt chặng đầu. Trả lời câu
"chức năng nào chưa ai đụng" — xếp màn ít người đạt nhất lên đầu."""

import frappe

from feedback_widget import kich_ban as kb


def execute(filters=None):
	return cot(), du_lieu()


def cot():
	return [
		{"label": "Kịch bản", "fieldname": "kich_ban", "fieldtype": "Link", "options": "Feedback Playbook", "width": 110},
		{"label": "Màn", "fieldname": "ten_kb", "fieldtype": "Data", "width": 200},
		{"label": "Mẫu màn", "fieldname": "man", "fieldtype": "Data", "width": 160},
		{"label": "Chặng đầu", "fieldname": "chang_dau", "fieldtype": "Data", "width": 110},
		{"label": "Số người đạt", "fieldname": "so_dat", "fieldtype": "Int", "width": 100},
		{"label": "Đã mở màn", "fieldname": "so_mo", "fieldtype": "Int", "width": 90},
		{"label": "Được giao", "fieldname": "so_giao", "fieldtype": "Int", "width": 90},
		{"label": "Lần cuối có người mở", "fieldname": "lan_cuoi_mo", "fieldtype": "Datetime", "width": 160},
	]


def du_lieu() -> list:
	rows = []
	for k in frappe.get_all("Feedback Playbook", filters={"dang_bat": 1}, pluck="name"):
		d = frappe.get_cached_doc("Feedback Playbook", k)
		dau = sorted(d.chang, key=lambda c: c.thu_tu or 0)
		dau = dau[0] if dau else None
		so_dat = 0
		if dau:
			for p in frappe.get_all("Feedback Playbook Progress", filters={"kich_ban": k}, fields=["chang_xong"]):
				if dau.ma in kb._j(p.chang_xong):
					so_dat += 1
		mo = frappe.db.sql("""SELECT COUNT(DISTINCT user), MAX(ts) FROM `tabFeedback Event`
		                      WHERE screen_id LIKE %s AND IFNULL(user, '') NOT IN ('', 'Guest')""", kb.mau_like(d.man))[0]
		so_giao = frappe.db.sql("""SELECT COUNT(DISTINCT a.user) FROM `tabFeedback Mission Assignee` a
		                           JOIN `tabFeedback Mission` m ON m.name = a.parent WHERE m.kich_ban = %s""", k)[0][0]
		rows.append({"kich_ban": k, "ten_kb": d.ten, "man": d.man, "chang_dau": dau.ten if dau else "",
		             "so_dat": so_dat, "so_mo": mo[0] or 0, "so_giao": so_giao or 0, "lan_cuoi_mo": mo[1]})
	return sorted(rows, key=lambda r: (r["so_dat"], r["so_mo"]))
