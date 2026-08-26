"""Sổ thô: che thông tin nhạy cảm, tôn trọng công tắc, không làm hỏng thao tác khi dữ liệu bẩn."""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget.api import su_kien

DU_AN = "kiemthu-sokien"


class TestSoSuKien(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Feedback Event", {"project": DU_AN})
		self._bat(1)

	def tearDown(self):
		frappe.db.delete("Feedback Event", {"project": DU_AN})
		self._bat(1)
		frappe.db.commit()

	def _bat(self, v):
		frappe.db.set_single_value("Feedback Settings", "collect_usage", v)
		frappe.clear_cache(doctype="Feedback Settings")
		frappe.db.commit()

	def test_che_thong_tin_nhay_cam_o_MOI_do_sau(self):
		"""Sổ đi qua tay nhiều người; một `password` lọt vào đây là lọt vĩnh viễn."""
		su_kien.ghi_lo(project=DU_AN, events=[{
			"kind": "chan", "message": "[MAYBAN] Máy bận",
			"context": {"args": {"password": "bí mật", "ma": "N102", "sau": {"api_key": "k", "ok": 1}}},
		}])
		e = frappe.get_all("Feedback Event", filters={"project": DU_AN}, fields=["context"])[0]
		self.assertIn('"password": "***"', e.context)
		self.assertIn('"api_key": "***"', e.context)
		self.assertIn('"ma": "N102"', e.context)      # cái không nhạy cảm phải GIỮ NGUYÊN

	def test_dong_hong_bi_bo_phan_con_lai_van_vao(self):
		kq = su_kien.ghi_lo(project=DU_AN, events=[
			{"kind": "dung", "screen_id": "#/a"},
			"không phải dict",
			{"kind": "loai-la"},
			{"kind": "chan", "message": "x"},
		])
		self.assertEqual(kq["nhan"], 2)
		self.assertEqual(kq["bo_qua"], 2)

	def test_TAT_cong_tac_thi_khong_ghi_gi(self):
		self._bat(0)
		kq = su_kien.ghi_lo(project=DU_AN, events=[{"kind": "dung", "screen_id": "#/a"}])
		self.assertTrue(kq.get("tat"))
		self.assertEqual(frappe.db.count("Feedback Event", {"project": DU_AN}), 0)

	def test_chu_ky_va_dau_hieu_tinh_o_MAY_CHU(self):
		"""Trình duyệt chỉ gửi câu nguyên văn — chữ ký là việc của máy chủ (một luật, một bản)."""
		su_kien.ghi_lo(project=DU_AN, events=[
			{"kind": "chan", "message": "[KHACCUON] Băng A-B1 của cuộn A", "endpoint": "ep"},
			{"kind": "chan", "message": "[KHACCUON] Băng Z-B9 của cuộn Z", "endpoint": "ep"},
		])
		ds = frappe.get_all("Feedback Event", filters={"project": DU_AN}, fields=["signature", "marker"])
		self.assertEqual(len({d.signature for d in ds}), 1)
		self.assertEqual({d.marker for d in ds}, {"KHACCUON"})
