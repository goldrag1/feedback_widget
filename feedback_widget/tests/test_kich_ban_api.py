"""API kịch bản màn cho widget (spec §5, §6)."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from feedback_widget import diem
from feedback_widget.api import kich_ban as api
from feedback_widget.tests import _kich_ban_chung as c

MAN = "thukb-api"


class TestKichBanApi(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		c.nguoi(c.NGUOI_A); c.nguoi(c.NGUOI_B)
		cls.cu = c.dat_cai_dat(kb_bat=1)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		c.dat_cai_dat(**cls.cu)
		super().tearDownClass()

	def setUp(self):
		frappe.set_user("Administrator")
		c.don_dep()
		self.k = c.kich_ban(MAN, huong_dan=[{"thu_tu": 1, "tieu_de": "Chọn kho", "noi_dung": "Chọn kho ở đây",
		                                      "chi_vao": "#kho"}],
		                    buoc=[{"chang": "lam-quen", "mo_ta": "Mở", "loai": "Mở màn"}])

	def tearDown(self):
		frappe.set_user("Administrator")
		c.don_dep()

	def test_tu_bat_huong_dan_nguoi_moi_nhung_khong_nguoi_da_quen(self):
		frappe.set_user(c.NGUOI_A)
		r = api.cua_toi(MAN, phien="p-now")
		self.assertTrue(r["huong_dan"]["tu_bat"])
		frappe.set_user("Administrator")
		for i in range(3):
			c.su_kien(c.NGUOI_B, MAN, add_to_date(now_datetime(), days=-3 + i), session_id=f"cu{i}")
		frappe.set_user(c.NGUOI_B)
		r = api.cua_toi(MAN, phien="p-now")
		self.assertFalse(r["huong_dan"]["tu_bat"], "đã quen màn (3 phiên trước) thì không tự bật")
		self.assertFalse(r["chang"][0]["xong"], "sự kiện TRƯỚC mốc tiến độ không tính bước")
		frappe.set_user("Administrator")
		c.su_kien(c.NGUOI_B, MAN, add_to_date(now_datetime(), seconds=1), session_id="p-now")
		frappe.set_user(c.NGUOI_B)
		self.assertTrue(api.cua_toi(MAN, phien="p-now")["chang"][0]["xong"])

	def test_khong_co_kich_ban_va_tat(self):
		frappe.set_user(c.NGUOI_A)
		self.assertIsNone(api.cua_toi("man-khac")["kich_ban"])
		frappe.set_user("Administrator")
		c.dat_cai_dat(kb_bat=0)
		try:
			frappe.set_user(c.NGUOI_A)
			self.assertIsNone(api.cua_toi(MAN))
			self.assertIsNone(api.bang_vang())
		finally:
			frappe.set_user("Administrator")
			c.dat_cai_dat(kb_bat=1)

	def test_cam_nhan_thich_khong_tao_gop_y(self):
		frappe.set_user(c.NGUOI_A)
		api.cua_toi(MAN)
		r = api.cam_nhan(self.k.name, "lam-quen", "👍")
		self.assertIsNone(r["ve"])
		api.cam_nhan(self.k.name, "lam-quen", "👍")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.count("Feedback Point", {"user": c.NGUOI_A, "ly_do": "Cảm nhận"}), 1)
		self.assertFalse(frappe.db.exists("Feedback Comment", {"submitter_user": c.NGUOI_A}))

	def test_cam_nhan_che_tao_gop_y_khong_thoa_buoc(self):
		frappe.set_user(c.NGUOI_A)
		r = api.cam_nhan(self.k.name, "lam-quen", "👎", "chậm quá", screen_id=MAN)
		frappe.set_user("Administrator")
		self.assertTrue(r["ve"])
		self.assertEqual(frappe.db.get_value("Feedback Comment", r["ve"], "tu_cam_nhan"), 1)

	def test_bang_vang(self):
		diem.ghi_diem(c.NGUOI_A, 40, "Bước", "THU|bv-a")
		diem.ghi_diem(c.NGUOI_B, 10, "Bước", "THU|bv-b")
		diem.ghi_diem(c.NGUOI_B, -10, "Thu hồi", "THU|bv-b-th")
		frappe.set_user(c.NGUOI_A)
		r = api.bang_vang(cong_ty="__all__")
		ten = [h["ten"] for h in r["hang"]]
		self.assertIn("thu-kb-a", ten)
		self.assertNotIn("thu-kb-b", ten, "0 điểm không lên bảng")
		self.assertNotIn("@", str(r), "không lộ email")
		self.assertNotIn("Administrator", ten)

	def test_thanh_tich(self):
		frappe.set_user(c.NGUOI_A)
		api.cua_toi(MAN)
		r = api.thanh_tich()
		self.assertEqual(r["cap"], "Tập sự")
		self.assertEqual(r["kich_ban"][0]["ten"], self.k.ten)
