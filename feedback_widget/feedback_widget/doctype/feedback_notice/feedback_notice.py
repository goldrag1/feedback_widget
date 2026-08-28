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

	def on_update(self):
		"""Báo NGAY cho máy đang mở — chủ đầu tư 28/08: gửi xong người dùng phải thấy,
		không phải sau khi họ tự tải lại trang.

		Đặt ở `on_update` (Frappe chạy nó cho cả lượt tạo lẫn lượt sửa) chứ không đặt ở
		script/màn nào tạo thông báo: Desk, `bao_ve_da_xu_ly` và mọi lượt gọi API là ba
		đường khác nhau, ba bản chép sẽ trôi lệch ngay lần đầu.

		Lỗi ở đây KHÔNG bao giờ được làm hỏng lượt lưu: redis realtime chết thì thông báo
		vẫn phải lưu được (và trình duyệt vẫn nhặt nó qua nhịp hỏi lại dự phòng).
		"""
		if not self._can_day_lai():
			return
		try:
			from feedback_widget.api.thong_bao import day_ngay

			day_ngay(self)
		except Exception:
			frappe.log_error(title=f"day thong bao {self.name}", message=frappe.get_traceback())

	def _can_day_lai(self) -> bool:
		"""Vừa tạo, hay vừa đổi thứ người nhận sẽ THẤY / phạm vi ai được nhận?

		Không bắn lại trên mọi lượt lưu: sửa một dấu phẩy trong `project` mà cả nhà nảy
		thẻ lần nữa thì cái loa sẽ bị tắt, và lúc đó cái đáng báo cũng chết theo.
		"""
		truoc = self.get_doc_before_save()
		if truoc is None:
			return True
		if any(self.has_value_changed(f) for f in TRUONG_DAY_LAI):
			return True
		return _nguoi_nhan(self) != _nguoi_nhan(truoc)


# Đổi mấy trường này = người nhận thấy khác đi ⇒ đáng bắn lại. `dang_bat` nằm trong đây
# nên bật lại một thông báo đã tắt cũng tới ngay.
TRUONG_DAY_LAI = ("tieu_de", "noi_dung", "duong_dan", "pham_vi", "dang_bat", "bat_dau", "het_han")


def _nguoi_nhan(doc) -> tuple:
	"""Cặp (người, vai) đã sắp xếp — dùng để so trước/sau, vì `has_value_changed` không
	nhìn thấy thay đổi trong bảng con."""
	nguoi = sorted((r.user or "") for r in (doc.get("cac_nguoi") or []))
	vai = sorted((r.role or "") for r in (doc.get("cac_vai") or []))
	return (tuple(nguoi), tuple(vai))
