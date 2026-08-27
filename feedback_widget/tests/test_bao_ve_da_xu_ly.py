"""Vé người gõ được xử lý ⇒ TỰ ĐỘNG có thẻ báo cho chính người ấy.

Đo trên site thật 26/08/2026: 93 vé người gõ trong 60 ngày, 74 vé Resolved, 0 lượt báo
ngược. Việc báo tay luôn là thứ rơi ra khỏi danh sách khi cuối ngày bận, nên nó phải nằm
ở đường GHI (`Feedback Comment.on_update`), không nằm trong trí nhớ ai cả.

Test chạy trên site thật của bench (FrappeTestCase) và dọn sạch thứ nó dựng.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget.bao_ve_da_xu_ly import bao_ve_da_xu_ly, can_bao, dang_bat

NGUOI = "thu-bao-ve@example.com"


def _dung_user():
	if not frappe.db.exists("User", NGUOI):
		frappe.get_doc({"doctype": "User", "email": NGUOI, "first_name": "Thử Báo Vé",
		                "send_welcome_email": 0}).insert(ignore_permissions=True)


def _dung_ve(**kw):
	d = {"doctype": "Feedback Comment", "message": "Ô cân thực bị cắt mất trên điện thoại",
	     "status": "New", "source": "user", "screen_id": "#/viec-cua-toi",
	     "screen_name": "steel-app", "project": "kiem-thu-bao-ve"}
	d.update(kw)
	ve = frappe.get_doc(d)
	ve.insert(ignore_permissions=True)
	frappe.db.set_value("Feedback Comment", ve.name, "owner", kw.pop("_owner", NGUOI),
	                    update_modified=False)
	return frappe.get_doc("Feedback Comment", ve.name)


class TestBaoVeDaXuLy(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_dung_user()

	def tearDown(self):
		for tb in frappe.get_all("Feedback Notice", filters={"cam_on_ai": NGUOI}, pluck="name"):
			frappe.delete_doc("Feedback Notice", tb, force=True, ignore_permissions=True)
		for ve in frappe.get_all("Feedback Comment", filters={"owner": NGUOI}, pluck="name"):
			frappe.delete_doc("Feedback Comment", ve, force=True, ignore_permissions=True)
		frappe.db.commit()

	def test_dong_ve_thi_TU_DONG_co_the_bao_cho_nguoi_go(self):
		ve = _dung_ve()
		ve.status = "Resolved"
		ve.status_note = "Đã sửa: bảng nay vừa màn, ô cân thực gõ được."
		ve.save(ignore_permissions=True)          # đi qua chính đường ghi thật
		tb = frappe.get_all("Feedback Notice", filters={"nguon_ve": ve.name},
		                    fields=["name", "pham_vi", "noi_dung", "duong_dan", "cam_on_ai"])
		self.assertEqual(len(tb), 1, "đóng vé mà không có thẻ báo nào được dựng")
		self.assertEqual(tb[0].pham_vi, "Một người")
		self.assertEqual(tb[0].cam_on_ai, NGUOI)
		self.assertIn("ô cân thực gõ được", tb[0].noi_dung)
		self.assertEqual(tb[0].duong_dan, "#/viec-cua-toi")
		nhan = frappe.get_all("Feedback Notice User", filters={"parent": tb[0].name}, pluck="user")
		self.assertEqual(nhan, [NGUOI])

	def test_ly_do_lay_duoc_tu_COMMENT_khi_khong_co_status_note(self):
		"""Script đóng vé ghi lý do bằng add_comment — đọc mỗi status_note là mất nửa số ca."""
		ve = _dung_ve()
		ve.status = "Resolved"
		ve.save(ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Feedback Notice", {"nguon_ve": ve.name}),
		                 "chưa có lý do thì KHÔNG báo — thẻ rỗng là tiếng ồn")
		ve.add_comment("Comment", "Đã vá và đo lại trên máy chủ: hết cắt cột.")
		ve.reload()
		self.assertEqual(bao_ve_da_xu_ly(ve) is not None, True)
		tb = frappe.get_all("Feedback Notice", filters={"nguon_ve": ve.name}, fields=["noi_dung"])
		self.assertIn("hết cắt cột", tb[0].noi_dung)

	def test_KHONG_bao_ve_may_va_KHONG_bao_hai_lan(self):
		may = _dung_ve(source="auto", message="ReferenceError: x is not defined")
		may.status = "Resolved"
		may.status_note = "Đã vá."
		may.save(ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Feedback Notice", {"nguon_ve": may.name}))

		ve = _dung_ve()
		ve.status = "Resolved"
		ve.status_note = "Đã sửa."
		ve.save(ignore_permissions=True)
		self.assertEqual(frappe.db.count("Feedback Notice", {"nguon_ve": ve.name}), 1,
		                 "đường ghi phải dựng đúng MỘT thẻ")
		ve.reload()
		self.assertIsNone(bao_ve_da_xu_ly(ve), "gọi lần hai phải KHÔNG dựng thẻ thứ hai")
		self.assertEqual(frappe.db.count("Feedback Notice", {"nguon_ve": ve.name}), 1)

	def test_wontfix_cung_duoc_bao(self):
		"""Im lặng với người bị từ chối là cách chắc nhất để lần sau họ không gõ vé nữa."""
		ve = _dung_ve()
		ve.status = "Wontfix"
		ve.status_note = "Việc này ERPNext làm sẵn ở màn khác — em chỉ dẫn anh/chị đường."
		ve.save(ignore_permissions=True)
		tb = frappe.get_all("Feedback Notice", filters={"nguon_ve": ve.name}, fields=["tieu_de"])
		self.assertEqual(len(tb), 1)
		self.assertIn("góp ý", tb[0].tieu_de.lower())

	def test_loi_o_khau_bao_KHONG_duoc_lam_hong_luot_dong_ve(self):
		from unittest.mock import patch
		ve = _dung_ve()
		with patch("feedback_widget.bao_ve_da_xu_ly.bao_ve_da_xu_ly", side_effect=RuntimeError("hỏng")):
			ve.status = "Resolved"
			ve.status_note = "Đã sửa."
			ve.save(ignore_permissions=True)      # phải KHÔNG ném
		self.assertEqual(frappe.db.get_value("Feedback Comment", ve.name, "status"), "Resolved")

	def test_cong_tac_THIEU_DONG_van_phai_coi_la_BAT(self):
		"""`get_single_value` trả 0 cho cả "chưa có dòng" lẫn "đã tắt" — dùng nó thì tính
		năng câm ngay trên mọi site đang chạy (field vừa thêm, tabSingles chưa có dòng)."""
		# Bộ test KHÔNG được để lại trạng thái chung: nhớ giá trị cũ rồi trả lại y nguyên,
		# kể cả ca "ban đầu không có dòng nào".
		cu = frappe.db.sql("""SELECT value FROM `tabSingles`
		                      WHERE doctype='Feedback Settings' AND field='tu_dong_bao_ve'""")
		try:
			frappe.db.sql("""DELETE FROM `tabSingles`
			                 WHERE doctype='Feedback Settings' AND field='tu_dong_bao_ve'""")
			self.assertTrue(dang_bat(), "thiếu dòng phải hiểu là BẬT theo mặc định của field")
			frappe.db.sql("""INSERT INTO `tabSingles` (doctype, field, value)
			                 VALUES ('Feedback Settings', 'tu_dong_bao_ve', '0')""")
			self.assertFalse(dang_bat(), "khai 0 thì phải TẮT thật")
		finally:
			frappe.db.sql("""DELETE FROM `tabSingles`
			                 WHERE doctype='Feedback Settings' AND field='tu_dong_bao_ve'""")
			if cu:
				frappe.db.sql("""INSERT INTO `tabSingles` (doctype, field, value)
				                 VALUES ('Feedback Settings', 'tu_dong_bao_ve', %s)""", (cu[0][0],))

	def test_khong_bao_cho_chinh_nguoi_dong_ve(self):
		ve = _dung_ve()
		frappe.db.set_value("Feedback Comment", ve.name, "owner", frappe.session.user,
		                    update_modified=False)
		ve.reload()
		ve.status = "Resolved"
		ve.status_note = "Tự đóng."
		nen, vi_sao = can_bao(ve)
		self.assertFalse(nen, f"đang báo cho chính người vừa đóng vé ({vi_sao})")
