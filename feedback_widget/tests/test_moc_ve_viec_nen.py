"""Vé do cầu Error Log dựng phải mang MỐC LÚC LỖI XẢY RA.

Ca thật 27/08/2026 trên site demo: ba dòng lỗi `misa_voucher_no` xảy ra lúc 07:00–07:15,
nhưng cầu chạy lần đầu lúc 17:15 (ngay sau khi bật sổ trên site ấy) nên vé ghi 17:15 —
và tôi đã báo chủ đầu tư "hai vé máy vừa lộ lúc 17:15" rồi phải đính chính: lỗi ấy đã được
phiên khác vá xong từ 08:20. Người đọc vé không có cách nào tự biết sai lệch đó.

Sổ THÔ đã đúng từ đầu (`_ghi_su_kien_nen` ghi `ts = r.creation`); chỉ vé bị lệch, vì
`collect` tự đóng dấu `now()` khi không ai truyền `ts`. Test khoá cả hai đầu.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from feedback_widget import tac_vu


class TestMocVeViecNen(FrappeTestCase):
	def setUp(self):
		self.cu = frappe.db.get_global(tac_vu.MOC)
		self.moc_loi = add_to_date(now_datetime(), hours=-9)

	def tearDown(self):
		# Trả lại ĐÚNG trạng thái cũ. `set_global(MOC, None)` KHÔNG phải là "xoá": nó ghi
		# chuỗi "None", rồi `_moc_da_doc()` trả chuỗi ấy và câu SQL `creation > 'None'`
		# khớp 0 dòng — cầu im lặng không đọc gì nữa. Đo được khi chạy CẢ BỘ: module này
		# xanh khi chạy riêng nhưng làm `test_cau_error_log` đỏ ({'doc': 0, 've': 0}),
		# đúng lớp lỗi "bộ test để lại trạng thái chung" mà chính tôi hay nhắc.
		if self.cu is None:
			frappe.db.sql("DELETE FROM `tabDefaultValue` WHERE defkey=%s AND parent='__default'",
			              (tac_vu.MOC,))
			frappe.cache.delete_key("defaults")
		else:
			frappe.db.set_global(tac_vu.MOC, self.cu)
		for dt, f in (("Feedback Comment", {"message": ["like", "%THU MOC VIEC NEN%"]}),
		              ("Feedback Event", {"message": ["like", "%THU MOC VIEC NEN%"]}),
		              ("Error Log", {"error": ["like", "%THU MOC VIEC NEN%"]})):
			for n in frappe.get_all(dt, filters=f, pluck="name"):
				frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
		frappe.db.commit()

	def _dung_error_log_cu(self):
		"""Một dòng Error Log của 9 TIẾNG TRƯỚC — đúng hình dạng ca thật."""
		e = frappe.get_doc({"doctype": "Error Log", "method": "thu.viec_nen.chay",
		                    "error": "Traceback\nValueError: THU MOC VIEC NEN"}).insert(ignore_permissions=True)
		frappe.db.set_value("Error Log", e.name, "creation", self.moc_loi, update_modified=False)
		frappe.db.commit()
		return frappe.get_doc("Error Log", e.name)

	def test_ve_va_su_kien_deu_mang_moc_luc_LOI_XAY_RA(self):
		e = self._dung_error_log_cu()
		frappe.db.set_global(tac_vu.MOC, str(add_to_date(self.moc_loi, minutes=-5)))
		kq = tac_vu.bac_cau_error_log()
		self.assertGreaterEqual(kq.get("ve", 0), 1, f"cầu không dựng vé nào: {kq}")

		ve = frappe.get_all("Feedback Comment", filters={"message": ["like", "%THU MOC VIEC NEN%"]},
		                    fields=["name", "ts", "creation"])
		self.assertEqual(len(ve), 1)
		lech = abs((ve[0].ts - self.moc_loi).total_seconds())
		self.assertLess(lech, 120,
		                f"vé mang mốc {ve[0].ts} trong khi lỗi xảy ra {self.moc_loi} — lệch {lech/3600:.1f} giờ")

		sk = frappe.get_all("Feedback Event", filters={"message": ["like", "%THU MOC VIEC NEN%"]},
		                    fields=["ts"])
		self.assertTrue(sk, "sổ thô không có dòng nào")
		self.assertLess(abs((sk[0].ts - self.moc_loi).total_seconds()), 120)

	def test_khong_truyen_ts_thi_van_la_bay_gio(self):
		"""Đường của người dùng gõ vé KHÔNG được đổi: thiếu `ts` thì vẫn đóng dấu hiện tại."""
		from feedback_widget.api.feedback import collect

		frappe.set_user("Administrator")
		r = collect(project="thu", screen_id="#/x", screen_name="thu",
		            message="THU MOC VIEC NEN — nguoi go", source="user")
		ten = r.get("name") if isinstance(r, dict) else None
		self.assertTrue(ten)
		ts = frappe.db.get_value("Feedback Comment", ten, "ts")
		self.assertLess(abs((ts - now_datetime()).total_seconds()), 120)
