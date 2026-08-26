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
		frappe.db.delete("Feedback Event", {"screen_id": "viec-nen"})
		frappe.db.set_global(tac_vu.MOC, "")
		frappe.db.commit()

	def tearDown(self):
		frappe.db.delete("Feedback Comment", {"screen_id": "viec-nen"})
		frappe.db.delete("Feedback Event", {"screen_id": "viec-nen"})
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

	def test_cau_va_khai_thac_gom_CUNG_MOT_KHOA(self):
		"""Bộ gom của cầu và chữ ký của hộp thư phải là MỘT.

		Cầu gom theo (câu lỗi, method); `collect` tính chữ ký theo (thông điệp, endpoint).
		Không truyền `endpoint` thì hai bên gom khác nhau: một sự cố ra hai vé và cột
		"bao nhiêu lần" nói sai — đo trên prod 25/08, nhóm 18 lần bị tách thành 2 và 16.
		"""
		import inspect

		for ham in (tac_vu.bac_cau_error_log, tac_vu.khai_thac_lich_su):
			src = inspect.getsource(ham)
			self.assertIn('"endpoint"', src,
				f"{ham.__name__} không khai endpoint ⇒ chữ ký lệch khoá gom")

	def test_cau_ghi_ca_SO_chu_khong_chi_de_ve(self):
		"""Bảng xếp hạng đọc `Feedback Event`; vé không đếm được nhịp.

		Đo prod 25-26/08: 15 lần việc nền hỏng, 0 dòng sổ ⇒ "chỗ tắc" của xưởng bằng 0
		trong khi xưởng đứng hình.
		"""
		tac_vu.bac_cau_error_log()
		self._log(NGOAI_LE, method="viec_nen hoan_thanh_cong_doan")
		kq = tac_vu.bac_cau_error_log()
		self.assertEqual(kq["ve"], 1)
		self.assertEqual(kq["su_kien"], 1)
		e = frappe.get_all("Feedback Event", filters={"screen_id": "viec-nen"},
		                   fields=["kind", "marker", "endpoint", "signature", "user", "ts"])
		self.assertEqual(len(e), 1)
		# `frappe.throw` = luật nghiệp vụ chạy đúng → `chan`, không phải `loi`.
		self.assertEqual(e[0].kind, "chan")
		self.assertEqual(e[0].marker, "XINDUYET")
		self.assertEqual(e[0].endpoint, "viec_nen hoan_thanh_cong_doan")
		self.assertTrue(e[0].signature)

	def test_lop_loi_KHAC_frappe_thi_la_loi_chu_khong_phai_chan(self):
		self.assertEqual(tac_vu._loai_su_kien("frappe.exceptions.PermissionError: chưa duyệt"), "chan")
		self.assertEqual(tac_vu._loai_su_kien("builtins.TypeError: 'str' object is not callable"), "loi")
		self.assertEqual(tac_vu._loai_su_kien("MySQLdb.OperationalError: (1054, 'Unknown column')"), "loi")

	def test_KHONG_ghi_hai_dong_cho_mot_su_co_da_co_tren_so(self):
		"""Lỗi 500 của đường đồng bộ vào CẢ Error Log lẫn sổ (widget báo từ trình duyệt).

		Ghi cả hai là một sự cố hoá hai dòng — con số "bao nhiêu lần" phồng theo hướng
		nguy hiểm nhất là hướng làm to.
		"""
		tac_vu.bac_cau_error_log()
		self._log(NGOAI_LE, method="viec_nen hoan_thanh_cong_doan")
		r = frappe.db.get_value("Error Log", {"method": "viec_nen hoan_thanh_cong_doan"},
		                        ["name", "creation"], as_dict=True, order_by="creation desc")
		cau = tac_vu._cau_cuoi(NGOAI_LE)
		frappe.get_doc({
			"doctype": "Feedback Event", "project": tac_vu._du_an(), "kind": "chan",
			"ts": r.creation, "user": "Administrator", "screen_id": "viec-nen",
			"endpoint": "viec_nen hoan_thanh_cong_doan", "message": cau,
			"signature": tac_vu._tinh_chu_ky(cau, "viec_nen hoan_thanh_cong_doan", "chan"),
		}).insert(ignore_permissions=True)
		frappe.db.commit()
		kq = tac_vu.bac_cau_error_log()
		self.assertEqual(kq["su_kien"], 0, "đã có dòng cùng chữ ký trong ±2 phút mà vẫn ghi thêm")
		self.assertEqual(frappe.db.count("Feedback Event", {"screen_id": "viec-nen"}), 1)
