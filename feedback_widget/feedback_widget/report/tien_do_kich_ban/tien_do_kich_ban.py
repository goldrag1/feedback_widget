"""Tiến độ kịch bản (spec §6.7) — mỗi dòng một cặp (kịch bản, người).

Cột trả lời ba câu người giao hỏi: người này đang ở đâu, nhắc có ăn thua không, và ai
đang KẸT (đã nhắc mà không động tay). "Có tác dụng" = trong 24 giờ sau lời nhắc có ít nhất
một sự kiện của chính người đó trên màn của kịch bản; khớp màn đi qua `kich_ban.mau_like`
để báo cáo và bộ chấm hiểu "màn" cùng một nghĩa.
"""

from datetime import timedelta

import frappe
from frappe.utils import cint, get_datetime, now_datetime

from feedback_widget import kich_ban as kb

CUA_SO_TAC_DUNG = timedelta(hours=24)


def execute(filters=None):
	f = frappe._dict(filters or {})
	return cot(), du_lieu(f)


def cot():
	return [
		{"label": "Kịch bản", "fieldname": "kich_ban", "fieldtype": "Link", "options": "Feedback Playbook", "width": 110},
		{"label": "Màn", "fieldname": "ten_kb", "fieldtype": "Data", "width": 180},
		{"label": "Người", "fieldname": "user", "fieldtype": "Link", "options": "User", "width": 190},
		{"label": "Chặng hiện tại", "fieldname": "chang_hien_tai", "fieldtype": "Data", "width": 120},
		{"label": "Bước xong", "fieldname": "buoc", "fieldtype": "Data", "width": 85},
		{"label": "Chuỗi duy trì", "fieldname": "chuoi", "fieldtype": "Int", "width": 95},
		{"label": "Lần cuối mở màn", "fieldname": "lan_cuoi_mo", "fieldtype": "Datetime", "width": 150},
		{"label": "Số lời nhắc", "fieldname": "so_nhac", "fieldtype": "Int", "width": 90},
		{"label": "% nhắc có tác dụng (24h)", "fieldname": "pct_tac_dung", "fieldtype": "Data", "width": 120},
		{"label": "Đang kẹt", "fieldname": "dang_ket", "fieldtype": "Check", "width": 75},
		{"label": "Giao bởi", "fieldname": "nguoi_giao", "fieldtype": "Link", "options": "User", "width": 160},
		{"label": "Hạn", "fieldname": "het_han", "fieldtype": "Datetime", "width": 150},
		{"label": "Trạng thái", "fieldname": "trang_thai", "fieldtype": "Data", "width": 110},
	]


def tac_dung_cua_nhac(user, man, cac_luc, luc=None) -> list:
	"""Mỗi lời nhắc (theo thời điểm gửi) → True/False/None. None = cửa sổ 24 giờ chưa hết mà
	chưa có hành động: chưa thể nói là vô tác dụng, nên không tính vào mẫu số."""
	luc = get_datetime(luc) if luc else now_datetime()
	ra = []
	for t in cac_luc:
		t = get_datetime(t)
		co = frappe.db.sql("""SELECT 1 FROM `tabFeedback Event` WHERE user = %s AND screen_id LIKE %s
		                      AND ts >= %s AND ts < %s LIMIT 1""", (user, kb.mau_like(man), t, t + CUA_SO_TAC_DUNG))
		ra.append(True if co else (None if luc < t + CUA_SO_TAC_DUNG else False))
	return ra


def du_lieu(f, luc=None) -> list:
	luc = get_datetime(luc) if luc else now_datetime()
	loc = {}
	if f.get("kich_ban"):
		loc["kich_ban"] = f.kich_ban
	if f.get("user"):
		loc["user"] = f.user
	rows = []
	for p in frappe.get_all("Feedback Playbook Progress", filters=loc,
	                        fields=["kich_ban", "user", "chang_hien_tai", "buoc_xong", "duy_tri"],
	                        order_by="kich_ban asc, user asc"):
		k = frappe.get_cached_doc("Feedback Playbook", p.kich_ban)
		buoc_xong = kb._j(p.buoc_xong)
		dt = kb._j(p.duy_tri)
		mot_lan = {c.ma for c in k.chang if c.loai == "Một lần"}
		tong = [b for b in k.buoc if b.chang in mot_lan]
		chuoi = max([kb.chuoi_hien_tai(c, dt.get(c.ma) or {}, luc) for c in k.chang if c.loai == "Duy trì"] or [0])
		lan_cuoi = frappe.db.sql("""SELECT MAX(ts) FROM `tabFeedback Event` WHERE user = %s AND screen_id LIKE %s""",
		                         (p.user, kb.mau_like(k.man)))[0][0]
		nhac = frappe.db.sql("""SELECT n.creation FROM `tabFeedback Notice` n
		                        JOIN `tabFeedback Notice User` u ON u.parent = n.name AND u.parenttype = 'Feedback Notice'
		                        WHERE n.kich_ban = %s AND u.user = %s AND IFNULL(n.loai_nhac, '') != ''
		                        ORDER BY n.creation ASC""", (p.kich_ban, p.user), pluck=True)
		td = tac_dung_cua_nhac(p.user, k.man, nhac, luc)
		da_ro = [x for x in td if x is not None]
		# Kẹt = lời nhắc GẦN NHẤT đã hết cửa sổ 24 giờ mà không có hành động nào.
		dang_ket = bool(td) and td[-1] is False
		if f.get("dang_ket") and not dang_ket:
			continue
		nv = frappe.db.sql("""SELECT m.nguoi_giao, m.het_han, a.trang_thai FROM `tabFeedback Mission Assignee` a
		                      JOIN `tabFeedback Mission` m ON m.name = a.parent
		                      WHERE m.kich_ban = %s AND a.user = %s ORDER BY m.creation DESC LIMIT 1""",
		                   (p.kich_ban, p.user), as_dict=True)
		nv = nv[0] if nv else frappe._dict()
		rows.append({
			"kich_ban": p.kich_ban, "ten_kb": k.ten, "user": p.user,
			"chang_hien_tai": next((c.ten for c in k.chang if c.ma == p.chang_hien_tai), p.chang_hien_tai or ""),
			"buoc": f"{len([b for b in tong if b.name in buoc_xong])}/{len(tong)}",
			"chuoi": chuoi, "lan_cuoi_mo": lan_cuoi, "so_nhac": len(nhac),
			"pct_tac_dung": f"{round(100 * sum(da_ro) / len(da_ro))}%" if da_ro else "—",
			"dang_ket": 1 if dang_ket else 0,
			"nguoi_giao": nv.get("nguoi_giao"), "het_han": nv.get("het_han"), "trang_thai": nv.get("trang_thai") or "",
		})
	return rows
