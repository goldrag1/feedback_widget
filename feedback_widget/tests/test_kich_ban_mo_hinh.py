"""Kịch bản màn — mô hình dữ liệu, cài đặt mặc định, chỉ mục (spec §4, §9)."""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget import cai_dat

DOCTYPE_MOI = [
	"Feedback Playbook", "Feedback Playbook Guide", "Feedback Playbook Stage", "Feedback Playbook Tip",
	"Feedback Mission Step", "Feedback Playbook Progress", "Feedback Mission", "Feedback Mission Assignee",
	"Feedback Point", "Feedback Badge Award",
]


class TestKichBanMoHinh(FrappeTestCase):
	def test_doctype_ton_tai(self):
		for dt in DOCTYPE_MOI:
			self.assertTrue(frappe.db.exists("DocType", dt), dt)
		for dt, f in [("Feedback Comment", "co_ich"), ("Feedback Comment", "thanh_cai_tien"),
		              ("Feedback Comment", "tu_cam_nhan"), ("Feedback Notice", "kich_ban"),
		              ("Feedback Notice", "loai_nhac"), ("Feedback Notice Seen", "tam_hoan")]:
			self.assertTrue(frappe.get_meta(dt).has_field(f), f"{dt}.{f}")

	def test_cai_dat_mac_dinh(self):
		ct = cai_dat.MAC_DINH
		self.assertEqual(ct["kb_bat"], 0)
		self.assertEqual([ct[k] for k in ("diem_buoc", "diem_chang", "diem_ky_duy_tri", "diem_nhiem_vu",
		                                  "diem_mo_duong", "diem_co_ich", "diem_cai_tien", "diem_cam_nhan")],
		                 [10, 30, 5, 30, 20, 20, 50, 5])
		self.assertEqual([ct["nguong_thanh_thao"], ct["nguong_key_user"], ct["nguong_dai_su"]], [100, 300, 700])
		self.assertEqual((ct["gio_lam_tu"], ct["gio_lam_den"], ct["ngay_lam_viec"]), ("08:00", "18:00", "1,2,3,4,5,6"))
		meta = frappe.get_meta("Feedback Settings")
		for k in ct:
			self.assertTrue(meta.has_field(k), f"Feedback Settings thiếu ô {k}")
		self.assertIn("Administrator", cai_dat.khong_xep_hang())

	def test_chi_muc(self):
		ten = {r["Key_name"] for r in frappe.db.sql("SHOW INDEX FROM `tabFeedback Event`", as_dict=True)}
		self.assertIn("fbw_user_ts", ten)
		self.assertIn("fbw_screen_ts", ten)

	def test_khoa_diem_unique(self):
		khoa = "THU|khoa-trung|" + frappe.generate_hash(length=6)
		frappe.get_doc({"doctype": "Feedback Point", "user": "Administrator", "diem": 1, "ly_do": "Bước", "khoa": khoa}).insert()
		with self.assertRaises((frappe.UniqueValidationError, frappe.DuplicateEntryError)):
			frappe.get_doc({"doctype": "Feedback Point", "user": "Administrator", "diem": 1, "ly_do": "Bước", "khoa": khoa}).insert()
		frappe.db.rollback()

	def test_gieo_khong_ghi_chet_o_chua_ai_cham(self):
		"""Gieo khoá mới KHÔNG được ghi 0 vào ô Check khác chưa ai chạm (đo mirror 20/10:
		bản `doc.save()` tắt mất `tu_dong_bao_ve`)."""
		frappe.db.sql("""DELETE FROM `tabSingles` WHERE doctype='Feedback Settings'
		                 AND field IN ('tu_dong_bao_ve', 'diem_buoc')""")
		thieu = cai_dat.gieo_mac_dinh()
		self.assertIn("diem_buoc", thieu)
		v = frappe.db.sql("""SELECT value FROM `tabSingles` WHERE doctype='Feedback Settings'
		                     AND field='tu_dong_bao_ve'""")
		self.assertEqual(v[0][0], "1")
		self.assertEqual(cai_dat.cai_dat()["diem_buoc"], 10)
