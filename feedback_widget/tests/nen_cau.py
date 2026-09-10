"""Nền chung cho mọi bài kiểm chạy CẦU Error Log.

Cầu đọc bảng `tabError Log` THẬT của site đang chạy bộ kiểm. Một bài kiểm lùi mốc
đọc về quá khứ (để dựng lại ca "lỗi cũ, cầu chạy muộn") sẽ kéo theo mọi dòng lỗi
thật của site vào hộp thư — và teardown dọn theo dấu riêng của bài kiểm thì không
bắt được chúng, vì chúng không mang dấu ấy.

Đo trên site asxh 10/09/2026: chạy `bench run-tests --app feedback_widget` một lượt
để lại **13 vé** cho những lỗi thật đã xử lý xong, trong hộp thư của chủ dự án. Không
có gì trong bộ kiểm báo động — vé trông y hệt vé thật, vì chúng LÀ vé thật, chỉ là
dựng lại lần hai.

Nên teardown phải dọn theo thứ chắc chắn: mọi vé/dòng sổ `viec-nen` SINH RA trong
lúc bài kiểm chạy. Mốc thời gian là thứ phân biệt được, không phải nội dung.
"""

import frappe
from frappe.utils import now_datetime

from feedback_widget import tac_vu


class NenCau:
	"""Trộn vào `FrappeTestCase`. Gọi `_giu_hien_truong()` ở setUp, `_tra_hien_truong()` ở tearDown."""

	def _giu_hien_truong(self):
		self._moc_cu = frappe.db.get_global(tac_vu.MOC)
		# Mốc thời gian, không phải danh sách tên: `collect` gộp theo chữ ký nên một vé
		# CŨ có thể chỉ được tăng `occurrences` chứ không sinh tên mới — nhưng vé sinh
		# mới thì luôn có `creation` sau mốc này.
		self._tu_luc = now_datetime()
		frappe.db.commit()

	def _tra_hien_truong(self):
		for dt in ("Feedback Comment", "Feedback Event"):
			for n in frappe.get_all(dt, filters={"screen_id": "viec-nen",
			                                     "creation": [">=", self._tu_luc]}, pluck="name"):
				frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
		# Trả lại ĐÚNG trạng thái cũ. `set_global(MOC, None)` KHÔNG phải là "xoá": nó ghi
		# chuỗi "None", rồi `_moc_da_doc()` trả chuỗi ấy và câu SQL `creation > 'None'`
		# khớp 0 dòng — cầu im lặng không đọc gì nữa.
		if self._moc_cu is None:
			frappe.db.sql("DELETE FROM `tabDefaultValue` WHERE defkey=%s AND parent='__default'",
			              (tac_vu.MOC,))
			frappe.cache.delete_key("defaults")
		else:
			frappe.db.set_global(tac_vu.MOC, self._moc_cu)
		frappe.db.commit()
