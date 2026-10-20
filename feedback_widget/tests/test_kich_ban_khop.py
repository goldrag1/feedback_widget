"""Luật khớp bước — MỘT định nghĩa ở kich_ban.py (spec §4.4)."""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget import kich_ban as kb
from feedback_widget.tests import _kich_ban_chung as c

MOC = "2026-10-19 08:00:00"


def buoc(**kw):
	d = {"chang": "lam-quen", "mo_ta": "thử", "so_lan": 1, "so_ngay": 1}
	d.update(kw)
	return frappe._dict(d)


class TestKichBanKhop(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		c.nguoi(c.NGUOI_A); c.nguoi(c.NGUOI_B)
		frappe.db.commit()

	def setUp(self):
		c.don_dep()

	def tearDown(self):
		c.don_dep()

	def test_mau_like(self):
		self.assertEqual(kb.mau_like("Form/X/*"), "Form/X/%")
		self.assertEqual(kb.mau_like("a_b%c"), "a\\_b\\%c")

	def test_mo_man_va_moc(self):
		b = buoc(loai="Mở màn")
		c.su_kien(c.NGUOI_A, "chot-ton", c.sau(MOC, hours=-1))
		self.assertFalse(kb.buoc_dat(b, "chot-ton", c.NGUOI_A, MOC), "sự kiện trước mốc không tính")
		c.su_kien(c.NGUOI_A, "chot-ton", c.sau(MOC, hours=1))
		self.assertTrue(kb.buoc_dat(b, "chot-ton", c.NGUOI_A, MOC))
		self.assertFalse(kb.buoc_dat(b, "chot-ton", c.NGUOI_B, MOC), "người khác không tính")

	def test_mau_sao_khop_form(self):
		c.su_kien(c.NGUOI_A, "Form/Doi Soat Cong No NCC/DSNCC-1", c.sau(MOC, hours=1))
		self.assertTrue(kb.buoc_dat(buoc(loai="Mở màn"), "Form/Doi Soat Cong No NCC/*", c.NGUOI_A, MOC))

	def test_gach_duoi_khong_la_ky_tu_bat_ky(self):
		c.su_kien(c.NGUOI_A, "chotXton", c.sau(MOC, hours=1))
		self.assertFalse(kb.buoc_dat(buoc(loai="Mở màn"), "chot_ton", c.NGUOI_A, MOC))

	def test_bam_nut_can_ok(self):
		b = buoc(loai="Bấm nút", nut="hop-thu::+ Tạo đơn mua")
		c.su_kien(c.NGUOI_A, "hop-thu", c.sau(MOC, hours=1), action_id="hop-thu::+ Tạo đơn mua", outcome="loi")
		self.assertFalse(kb.buoc_dat(b, "hop-thu", c.NGUOI_A, MOC))
		c.su_kien(c.NGUOI_A, "hop-thu", c.sau(MOC, hours=2), action_id="hop-thu::+ Tạo đơn mua", outcome="ok")
		self.assertTrue(kb.buoc_dat(b, "hop-thu", c.NGUOI_A, MOC))

	def test_goi_may_chu_chap_nhan_chan(self):
		ep = "my_custom_app.my_custom_app.chot_ton.create"
		c.su_kien(c.NGUOI_A, "chot-ton", c.sau(MOC, hours=1), kind="chan", endpoint=ep, outcome="chan",
		          message="Tại thời điểm chốt, mọi mặt hàng đã đếm đều khớp sổ — không cần ghi phiếu.")
		self.assertFalse(kb.buoc_dat(buoc(loai="Gọi máy chủ", endpoint=ep), "chot-ton", c.NGUOI_A, MOC))
		self.assertTrue(kb.buoc_dat(buoc(loai="Gọi máy chủ", endpoint=ep, chap_nhan_chan="đều khớp sổ"),
		                            "chot-ton", c.NGUOI_A, MOC))

	def test_tao_chung_tu(self):
		frappe.set_user(c.NGUOI_A)
		try:
			frappe.get_doc({"doctype": "ToDo", "description": c.TIEN_TO + "todo"}).insert(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")
		self.assertTrue(kb.buoc_dat(buoc(loai="Tạo chứng từ", doctype_ct="ToDo", docstatus_toi_thieu="0"),
		                            "x", c.NGUOI_A, MOC))
		self.assertFalse(kb.buoc_dat(buoc(loai="Tạo chứng từ", doctype_ct="ToDo", docstatus_toi_thieu="1"),
		                             "x", c.NGUOI_A, MOC))

	def test_gop_y_tren_man_bo_cam_nhan(self):
		b = buoc(loai="Góp ý trên màn")
		ve = frappe.get_doc({"doctype": "Feedback Comment", "project": c.TIEN_TO + "du-an", "source": "user",
		                     "submitter_user": c.NGUOI_A, "screen_id": "chot-ton", "screen_name": "chot-ton", "message": "👍",
		                     "ts": c.sau(MOC, hours=1), "tu_cam_nhan": 1}).insert(ignore_permissions=True)
		self.assertFalse(kb.buoc_dat(b, "chot-ton", c.NGUOI_A, MOC), "cảm nhận không thỏa bước góp ý")
		ve.db_set("tu_cam_nhan", 0)
		self.assertTrue(kb.buoc_dat(b, "chot-ton", c.NGUOI_A, MOC))

	def test_so_ngay(self):
		b = buoc(loai="Mở màn", so_ngay=3)
		c.su_kien(c.NGUOI_A, "chot-ton", c.sau(MOC, hours=1))
		c.su_kien(c.NGUOI_A, "chot-ton", c.sau(MOC, days=1, hours=1))
		self.assertEqual(kb.dem_buoc(b, "chot-ton", c.NGUOI_A, MOC), (2, 2))
		self.assertFalse(kb.buoc_dat(b, "chot-ton", c.NGUOI_A, MOC))
		c.su_kien(c.NGUOI_A, "chot-ton", c.sau(MOC, days=2, hours=1))
		self.assertTrue(kb.buoc_dat(b, "chot-ton", c.NGUOI_A, MOC))

	def test_kich_ban_cua_man(self):
		k = c.kich_ban("Form/THUKB Doc/*")
		self.assertEqual(kb.kich_ban_cua_man("Form/THUKB Doc/ABC-1"), k.name)
		self.assertIsNone(kb.kich_ban_cua_man("Form/Khac/ABC-1"))
		k.db_set("dang_bat", 0)
		self.assertIsNone(kb.kich_ban_cua_man("Form/THUKB Doc/ABC-1"))
