"""Sổ điểm, cấp, huân chương (spec §8)."""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget import diem
from feedback_widget.tests import _kich_ban_chung as c


class TestKichBanDiem(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		c.nguoi(c.NGUOI_A)
		frappe.db.commit()

	def setUp(self):
		c.don_dep()

	def tearDown(self):
		c.don_dep()

	def test_khong_cong_doi(self):
		self.assertTrue(diem.ghi_diem(c.NGUOI_A, 10, "Bước", "THU|k1"))
		self.assertFalse(diem.ghi_diem(c.NGUOI_A, 10, "Bước", "THU|k1"))
		self.assertEqual(diem.tong_diem(c.NGUOI_A), 10)

	def test_bat_tat_thu_hoi(self):
		k = "Góp ý có ích|FB-THU|" + c.NGUOI_A
		self.assertEqual(diem.dat_diem(c.NGUOI_A, 20, "Góp ý có ích", k, True), 20)
		self.assertEqual(diem.dat_diem(c.NGUOI_A, 20, "Góp ý có ích", k, True), 0, "bật lại không cộng thêm")
		self.assertEqual(diem.dat_diem(c.NGUOI_A, 20, "Góp ý có ích", k, False), -20)
		self.assertEqual(diem.dat_diem(c.NGUOI_A, 20, "Góp ý có ích", k, False), 0, "tắt lại không trừ thêm")
		self.assertEqual(diem.tong_diem(c.NGUOI_A), 0)
		self.assertEqual(diem.dat_diem(c.NGUOI_A, 20, "Góp ý có ích", k, True), 20, "bật lần hai được cấp lại")
		self.assertEqual(diem.tong_diem(c.NGUOI_A), 20)
		self.assertFalse(diem.thu_hoi("khong-co"))
		self.assertTrue(diem.thu_hoi(k))
		self.assertEqual(diem.tong_diem(c.NGUOI_A), 0)

	def test_cap(self):
		self.assertEqual(diem.cap(99), "Tập sự")
		self.assertEqual(diem.cap(100), "Thành thạo")
		self.assertEqual(diem.cap(300), "Key user")
		self.assertEqual(diem.cap(700), "Đại sứ chuyển đổi số")
		self.assertEqual(diem.nguong_ke(150), 300)
		self.assertIsNone(diem.nguong_ke(900))

	def test_chua_bao_va_len_cap(self):
		diem.ghi_diem(c.NGUOI_A, 90, "Bước", "THU|a")
		diem.danh_dau_da_bao(c.NGUOI_A)
		diem.ghi_diem(c.NGUOI_A, 20, "Chặng", "THU|b")
		diem.trao(c.NGUOI_A, "mo-duong", "THU|mo-duong")
		cb = diem.chua_bao(c.NGUOI_A)
		self.assertEqual([d.diem for d in cb["diem"]], [20])
		self.assertEqual(cb["huan_chuong"][0]["ten"], "🚀 Người mở đường")
		self.assertEqual((cb["cap_truoc"], cb["cap_sau"]), ("Tập sự", "Thành thạo"))
		diem.danh_dau_da_bao(c.NGUOI_A)
		cb = diem.chua_bao(c.NGUOI_A)
		self.assertEqual((cb["diem"], cb["huan_chuong"], cb["cap_truoc"]), ([], [], "Thành thạo"))

	def _diem_tuan_truoc(self, n):
		for i in range(n):
			k = f"THU|tuan{i}"
			diem.ghi_diem(c.NGUOI_A, 5, "Bước", k)
			frappe.db.sql("UPDATE `tabFeedback Point` SET creation = %s WHERE khoa = %s",
			              (c.sau("2026-10-14 10:00:00", days=-7 * i), k))

	def test_chuyen_can(self):
		self._diem_tuan_truoc(3)
		diem.kiem_huan_chuong_ngay("2026-10-15 10:00:00")
		self.assertEqual(diem.huan_chuong_cua(c.NGUOI_A), {}, "3 tuần chưa đủ")
		self._diem_tuan_truoc(4)
		diem.kiem_huan_chuong_ngay("2026-10-15 10:00:00")
		diem.kiem_huan_chuong_ngay("2026-10-16 10:00:00")
		self.assertEqual(diem.huan_chuong_cua(c.NGUOI_A), {"chuyen-can": 1}, "4 tuần ⇒ một lần, chạy lại không trao thêm")


def tearDownModule():
	frappe.set_user("Administrator")
	c.xoa_nguoi()
