"""Thông báo đẩy: đúng người nhận, đúng một lần, và cảm ơn người báo.

Ba tính chất phải đúng trước khi nối dây vào giao diện:
 1. người ngoài phạm vi KHÔNG nhận được (gửi nhầm một lần là người ta tắt luôn widget);
 2. đã xem thì thôi hiện lại, và "đã bấm" đo được (0 lượt bấm = sai người hoặc sai lời);
 3. thông báo sinh ra từ một vé BẮT BUỘC ghi tên người được cảm ơn.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget.api import thong_bao

NGUOI_A = "thu-tb-a@kiemthu.local"
NGUOI_B = "thu-tb-b@kiemthu.local"
VAI = "Thu Vai Thong Bao"


def _nguoi(email):
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0],
		                "send_welcome_email": 0}).insert(ignore_permissions=True)
	return email


class TestThongBaoDay(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		_nguoi(NGUOI_A); _nguoi(NGUOI_B)
		if not frappe.db.exists("Role", VAI):
			frappe.get_doc({"doctype": "Role", "role_name": VAI}).insert(ignore_permissions=True)
		frappe.db.commit()

	def setUp(self):
		frappe.set_user("Administrator")
		for u in (NGUOI_A, NGUOI_B):
			frappe.db.delete("Has Role", {"parent": u, "role": VAI})
		frappe.clear_cache()
		frappe.db.commit()

	def tearDown(self):
		for u in (NGUOI_A, NGUOI_B):
			frappe.db.delete("Has Role", {"parent": u, "role": VAI})
		for n in frappe.get_all("Feedback Notice", filters={"tieu_de": ["like", "THU-%"]}, pluck="name"):
			frappe.db.delete("Feedback Notice Seen", {"thong_bao": n})
			frappe.delete_doc("Feedback Notice", n, force=True, ignore_permissions=True)
		frappe.db.commit()

	def _tao(self, pham_vi, nguoi=None, vai=None, ve=None, cam_on=None):
		d = frappe.get_doc({
			"doctype": "Feedback Notice", "tieu_de": "THU-thong-bao",
			"noi_dung": "Thẻ việc nay hiện KL còn lại.", "duong_dan": "#/viec-cua-toi",
			"pham_vi": pham_vi, "nguon_ve": ve, "cam_on_ai": cam_on,
			"cac_nguoi": [{"user": u} for u in (nguoi or [])],
			"cac_vai": [{"role": r} for r in (vai or [])],
		})
		d.insert(ignore_permissions=True)
		frappe.db.commit()
		return d

	def test_mot_nguoi_thi_nguoi_khac_khong_nhan(self):
		self._tao("Một người", nguoi=[NGUOI_A])
		self.assertEqual(len(thong_bao._cua_toi(NGUOI_A)), 1)
		self.assertEqual(thong_bao._cua_toi(NGUOI_B), [], "người ngoài phạm vi vẫn nhận được")

	def test_nhom_vai_theo_vai_that(self):
		self._tao("Nhóm vai", vai=[VAI])
		self.assertEqual(thong_bao._cua_toi(NGUOI_A), [], "chưa có vai mà đã nhận")
		u = frappe.get_doc("User", NGUOI_A)
		u.append("roles", {"role": VAI})
		u.save(ignore_permissions=True)
		frappe.db.commit()
		self.assertEqual(len(thong_bao._cua_toi(NGUOI_A)), 1, "có vai rồi vẫn không nhận")

	def test_da_xem_thi_thoi_hien_va_dem_duoc_luot_bam(self):
		d = self._tao("Một người", nguoi=[NGUOI_A])
		frappe.set_user(NGUOI_A)
		try:
			thong_bao.da_xem(d.name, da_bam=1)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(thong_bao._cua_toi(NGUOI_A), [], "đã xem rồi vẫn hiện lại")
		self.assertEqual(thong_bao.dem_da_xem(d.name), {"da_xem": 1, "da_bam": 1})

	def test_sinh_tu_ve_thi_phai_co_loi_cam_on(self):
		ve = frappe.get_doc({"doctype": "Feedback Comment", "message": "THU-ve",
		                     "screen_id": "thu", "screen_name": "THU màn",
		                     "ts": frappe.utils.now_datetime(), "project": "thu",
		                     "submitter_user": NGUOI_A}).insert(ignore_permissions=True)
		frappe.db.commit()
		try:
			d = self._tao("Một người", nguoi=[NGUOI_A], ve=ve.name)
			# Người báo có họ tên → tự điền, không bắt người soạn gõ lại.
			self.assertTrue((d.cam_on_ai or "").strip(),
			                "thông báo từ vé mà không cảm ơn ai — đúng thứ làm người ta thôi gõ vé")
		finally:
			frappe.delete_doc("Feedback Comment", ve.name, force=True, ignore_permissions=True)
			frappe.db.commit()
