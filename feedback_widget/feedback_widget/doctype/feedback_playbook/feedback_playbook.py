"""Kịch bản màn: hướng dẫn lần đầu, chặng mục tiêu, mẹo (spec §4.1)."""

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class FeedbackPlaybook(Document):
	def validate(self):
		ma = [c.ma for c in self.chang]
		if len(ma) != len(set(ma)):
			frappe.throw("Mã chặng bị trùng: mỗi chặng một mã riêng.")
		for b in self.buoc:
			if b.chang not in ma:
				frappe.throw(f"Bước «{b.mo_ta}» trỏ vào chặng «{b.chang}» không có trong kịch bản.")
		for c in self.chang:
			if c.loai == "Duy trì" and not c.chu_ky:
				c.chu_ky = "Ngày"
		if cint(self.dang_bat):
			self._khong_chong_lan()

	def _khong_chong_lan(self):
		"""Hai kịch bản đang bật cùng khớp một màn thì không biết chấm theo cái nào."""
		from feedback_widget.kich_ban import khop_man

		mau = lambda m: (m or "").replace("*", "Z")
		for k in frappe.get_all("Feedback Playbook", filters={"dang_bat": 1, "name": ["!=", self.name or ""]},
		                        fields=["name", "ten", "man"]):
			if khop_man(k.man, mau(self.man)) or khop_man(self.man, mau(k.man)):
				frappe.throw(f"Màn «{self.man}» chồng lên kịch bản đang bật «{k.ten}» ({k.man}). "
				             "Tắt một trong hai, hoặc viết mẫu màn cụ thể hơn.")

	def on_update(self):
		frappe.clear_document_cache(self.doctype, self.name)


@frappe.whitelist(methods=["POST"])
def phat_lai_huong_dan(kich_ban: str) -> dict:
	"""Hướng dẫn đổi nhiều: cho MỌI người xem lại từ đầu (spec §10.6)."""
	frappe.only_for("System Manager")
	frappe.db.sql("""UPDATE `tabFeedback Playbook Progress` SET huong_dan = 'Chưa xem', huong_dan_the = 0
	                 WHERE kich_ban = %s""", kich_ban)
	return {"ok": True, "so_nguoi": frappe.db.count("Feedback Playbook Progress", {"kich_ban": kich_ban})}
