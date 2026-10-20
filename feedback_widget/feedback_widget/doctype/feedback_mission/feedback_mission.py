"""Giao một kịch bản cho người cụ thể, kèm chặng cần đạt và hạn (spec §4.7)."""

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, cint, get_datetime, now_datetime


class FeedbackMission(Document):
	def before_insert(self):
		self.bat_dau = self.bat_dau or now_datetime()
		self.het_han = self.het_han or add_days(get_datetime(self.bat_dau), 7)
		self.nguoi_giao = self.nguoi_giao or frappe.session.user

	def validate(self):
		from feedback_widget.cai_dat import cai_dat

		kb = frappe.get_doc("Feedback Playbook", self.kich_ban)
		if self.chang_muc_tieu not in [c.ma for c in kb.chang]:
			frappe.throw(f"Chặng «{self.chang_muc_tieu}» không có trong kịch bản «{kb.ten}».")
		if self.bat_dau and self.het_han:
			gioi_han = max(cint(cai_dat().get("retention_days")) - 7, 1)
			if (get_datetime(self.het_han) - get_datetime(self.bat_dau)).days > gioi_han:
				frappe.throw(f"Hạn giao tối đa {gioi_han} ngày: sổ thao tác chỉ giữ "
				             f"{cai_dat().get('retention_days')} ngày, giao dài hơn sẽ mất dấu nửa chừng.")
		thieu = []
		for a in self.nguoi_nhan:
			if not frappe.db.get_value("User", a.user, "enabled"):
				thieu.append(f"Tài khoản {a.user} đang bị tắt.")
				continue
			ly_do = thieu_quyen(a.user, kb.duong_dan)
			if ly_do:
				thieu.append(ly_do)
		if thieu:
			_ghi_so_chan(self, thieu)
			frappe.throw("Chưa giao được:<br>" + "<br>".join(thieu))

	def after_insert(self):
		from feedback_widget import kich_ban, nhac

		kb = frappe.get_cached_doc("Feedback Playbook", self.kich_ban)
		ch = next((c for c in kb.chang if c.ma == self.chang_muc_tieu), None)
		for a in self.nguoi_nhan:
			kich_ban.tien_do(self.kich_ban, a.user, tao=True, luc=self.bat_dau)
			if frappe.flags.kb_khong_gui_moi:
				continue
			muc_tieu = f"đạt «{ch.ten}»" if ch.loai == "Một lần" else f"giữ «{ch.ten}» {cint(self.chuoi_muc_tieu)} kỳ liền"
			nhac.gui_nhac(a.user, self.kich_ban, "N0", f"Mời anh/chị dùng thử «{kb.ten}»",
			              ((kb.ly_do or "").strip() + f" Mục tiêu: {muc_tieu} trước "
			               f"{get_datetime(self.het_han).strftime('%d/%m')}.").strip(),
			              kb.duong_dan, nhiem_vu=self.name, bo_qua_tran=True)


def thieu_quyen(user, duong_dan) -> str | None:
	"""Người này có mở được màn của kịch bản không. Trả câu giải thích, hoặc None nếu được."""
	ten = frappe.db.get_value("User", user, "full_name") or user
	p = [x for x in (duong_dan or "").split("?")[0].split("/") if x]
	if len(p) < 2 or p[0] not in ("app", "desk"):
		return None
	vai = set(frappe.get_roles(user))
	if "System Manager" in vai:
		return None
	trang = p[1]
	if frappe.db.exists("Page", trang):
		can = set(frappe.get_all("Has Role", filters={"parent": trang, "parenttype": "Page"}, pluck="role"))
		if can and not (can & vai):
			return f"{ten} không mở được trang «{trang}» (cần một trong các vai: {', '.join(sorted(can))})."
		return None
	if trang == "query-report" and len(p) > 2:
		rp = p[2].replace("-", " ")
		if frappe.db.exists("Report", rp) and not frappe.has_permission("Report", "read", rp, user=user):
			return f"{ten} không mở được báo cáo «{rp}»."
		return None
	dt = frappe.db.get_value("DocType", {"name": ["like", trang.replace("-", "_")]}, "name") or \
		next((d for d in frappe.get_all("DocType", pluck="name") if frappe.scrub(d).replace("_", "-") == trang), None)
	if dt and not frappe.has_permission(dt, "read", user=user):
		return f"{ten} không mở được «{dt}» (thiếu quyền đọc)."
	return None


def _ghi_so_chan(doc, thieu):
	"""Cổng chặn phải để lại dòng sổ — kể cả khi lượt lưu bị cuộn lại: ghi SAU rollback."""
	tin = " | ".join(thieu)[:1000]
	nguoi = frappe.session.user

	def ghi():
		try:
			frappe.get_doc({"doctype": "Feedback Event", "project": frappe.local.site, "kind": "chan",
			                "ts": now_datetime(), "user": nguoi, "screen_id": "Form/Feedback Mission",
			                "outcome": "chan", "signature": "kich-ban-giao-thieu-quyen",
			                "message": tin}).insert(ignore_permissions=True)
			frappe.db.commit()
		except Exception:
			pass

	frappe.db.after_rollback.add(ghi)
	if frappe.flags.in_test:   # test không đi qua tầng request nên không có rollback tự động
		ghi()
