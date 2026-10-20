"""Nhắc khi chậm (N1–N5) + luật chống ồn + vòng đời thẻ nhắc (spec §7)."""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget import nhac
from feedback_widget.api import thong_bao
from feedback_widget.tests import _kich_ban_chung as c

MAN = "thukb-nhac"
T2 = "2026-10-19 09:00:00"     # thứ Hai, trong giờ làm


def _the(user, loai=None):
	return frappe.db.sql("""SELECT n.name, n.loai_nhac FROM `tabFeedback Notice` n
	                        JOIN `tabFeedback Notice User` u ON u.parent = n.name AND u.parenttype='Feedback Notice'
	                        WHERE u.user = %s AND n.loai_nhac IS NOT NULL""" + (" AND n.loai_nhac = %s" if loai else ""),
	                     (user, loai) if loai else (user,), as_dict=True)


class TestKichBanNhac(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		c.nguoi(c.NGUOI_A); c.nguoi(c.NGUOI_B)
		cls.cu = c.dat_cai_dat(kb_bat=1)

	@classmethod
	def tearDownClass(cls):
		c.dat_cai_dat(**cls.cu)
		super().tearDownClass()

	def setUp(self):
		c.don_dep()

	def tearDown(self):
		c.don_dep()

	def _kb(self, duy_tri=False):
		if duy_tri:
			return c.kich_ban(MAN, chang=[{"ma": "hang-ngay", "ten": "Hằng ngày", "thu_tu": 1, "loai": "Duy trì",
			                               "chu_ky": "Ngày", "gio_han": "17:00:00"}],
			                  buoc=[{"chang": "hang-ngay", "mo_ta": "Ghi", "loai": "Bấm nút", "nut": MAN + "::Ghi"}])
		return c.kich_ban(MAN, buoc=[
			{"chang": "lam-quen", "mo_ta": "Mở", "loai": "Mở màn"},
			{"chang": "lam-quen", "mo_ta": "Ghi phiếu", "loai": "Bấm nút", "nut": MAN + "::Ghi"},
			{"chang": "lam-quen", "mo_ta": "Góp ý", "loai": "Góp ý trên màn"},
		])

	def _giao(self, k, chang="lam-quen", nguoi=(c.NGUOI_A,), giao=None):
		frappe.flags.kb_khong_gui_moi = True   # thẻ "được mời" thử ở test_giao
		try:
			return frappe.get_doc({"doctype": "Feedback Mission", "kich_ban": k.name, "chang_muc_tieu": chang,
			                       "bat_dau": T2, "het_han": c.sau(T2, days=7), "nhac": 1,
			                       "nguoi_giao": giao or c.NGUOI_B,
			                       "nguoi_nhan": [{"user": u} for u in nguoi]}).insert(ignore_permissions=True)
		finally:
			frappe.flags.kb_khong_gui_moi = False

	def test_n1_chua_mo(self):
		self._giao(self._kb())
		nhac.nhac_kich_ban(c.sau(T2, hours=5))
		self.assertEqual(_the(c.NGUOI_A), [], "chưa đủ 24 giờ")
		nhac.nhac_kich_ban(c.sau(T2, days=1, hours=1))
		self.assertEqual([t.loai_nhac for t in _the(c.NGUOI_A)], ["N1"])
		nhac.nhac_kich_ban(c.sau(T2, days=1, hours=2))
		self.assertEqual(len(_the(c.NGUOI_A)), 1, "chạy lại không gửi đôi")

	def test_n2_cham_tien_do(self):
		self._giao(self._kb())
		c.su_kien(c.NGUOI_A, MAN, c.sau(T2, hours=1))
		nhac.nhac_kich_ban(c.sau(T2, days=4, hours=1))   # 57% thời gian, 0/3 bước được chấm
		self.assertEqual([t.loai_nhac for t in _the(c.NGUOI_A)], ["N2"])

	def test_n3_sap_het_han(self):
		self._giao(self._kb())
		c.su_kien(c.NGUOI_A, MAN, c.sau(T2, hours=1))
		nhac.nhac_kich_ban(c.sau(T2, days=7, minutes=-30))   # thứ Hai 08:30, còn 30 phút
		self.assertEqual([t.loai_nhac for t in _the(c.NGUOI_A)], ["N3"], "N3 thắng N2 khi vượt trần 1/kịch bản")

	def test_n4_qua_han_va_tong_hop_cho_nguoi_giao(self):
		nv = self._giao(self._kb())
		nhac.nhac_kich_ban(c.sau(T2, days=8, hours=1))   # thứ Ba tuần sau
		self.assertEqual([t.loai_nhac for t in _the(c.NGUOI_A)], ["N4"])
		self.assertEqual([t.loai_nhac for t in _the(c.NGUOI_B)], ["N4-tong-hop"])
		nv.reload()
		self.assertEqual(nv.nguoi_nhan[0].trang_thai, "Quá hạn")
		nhac.nhac_kich_ban(c.sau(T2, days=8, hours=2))
		self.assertEqual(len(_the(c.NGUOI_B)), 1, "thẻ tổng hợp một lần mỗi ngày")
		nhac.nhac_kich_ban(c.sau(T2, days=9, hours=1))
		self.assertEqual(len(_the(c.NGUOI_A, "N4")), 1, "N4 cho người nhận chỉ một lần")
		self.assertEqual(len(_the(c.NGUOI_B)), 2, "ngày hôm sau lại có một thẻ tổng hợp")

	def test_ngoai_gio_khong_gui(self):
		self._giao(self._kb())
		nhac.nhac_kich_ban(c.sau(T2, days=1, hours=10))   # 19:00
		nhac.nhac_kich_ban(c.sau(T2, days=6, hours=1))    # Chủ nhật
		self.assertEqual(_the(c.NGUOI_A), [])

	def test_n5_chi_nguoi_duoc_giao(self):
		k = self._kb(duy_tri=True)
		self._giao(k, chang="hang-ngay")
		c.su_kien(c.NGUOI_B, MAN, c.sau(T2, hours=1))
		nhac.nhac_kich_ban(c.sau(T2, hours=6, minutes=30))   # 15:30, hạn 17:00
		self.assertEqual([t.loai_nhac for t in _the(c.NGUOI_A)], ["N5"])
		self.assertEqual(_the(c.NGUOI_B), [], "người không được giao không bao giờ bị nhắc")

	def test_de_mai_va_dung_sau_ba_lan_bo_qua(self):
		self._giao(self._kb())
		nhac.nhac_kich_ban(c.sau(T2, days=1, hours=1))
		ten = _the(c.NGUOI_A)[0].name
		frappe.set_user(c.NGUOI_A)
		thong_bao.da_xem(ten, tam_hoan=1)
		frappe.set_user("Administrator")
		self.assertIsNone(nhac.gui_nhac(c.NGUOI_A, frappe.db.get_value("Feedback Playbook", {"man": MAN}),
		                                "N2", "x", "y", "/app/x", luc=c.sau(T2, days=1, hours=5)),
		                  "đang tạm hoãn tới giờ làm ngày kế")
		frappe.db.set_value("Feedback Playbook Progress", {"user": c.NGUOI_A}, "so_lan_bo_qua_lien", 3)
		nhac.nhac_kich_ban(c.sau(T2, days=3, hours=1))
		self.assertEqual(len(_the(c.NGUOI_A)), 1, "bỏ qua 3 lần ⇒ dừng nhắc")
		self.assertTrue(_the(c.NGUOI_B, "N4-tong-hop"), "người giao được báo để nói chuyện trực tiếp")

	def test_tran_ngay(self):
		kbs = [self._kb()]
		for i in range(3):
			kbs.append(c.kich_ban(f"{MAN}-{i}", buoc=[{"chang": "lam-quen", "mo_ta": "Mở", "loai": "Mở màn"}]))
		for k in kbs:
			self._giao(k)
		nhac.nhac_kich_ban(c.sau(T2, days=1, hours=1))
		self.assertEqual(len(_the(c.NGUOI_A)), 3, "tối đa 3 lời nhắc/người/ngày")
