"""Hai báo cáo quản trị của kịch bản màn (spec §6.7): tiến độ theo cặp + màn chưa ai dùng."""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget.feedback_widget.report.man_chua_ai_dung import man_chua_ai_dung as mc
from feedback_widget.feedback_widget.report.tien_do_kich_ban import tien_do_kich_ban as td
from feedback_widget import kich_ban as kb
from feedback_widget.tests import _kich_ban_chung as c

MAN = "thukb-bao-cao"
T2 = "2026-10-19 09:00:00"     # thứ Hai, trong giờ làm


def _nhac(k, user, luc):
	n = frappe.get_doc({"doctype": "Feedback Notice", "tieu_de": "THU nhắc", "noi_dung": "thử", "pham_vi": "Một người",
	                    "cac_nguoi": [{"user": user}], "dang_bat": 1, "kich_ban": k.name,
	                    "loai_nhac": "N1"}).insert(ignore_permissions=True)
	frappe.db.sql("UPDATE `tabFeedback Notice` SET creation = %s WHERE name = %s", (luc, n.name))
	return n.name


class TestKichBanBaoCao(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		c.nguoi(c.NGUOI_A); c.nguoi(c.NGUOI_B)
		cls.cu = c.dat_cai_dat(kb_bat=1)

	@classmethod
	def tearDownClass(cls):
		c.don_dep()
		c.dat_cai_dat(**cls.cu)
		super().tearDownClass()

	def setUp(self):
		c.don_dep()
		self.k = c.kich_ban(MAN, buoc=[{"chang": "lam-quen", "mo_ta": "Mở màn", "loai": "Mở màn", "so_lan": 1},
		                              {"chang": "lam-quen", "mo_ta": "Mở 3 lần", "loai": "Mở màn", "so_lan": 3}])
		kb.tien_do(self.k.name, c.NGUOI_A, luc=T2)
		kb.tien_do(self.k.name, c.NGUOI_B, luc=T2)

	def tearDown(self):
		c.don_dep()

	def _dong(self, user, **f):
		return next(r for r in td.du_lieu(frappe._dict(kich_ban=self.k.name, **f), luc=c.sau(T2, days=3))
		            if r["user"] == user)

	def test_nhac_co_tac_dung_va_dang_ket(self):
		# A: nhắc lúc T2, mở màn 2 giờ sau ⇒ có tác dụng. B: nhắc lúc T2, không động tay ⇒ kẹt.
		_nhac(self.k, c.NGUOI_A, T2); _nhac(self.k, c.NGUOI_B, T2)
		c.su_kien(c.NGUOI_A, MAN, c.sau(T2, hours=2))
		c.su_kien(c.NGUOI_B, MAN, c.sau(T2, hours=30))     # quá 24 giờ: không tính cho lời nhắc
		a, b = self._dong(c.NGUOI_A), self._dong(c.NGUOI_B)
		self.assertEqual((a["so_nhac"], a["pct_tac_dung"], a["dang_ket"]), (1, "100%", 0))
		self.assertEqual((b["so_nhac"], b["pct_tac_dung"], b["dang_ket"]), (1, "0%", 1))
		ket = [r["user"] for r in td.du_lieu(frappe._dict(kich_ban=self.k.name, dang_ket=1), luc=c.sau(T2, days=3))]
		self.assertEqual(ket, [c.NGUOI_B])

	def test_nhac_chua_het_24h_khong_tinh(self):
		_nhac(self.k, c.NGUOI_A, T2)
		r = next(r for r in td.du_lieu(frappe._dict(kich_ban=self.k.name), luc=c.sau(T2, hours=5))
		         if r["user"] == c.NGUOI_A)
		self.assertEqual((r["pct_tac_dung"], r["dang_ket"]), ("—", 0), "cửa sổ chưa hết thì chưa phải kẹt")

	def test_buoc_xong_va_lan_cuoi_mo(self):
		c.su_kien(c.NGUOI_A, MAN, c.sau(T2, hours=1))
		kb.cham(self.k.name, c.NGUOI_A, luc=c.sau(T2, hours=2))
		a = self._dong(c.NGUOI_A)
		self.assertEqual(a["buoc"], "1/2")
		self.assertEqual(str(a["lan_cuoi_mo"])[:16], str(c.sau(T2, hours=1))[:16])

	def test_man_chua_ai_dung(self):
		k2 = c.kich_ban(MAN + "-2", chang=[{"ma": "lam-quen", "ten": "Làm quen", "thu_tu": 1, "loai": "Một lần"}],
		                buoc=[{"chang": "lam-quen", "mo_ta": "Mở màn", "loai": "Mở màn", "so_lan": 1}])
		kb.tien_do(k2.name, c.NGUOI_A, luc=T2)
		c.su_kien(c.NGUOI_A, MAN + "-2", c.sau(T2, hours=1))
		kb.cham(k2.name, c.NGUOI_A, luc=c.sau(T2, hours=2))
		rows = {r["kich_ban"]: r for r in mc.du_lieu()}
		self.assertEqual(rows[k2.name]["so_dat"], 1)
		self.assertEqual(rows[self.k.name]["so_dat"], 0)
		ds = [r["kich_ban"] for r in mc.du_lieu() if r["kich_ban"] in (k2.name, self.k.name)]
		self.assertEqual(ds, [self.k.name, k2.name], "màn ít người đạt nhất lên đầu")


def tearDownModule():
	frappe.set_user("Administrator")
	c.xoa_nguoi()
