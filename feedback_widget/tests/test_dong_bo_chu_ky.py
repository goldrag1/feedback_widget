"""Vé và sổ phải nối được với nhau — nếu không, mục "Hồi quy" luôn rỗng và không ai biết."""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget.chu_ky import chu_ky
from feedback_widget.patches import v2_dong_bo_chu_ky_ve_va_so as patch

DU_AN = "kiemthu-chuky"
CAU = "[THIEUCAN] Chưa cân đủ đầu ra nên không đối soát được"
EP = "viec_nen hoan_thanh_cong_doan"


class TestDongBoChuKy(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self._don()
		frappe.get_doc({
			"doctype": "Feedback Comment", "project": DU_AN, "message": CAU,
			"source": "auto", "signature": "KHOA-CU-VE", "status": "New",
			"screen_id": "viec-nen", "screen_name": "Việc nền · kiểm thử", "submitter": "(máy chủ)",
			"context": frappe.as_json({"app": {"endpoint": EP}}),
		}).insert(ignore_permissions=True)
		frappe.get_doc({
			"doctype": "Feedback Event", "project": DU_AN, "kind": "chan", "message": CAU,
			"endpoint": EP, "screen_id": "viec-nen", "user": "Administrator",
			"ts": frappe.utils.now_datetime(),
			"signature": "KHOA-CU-SO",
		}).insert(ignore_permissions=True)
		frappe.db.commit()

	def tearDown(self):
		self._don()

	def _don(self):
		frappe.db.delete("Feedback Comment", {"project": DU_AN})
		frappe.db.delete("Feedback Event", {"project": DU_AN})
		frappe.db.commit()

	def _khoa(self):
		return (frappe.db.get_value("Feedback Comment", {"project": DU_AN}, "signature"),
		        frappe.db.get_value("Feedback Event", {"project": DU_AN}, "signature"))

	def test_truoc_khi_va_hai_ben_KHONG_khop(self):
		"""Chốt hiện trạng — nếu ca này xanh mà không cần patch thì patch là thừa."""
		ve, so = self._khoa()
		self.assertNotEqual(ve, so)

	def test_sau_khi_chay_hai_ben_ra_CUNG_khoa(self):
		patch.execute()
		ve, so = self._khoa()
		self.assertEqual(ve, so, "vé và sổ vẫn không nối được")
		self.assertEqual(ve, chu_ky(CAU, EP), "khoá không bằng công thức đang dùng")

	def test_XEM_TRUOC_khong_ghi_gi(self):
		kq = patch.execute(chay_thu=1)
		self.assertEqual(kq["ve"], 1)
		self.assertEqual(kq["so"], 1)
		self.assertEqual(self._khoa(), ("KHOA-CU-VE", "KHOA-CU-SO"))

	def test_chay_lai_lan_hai_KHONG_doi_gi_nua(self):
		patch.execute()
		truoc = self._khoa()
		kq = patch.execute()
		self.assertEqual((kq["ve"], kq["so"]), (0, 0), "chạy lại vẫn ghi = không idempotent")
		self.assertEqual(self._khoa(), truoc)
