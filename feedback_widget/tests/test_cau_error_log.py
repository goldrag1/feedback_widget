"""Cầu Error Log → hộp thư: chỉ NGOẠI LỆ, và lần đầu KHÔNG đọc ngược lịch sử."""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget import tac_vu

NGOAI_LE = ("Traceback (most recent call last):\n  File \"x.py\", line 1\n"
            "frappe.exceptions.ValidationError: [XINDUYET] Cân không khớp — NL vào 1.650 kg")
NHAT_KY = "Repack · [OUTPUT:XB-2026-4171:Xả băng] Nhập kho kết quả Xả băng"


class TestCauErrorLog(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Feedback Comment", {"screen_id": "viec-nen"})
		frappe.db.set_global(tac_vu.MOC, "")
		frappe.db.commit()

	def tearDown(self):
		frappe.db.delete("Feedback Comment", {"screen_id": "viec-nen"})
		frappe.db.commit()

	def _log(self, noi_dung, method="kiemthu viec_nen"):
		frappe.get_doc({"doctype": "Error Log", "method": method,
		                "error": noi_dung}).insert(ignore_permissions=True)
		frappe.db.commit()

	def test_lan_dau_KHONG_doc_nguoc_lich_su(self):
		"""Bật một tính năng ghi sổ không được đổ hàng trăm vé cũ vào hộp thư người trực."""
		self._log(NGOAI_LE)              # có sẵn TRƯỚC khi mốc được đặt
		frappe.db.set_global(tac_vu.MOC, "")
		tac_vu.bac_cau_error_log()
		self.assertEqual(frappe.db.count("Feedback Comment", {"screen_id": "viec-nen"}), 0)

	def test_chi_bac_cau_NGOAI_LE_chu_khong_bac_nhat_ky(self):
		tac_vu.bac_cau_error_log()       # đặt mốc = bây giờ
		self._log(NHAT_KY)
		self._log(NGOAI_LE)
		kq = tac_vu.bac_cau_error_log()
		self.assertEqual(kq["ve"], 1)
		ve = frappe.get_all("Feedback Comment", filters={"screen_id": "viec-nen"},
		                    fields=["marker", "source"])
		self.assertEqual(len(ve), 1)
		self.assertEqual(ve[0].marker, "XINDUYET")
		self.assertEqual(ve[0].source, "auto")

	def test_chay_lai_KHONG_nhan_doi_ve(self):
		tac_vu.bac_cau_error_log()
		self._log(NGOAI_LE)
		tac_vu.bac_cau_error_log()
		tac_vu.bac_cau_error_log()
		self.assertEqual(frappe.db.count("Feedback Comment", {"screen_id": "viec-nen"}), 1)

	def test_khai_thac_lich_su_mac_dinh_CHAY_THU(self):
		"""Trình khai thác lịch sử mà mặc định GHI là cách tạo 200 vé trong hộp thư người khác."""
		self._log(NGOAI_LE)
		kq = tac_vu.khai_thac_lich_su(so_ngay=1)
		self.assertTrue(kq["chay_thu"])
		self.assertNotIn("ve", kq)
		self.assertEqual(frappe.db.count("Feedback Comment", {"screen_id": "viec-nen"}), 0)
