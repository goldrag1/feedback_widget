"""`status_changed_at` là mốc mà mục "Hồi quy" dựa vào — sai mốc là báo hồi quy giả."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

DU_AN = "kiemthu-moc"


class TestMocDoiTrangThai(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Feedback Comment", {"project": DU_AN})
		frappe.db.commit()

	def tearDown(self):
		frappe.db.delete("Feedback Comment", {"project": DU_AN})
		frappe.db.commit()

	def _ve(self, **kw):
		d = {"doctype": "Feedback Comment", "project": DU_AN, "message": "kiểm thử",
		     "source": "auto", "status": "New", "screen_id": "viec-nen",
		     "screen_name": "Việc nền · kiểm thử", "submitter": "(máy chủ)"}
		d.update(kw)
		return frappe.get_doc(d).insert(ignore_permissions=True)

	def test_luc_TAO_lay_dong_ho_MAY_CHU_chu_khong_lay_ts_cua_trinh_duyet(self):
		"""`ts` do trình duyệt gửi là giờ UTC — sớm hơn sổ sự kiện 7 tiếng trên site VN."""
		ve = self._ve(ts=add_to_date(now_datetime(), hours=-7))
		lech = abs((ve.status_changed_at - now_datetime()).total_seconds())
		self.assertLess(lech, 120, f"mốc lấy theo ts của trình duyệt: {ve.status_changed_at}")

	def test_doi_trang_thai_qua_DOC_thi_moc_nhay_theo(self):
		ve = self._ve(ts=add_to_date(now_datetime(), hours=-3))
		cu = ve.status_changed_at
		frappe.db.set_value("Feedback Comment", ve.name, "modified",
		                    add_to_date(now_datetime(), hours=-3), update_modified=False)
		ve.reload()
		ve.status = "Resolved"
		ve.save(ignore_permissions=True)
		self.assertGreater(ve.status_changed_at, cu, "đóng vé mà mốc không nhảy")

	def test_db_set_value_KHONG_dong_dau_duoc_moc(self):
		"""Chốt lý do vì sao đường đóng vé phải đi qua doc: đây là cái bẫy đã cắn 26/08."""
		ve = self._ve()
		cu = frappe.db.get_value("Feedback Comment", ve.name, "status_changed_at")
		frappe.db.set_value("Feedback Comment", ve.name, "status", "Resolved")
		self.assertEqual(frappe.db.get_value("Feedback Comment", ve.name, "status_changed_at"), cu)
