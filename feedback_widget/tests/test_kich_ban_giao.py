"""Giao kịch bản: kiểm quyền, người bị tắt, hạn, thẻ "được mời" (spec §4.7)."""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget.tests import _kich_ban_chung as c


class TestKichBanGiao(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		c.nguoi(c.NGUOI_A)
		cls.cu = c.dat_cai_dat(kb_bat=1)
		if not frappe.db.exists("Page", "thukb-trang"):
			frappe.get_doc({"doctype": "Page", "page_name": "thukb-trang", "title": "thukb", "module": "Feedback Widget",
			                "standard": "No", "roles": [{"role": "System Manager"}]}).insert(ignore_permissions=True)
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		c.dat_cai_dat(**cls.cu)
		frappe.delete_doc("Page", "thukb-trang", force=True, ignore_permissions=True)
		frappe.db.commit()
		super().tearDownClass()

	def setUp(self):
		c.don_dep()
		frappe.db.delete("Feedback Event", {"signature": "kich-ban-giao-thieu-quyen", "user": "Administrator"})

	def tearDown(self):
		c.don_dep()
		frappe.db.delete("Feedback Event", {"signature": "kich-ban-giao-thieu-quyen", "user": "Administrator"})
		frappe.db.commit()

	def _giao(self, k, **kw):
		d = {"doctype": "Feedback Mission", "kich_ban": k.name, "chang_muc_tieu": "lam-quen",
		     "nguoi_nhan": [{"user": c.NGUOI_A}]}
		d.update(kw)
		return frappe.get_doc(d).insert(ignore_permissions=True)

	def test_thieu_vai_trang_thi_chan_va_ghi_so(self):
		k = c.kich_ban("thukb-trang")
		with self.assertRaises(frappe.ValidationError):
			self._giao(k)
		self.assertTrue(frappe.db.exists("Feedback Event", {"signature": "kich-ban-giao-thieu-quyen"}))

	def test_nguoi_bi_tat(self):
		k = c.kich_ban("thukb-mo")
		frappe.db.set_value("User", c.NGUOI_A, "enabled", 0)
		try:
			with self.assertRaises(frappe.ValidationError):
				self._giao(k)
		finally:
			frappe.db.set_value("User", c.NGUOI_A, "enabled", 1)

	def test_han_qua_dai(self):
		k = c.kich_ban("thukb-mo")
		with self.assertRaises(frappe.ValidationError):
			self._giao(k, bat_dau="2026-10-01 08:00:00", het_han="2026-12-31 08:00:00")

	def test_giao_hop_le_tao_tien_do_va_the_moi(self):
		k = c.kich_ban("thukb-mo")
		nv = self._giao(k)
		self.assertTrue(frappe.db.exists("Feedback Playbook Progress", {"kich_ban": k.name, "user": c.NGUOI_A}))
		tb = frappe.get_all("Feedback Notice", filters={"nhiem_vu": nv.name, "loai_nhac": "N0"},
		                    fields=["name", "pham_vi", "kich_ban"])
		self.assertEqual(len(tb), 1)
		self.assertEqual((tb[0].pham_vi, tb[0].kich_ban), ("Một người", k.name))

	def test_chong_lan_man(self):
		c.kich_ban("Form/THUKB X/*")
		with self.assertRaises(frappe.ValidationError):
			c.kich_ban("Form/THUKB X/ABC-*")
