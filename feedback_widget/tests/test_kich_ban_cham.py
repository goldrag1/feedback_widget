"""Chấm tiến độ: chặng Một lần theo thứ tự, Duy trì + chuỗi, nhiệm vụ, Người mở đường (spec §5, §8)."""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget import diem, kich_ban as kb
from feedback_widget.tests import _kich_ban_chung as c

MAN = "thukb-cham"
T2 = "2026-10-19 08:00:00"   # thứ Hai


def _kb_hai_chang():
	return c.kich_ban(MAN, chang=[
		{"ma": "lam-quen", "ten": "Làm quen", "thu_tu": 1, "loai": "Một lần"},
		{"ma": "thanh-thao", "ten": "Thành thạo", "thu_tu": 2, "loai": "Một lần"},
	], buoc=[
		{"chang": "lam-quen", "mo_ta": "Mở", "loai": "Mở màn", "so_lan": 1, "so_ngay": 1},
		{"chang": "lam-quen", "mo_ta": "Bấm", "loai": "Bấm nút", "nut": MAN + "::Ghi", "so_lan": 1, "so_ngay": 1},
		{"chang": "thanh-thao", "mo_ta": "Bấm 2 ngày", "loai": "Bấm nút", "nut": MAN + "::Ghi", "so_lan": 1, "so_ngay": 2},
	])


def _kb_duy_tri():
	return c.kich_ban(MAN, chang=[
		{"ma": "hang-ngay", "ten": "Hằng ngày", "thu_tu": 1, "loai": "Duy trì", "chu_ky": "Ngày",
		 "gio_han": "17:00:00", "ngay_lam_viec": "1,2,3,4,5,6"},
	], buoc=[{"chang": "hang-ngay", "mo_ta": "Ghi", "loai": "Bấm nút", "nut": MAN + "::Ghi", "so_lan": 1, "so_ngay": 1}])


class TestKichBanCham(FrappeTestCase):
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

	def _ghi(self, luc):
		c.su_kien(c.NGUOI_A, MAN, luc, action_id=MAN + "::Ghi", outcome="ok")

	def test_chang_theo_thu_tu_va_khong_cong_doi(self):
		k = _kb_hai_chang()
		kb.tien_do(k.name, c.NGUOI_A, luc=T2)
		self._ghi(c.sau(T2, hours=1))
		moi = kb.cham(k.name, c.NGUOI_A, c.sau(T2, hours=2))
		self.assertIn("chang", [m["loai"] for m in moi])
		p = kb.tien_do(k.name, c.NGUOI_A, tao=False)
		self.assertEqual(p.chang_hien_tai, "thanh-thao")
		self.assertEqual(diem.tong_diem(c.NGUOI_A), 10 + 10 + 30, "2 bước + chặng; bước chặng 2 chưa đủ 2 ngày")
		kb.cham(k.name, c.NGUOI_A, c.sau(T2, hours=3))
		self.assertEqual(diem.tong_diem(c.NGUOI_A), 50, "chấm lại không cộng đôi")
		frappe.db.delete("Feedback Event", {"user": c.NGUOI_A})
		kb.cham(k.name, c.NGUOI_A, c.sau(T2, hours=4))
		p.reload()
		self.assertIn("lam-quen", kb._j(p.chang_xong), "bước/chặng đã xong giữ nguyên khi sổ sự kiện bị dọn")

	def test_duy_tri_chuoi(self):
		k = _kb_duy_tri()
		kb.tien_do(k.name, c.NGUOI_A, luc=T2)
		self._ghi(c.sau(T2, hours=1))                     # T2
		self._ghi(c.sau(T2, days=1, hours=1))             # T3
		self._ghi(c.sau(T2, days=3, hours=1))             # T5 (bỏ T4)
		kb.cham(k.name, c.NGUOI_A, c.sau(T2, days=1, hours=5))
		p = kb.tien_do(k.name, c.NGUOI_A, tao=False)
		self.assertEqual(kb._j(p.duy_tri)["hang-ngay"]["chuoi"], 2)
		kb.cham(k.name, c.NGUOI_A, c.sau(T2, days=3, hours=5))
		p.reload()
		tt = kb._j(p.duy_tri)["hang-ngay"]
		self.assertEqual((tt["chuoi"], tt["chuoi_dai_nhat"]), (1, 2))

	def test_duy_tri_sau_gio_han_khong_tinh_va_chu_nhat_khong_co_ky(self):
		k = _kb_duy_tri()
		kb.tien_do(k.name, c.NGUOI_A, luc=T2)
		self._ghi(c.sau(T2, hours=10))                    # 18:00 > hạn 17:00
		kb.cham(k.name, c.NGUOI_A, c.sau(T2, hours=11))
		p = kb.tien_do(k.name, c.NGUOI_A, tao=False)
		self.assertFalse(kb._j(p.duy_tri).get("hang-ngay", {}).get("ky_cuoi_dat"))
		ch = k.chang[0]
		self.assertIsNone(kb.ky_hien_tai(ch, c.sau(T2, days=6, hours=2)), "Chủ nhật không có kỳ")

	def _giao(self, k, chang_muc_tieu, bat_dau, chuoi=3):
		return frappe.get_doc({"doctype": "Feedback Mission", "kich_ban": k.name, "chang_muc_tieu": chang_muc_tieu,
		                       "chuoi_muc_tieu": chuoi, "bat_dau": bat_dau, "het_han": c.sau(bat_dau, days=7),
		                       "nhac": 0, "nguoi_nhan": [{"user": c.NGUOI_A}]}).insert(ignore_permissions=True)

	def test_nhiem_vu_va_nguoi_mo_duong(self):
		k = _kb_hai_chang()
		nv = self._giao(k, "lam-quen", T2)
		kb.tien_do(k.name, c.NGUOI_A, luc=T2)
		self._ghi(c.sau(T2, hours=1))
		kb.cham(k.name, c.NGUOI_A, c.sau(T2, hours=2))
		nv.reload()
		self.assertEqual(nv.nguoi_nhan[0].trang_thai, "Hoàn thành")
		self.assertEqual(diem.huan_chuong_cua(c.NGUOI_A).get("mo-duong"), 1)

	def test_nhiem_vu_sau_48h_khong_mo_duong(self):
		k = _kb_hai_chang()
		self._giao(k, "lam-quen", T2)
		kb.tien_do(k.name, c.NGUOI_A, luc=T2)
		self._ghi(c.sau(T2, days=3))
		kb.cham(k.name, c.NGUOI_A, c.sau(T2, days=3, hours=1))
		self.assertFalse(diem.huan_chuong_cua(c.NGUOI_A).get("mo-duong"))
		self.assertTrue(frappe.db.exists("Feedback Point", {"user": c.NGUOI_A, "ly_do": "Hoàn thành nhiệm vụ"}))


def tearDownModule():
	frappe.set_user("Administrator")
	c.xoa_nguoi()
