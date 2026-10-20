"""Thanh bên của module: mục trỏ Workspace đã xoá làm trắng mọi trang báo cáo (sidebar_item.js
đọc `.public` của undefined) — after_migrate phải dọn, và lối vào kịch bản màn phải có."""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget import thanh_ben


class TestThanhBen(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.sb = frappe.db.get_value("Workspace Sidebar", {"module": thanh_ben.MODULE}, "name")
		if not self.sb:
			self.skipTest("site này không có thanh bên của module")

	def tearDown(self):
		frappe.db.delete("Workspace Sidebar Item", {"parent": self.sb, "link_to": "THU-WS-DA-XOA"})
		frappe.db.commit()

	def test_xoa_muc_mo_coi_va_them_loi_vao(self):
		frappe.get_doc({"doctype": "Workspace Sidebar Item", "parent": self.sb, "parenttype": "Workspace Sidebar",
		                "parentfield": "items", "type": "Link", "link_type": "Workspace",
		                "link_to": "THU-WS-DA-XOA", "label": "Home", "idx": 99}).db_insert()
		ra = thanh_ben.don_va_bo_sung()
		self.assertGreaterEqual(ra["xoa"], 1)
		self.assertFalse(frappe.db.exists("Workspace Sidebar Item", {"parent": self.sb, "link_to": "THU-WS-DA-XOA"}))
		for loai, dich, _nhan in thanh_ben.MUC_THEM:
			if frappe.db.exists(loai, dich):
				self.assertTrue(frappe.db.exists("Workspace Sidebar Item", {"parent": self.sb, "link_to": dich}), dich)
		self.assertEqual(thanh_ben.don_va_bo_sung(), {"xoa": 0, "them": 0}, "chạy lại không đổi gì")
