"""Góp ý có ích / thành cải tiến → điểm, thu hồi, huân chương, bù điểm (spec §8.2)."""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget import diem
from feedback_widget.patches import v6_bu_diem_gop_y
from feedback_widget.tests import _kich_ban_chung as c


def _ve(source="user", tag=None):
	return frappe.get_doc({"doctype": "Feedback Comment", "project": c.TIEN_TO + "du-an", "source": source,
	                       "submitter_user": c.NGUOI_A, "screen_id": "thukb-gy", "screen_name": "thukb-gy",
	                       "message": c.TIEN_TO + "góp ý", "ts": "2026-10-19 09:00:00", "status": "New",
	                       "tag_type": tag}).insert(ignore_permissions=True)


class TestKichBanGopY(FrappeTestCase):
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

	def test_resolved_tu_bat_co_ich_mot_lan(self):
		ve = _ve()
		ve.status = "Resolved"; ve.save(ignore_permissions=True)
		self.assertEqual(ve.co_ich, 1)
		self.assertEqual(diem.tong_diem(c.NGUOI_A), 20)
		ve.status_note = "sửa vặt"; ve.save(ignore_permissions=True)
		self.assertEqual(diem.tong_diem(c.NGUOI_A), 20, "lưu lại không cộng thêm")
		ve.co_ich = 0; ve.save(ignore_permissions=True)
		self.assertEqual(diem.tong_diem(c.NGUOI_A), 0, "tắt tay ⇒ thu hồi")
		self.assertTrue(frappe.db.exists("Feedback Point", {"user": c.NGUOI_A, "ly_do": "Thu hồi"}))

	def test_cai_tien_va_huan_chuong(self):
		ve = _ve(tag="bug")
		ve.thanh_cai_tien = 1; ve.save(ignore_permissions=True)
		self.assertEqual(diem.tong_diem(c.NGUOI_A), 70)
		self.assertEqual(diem.huan_chuong_cua(c.NGUOI_A), {"mat-tinh": 1})

	def test_ve_may_khong_co_diem(self):
		ve = _ve(source="auto")
		ve.status = "Resolved"; ve.save(ignore_permissions=True)
		self.assertEqual(diem.tong_diem(c.NGUOI_A), 0)

	def test_bu_diem_chay_hai_lan(self):
		ve = _ve()
		frappe.db.set_value("Feedback Comment", ve.name, "status", "Resolved")
		v6_bu_diem_gop_y.execute([ve.name])
		v6_bu_diem_gop_y.execute([ve.name])
		self.assertEqual(diem.tong_diem(c.NGUOI_A), 20)
