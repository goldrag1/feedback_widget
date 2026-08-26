"""Thông báo ĐẨY cho người dùng — do người phát triển/quản trị tạo ở bước cuối lượt ship.

Vì sao có DocType này: sửa xong mà người báo không biết thì với họ nó chưa xảy ra — họ đã
bỏ đường ấy và không quay lại thử. Đo trên prod 26/08: 93 vé người gõ trong 60 ngày, 74 vé
đã Resolved, 0 lượt báo ngược.

KHÔNG phải màn cho người dùng nghiệp vụ soạn tin: quyền tạo giới hạn ở System Manager.
Một cái loa ai cũng bấm được sẽ nhanh chóng thành thứ người ta tắt.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, now_datetime


class FeedbackNotice(Document):
	def validate(self):
		self.tieu_de = (self.tieu_de or "").strip()
		self.duong_dan = (self.duong_dan or "").strip()

		if self.pham_vi == "Một người" and not self.cac_nguoi:
			frappe.throw(_("Phạm vi 'Một người' phải khai ít nhất một người nhận."))
		if self.pham_vi == "Nhóm vai" and not self.cac_vai:
			frappe.throw(_("Phạm vi 'Nhóm vai' phải khai ít nhất một vai."))

		# Lời cảm ơn là BẮT BUỘC khi thông báo sinh ra từ một vé: người gõ vé bỏ công mô
		# tả và chụp màn; việc đó biến mất vào im lặng thì lần sau họ tự xoay xở và mình
		# mù trở lại. Gọi TÊN — "theo góp ý của người dùng" là cảm ơn gửi cho không ai cả.
		if self.nguon_ve and not (self.cam_on_ai or "").strip():
			ve = frappe.db.get_value("Feedback Comment", self.nguon_ve,
			                         ["submitter_user", "user_full_name", "owner"], as_dict=True) or {}
			if (ve.get("user_full_name") or "").strip():
				self.cam_on_ai = ve["user_full_name"].strip()
				return
			nguoi = ve.get("submitter_user") or ve.get("owner")
			ten = frappe.db.get_value("User", nguoi, "full_name") if nguoi else None
			if ten:
				self.cam_on_ai = ten
			else:
				frappe.throw(_("Thông báo sinh ra từ vé {0} phải ghi TÊN người được cảm ơn.")
				             .format(self.nguon_ve))

		if not self.bat_dau:
			self.bat_dau = now_datetime()
		if not self.het_han:
			# 14 ngày: đủ để người nghỉ phép quay lại vẫn thấy, không đủ lâu để thành rác.
			self.het_han = add_days(self.bat_dau, 14)
