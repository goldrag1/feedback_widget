"""Tên dự án khai ở Cài đặt phải là thứ MÁY CHỦ ghi vào sổ.

Bản gộp hai bảng cài đặt (26/08) đổi tên khoá `project` → `project_name`, còn bốn chỗ đọc
ở máy chủ (`su_kien.ghi_lo`, `kiem_ke_giao_dien`, `khai_danh_muc`, `tac_vu._du_an`) vẫn hỏi
khoá cũ: chúng lặng lẽ rơi về tên site, tức mọi bản ghi của một site khai tên riêng bị dồn
sang một rổ khác — không lỗi, không dòng log, chỉ là báo cáo đếm thiếu.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget import tac_vu
from feedback_widget.api import su_kien

TEN = "THU-du-an-khoa"
MAN = "kiem-thu-khoa"


class TestKhoaDuAn(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self._cu = frappe.db.get_single_value("Feedback Settings", "project_name")
		self._dat(TEN)

	def tearDown(self):
		frappe.db.delete("Feedback Event", {"screen_id": MAN})
		self._dat(self._cu or "")
		frappe.db.commit()

	def _dat(self, v):
		frappe.db.set_single_value("Feedback Settings", "project_name", v)
		frappe.clear_cache(doctype="Feedback Settings")
		frappe.db.commit()

	def test_tac_vu_doc_ten_du_an_da_khai(self):
		self.assertEqual(tac_vu._du_an(), TEN)

	def test_ghi_lo_khong_truyen_project_thi_lay_ten_da_khai(self):
		"""Trình duyệt cũ không gửi `project` — máy chủ phải tự khai đúng, không rơi về tên site."""
		su_kien.ghi_lo(events=[{"kind": "dung", "outcome": "ok", "screen_id": MAN}])
		frappe.db.commit()
		self.assertEqual(
			frappe.db.count("Feedback Event", {"project": TEN, "screen_id": MAN}), 1)
		self.assertEqual(
			frappe.db.count("Feedback Event", {"project": frappe.local.site, "screen_id": MAN}), 0)
