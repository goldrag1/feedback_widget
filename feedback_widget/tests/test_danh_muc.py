"""Danh mục màn/nút — điều kiện để trả lời "cái gì KHÔNG ai dùng"."""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget.api import su_kien
from feedback_widget.feedback_widget.report.unused_ui import unused_ui

DU_AN = "kiemthu-danhmuc"


class TestDanhMuc(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self._don()

	def tearDown(self):
		self._don()

	def _don(self):
		frappe.db.delete("Feedback Manifest Item", {"project": DU_AN})
		frappe.db.delete("Feedback Event", {"project": DU_AN})
		frappe.db.commit()

	def test_man_khong_ai_vao_hien_ra_la_CHUA_AI_DUNG(self):
		su_kien.khai_danh_muc(project=DU_AN, nguon="kiemthu", items=[
			{"kind": "screen", "item_id": "#/co-nguoi-vao", "item_name": "Có người vào"},
			{"kind": "screen", "item_id": "#/khong-ai-vao", "item_name": "Không ai vào"},
		])
		su_kien.ghi_lo(project=DU_AN, events=[
			{"kind": "dung", "screen_id": "#/co-nguoi-vao", "outcome": "ok"}])
		_, rows = unused_ui.execute({"project": DU_AN, "so_ngay": 7})
		theo_ma = {r["item_id"]: r for r in rows}
		self.assertEqual(theo_ma["#/khong-ai-vao"]["danh_gia"], "CHƯA AI DÙNG")
		self.assertEqual(theo_ma["#/khong-ai-vao"]["so_lan"], 0)
		self.assertEqual(theo_ma["#/co-nguoi-vao"]["so_lan"], 1)

	def test_muc_bi_GO_khoi_ma_thi_danh_dau_chu_khong_XOA(self):
		"""Lịch sử dùng của một màn đã gỡ vẫn có nghĩa ("trước đó 12 người/ngày")."""
		su_kien.khai_danh_muc(project=DU_AN, nguon="kiemthu", items=[
			{"kind": "screen", "item_id": "#/con", "item_name": "Còn"},
			{"kind": "screen", "item_id": "#/da-go", "item_name": "Đã gỡ"},
		])
		kq = su_kien.khai_danh_muc(project=DU_AN, nguon="kiemthu", items=[
			{"kind": "screen", "item_id": "#/con", "item_name": "Còn"}])
		self.assertEqual(kq["khong_con_trong_ma"], 1)
		self.assertTrue(frappe.db.exists("Feedback Manifest Item", f"{DU_AN}::screen::#/da-go"))
		self.assertEqual(frappe.db.get_value("Feedback Manifest Item",
		                                     f"{DU_AN}::screen::#/da-go", "con_dung"), 0)

	def test_kiem_ke_runtime_khong_de_trung(self):
		"""Mỗi lần mở màn lại kiểm kê — không được đẻ bản ghi mới mỗi lần."""
		nut = [{"item_id": "#/a::Lưu", "item_name": "Lưu", "screen_id": "#/a"}]
		su_kien.kiem_ke_giao_dien(project=DU_AN, items=nut)
		su_kien.kiem_ke_giao_dien(project=DU_AN, items=nut)
		self.assertEqual(frappe.db.count("Feedback Manifest Item",
		                                 {"project": DU_AN, "kind": "action"}), 1)
