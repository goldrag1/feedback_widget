"""Đồ dùng chung cho test kịch bản màn: người thử, sự kiện giả, kịch bản giả, dọn dẹp."""

import frappe
from frappe.utils import add_to_date, get_datetime

NGUOI_A = "thu-kb-a@kiemthu.local"
NGUOI_B = "thu-kb-b@kiemthu.local"
TIEN_TO = "THU-KB-"


def nguoi(email, vai=()):
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0],
		                "send_welcome_email": 0, "user_type": "System User"}).insert(ignore_permissions=True)
	for v in vai:
		if not frappe.db.exists("Has Role", {"parent": email, "role": v, "parenttype": "User"}):
			frappe.get_doc("User", email).add_roles(v)
	return email


def su_kien(user, man, luc, kind="dung", action_id=None, endpoint=None, outcome=None, message=None, session_id="s1"):
	return frappe.get_doc({
		"doctype": "Feedback Event", "project": TIEN_TO + "du-an", "kind": kind, "ts": get_datetime(luc),
		"user": user, "screen_id": man, "action_id": action_id, "endpoint": endpoint,
		"outcome": outcome, "message": message, "session_id": session_id,
	}).insert(ignore_permissions=True)


def kich_ban(man, chang=None, buoc=None, huong_dan=None, meo=None, ten=None):
	chang = chang or [{"ma": "lam-quen", "ten": "Làm quen", "thu_tu": 1, "loai": "Một lần", "diem": 30}]
	d = frappe.get_doc({
		"doctype": "Feedback Playbook", "ten": ten or (TIEN_TO + man), "man": man,
		"duong_dan": "/app/" + man.split("/")[0], "dang_bat": 1,
		"chang": chang, "buoc": buoc or [], "huong_dan": huong_dan or [], "meo": meo or [],
	})
	d.insert(ignore_permissions=True)
	return d


def don_dep():
	for n in frappe.get_all("Feedback Mission", filters={"kich_ban": ["in", _kb()]}, pluck="name"):
		frappe.delete_doc("Feedback Mission", n, force=True, ignore_permissions=True)
	nguoi_thu = frappe.get_all("Feedback Notice User", filters={"user": ["in", [NGUOI_A, NGUOI_B]],
	                           "parenttype": "Feedback Notice"}, pluck="parent")
	for n in set(frappe.get_all("Feedback Notice", filters={"kich_ban": ["in", _kb()]}, pluck="name") + nguoi_thu):
		frappe.db.delete("Feedback Notice Seen", {"thong_bao": n})
		frappe.delete_doc("Feedback Notice", n, force=True, ignore_permissions=True)
	for kb in _kb():
		frappe.db.delete("Feedback Playbook Progress", {"kich_ban": kb})
		frappe.delete_doc("Feedback Playbook", kb, force=True, ignore_permissions=True)
	for u in (NGUOI_A, NGUOI_B):
		frappe.db.delete("Feedback Point", {"user": u})
		frappe.db.delete("Feedback Badge Award", {"user": u})
		frappe.db.delete("Feedback Event", {"user": u})
		frappe.db.delete("Feedback Comment", {"submitter_user": u})
		frappe.db.delete("ToDo", {"owner": u})
	frappe.db.delete("Feedback Event", {"project": ["like", TIEN_TO + "%"]})
	frappe.db.commit()


def _kb():
	return frappe.get_all("Feedback Playbook", filters={"ten": ["like", TIEN_TO + "%"]}, pluck="name") or ["__none__"]


def sau(luc, **kw):
	return add_to_date(get_datetime(luc), **kw)


def dat_cai_dat(**kv) -> dict:
	"""Ghi thẳng `tabSingles` (như cai_dat.py đọc), trả giá trị cũ để khôi phục."""
	cu = {}
	for k, v in kv.items():
		r = frappe.db.sql("SELECT value FROM `tabSingles` WHERE doctype='Feedback Settings' AND field=%s", k)
		cu[k] = r[0][0] if r else None
		frappe.db.sql("DELETE FROM `tabSingles` WHERE doctype='Feedback Settings' AND field=%s", k)
		if v is not None:
			frappe.db.sql("INSERT INTO `tabSingles` (doctype, field, value) VALUES ('Feedback Settings', %s, %s)", (k, v))
	frappe.db.commit()
	return cu
