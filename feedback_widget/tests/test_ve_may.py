"""Vé MÁY: gom theo chữ ký, vé đã đóng mà lỗi quay lại thì mở vé MỚI.

Vì sao phải có test: nếu gom hỏng, một lỗi lặp 40 lần đẻ 40 vé và hộp thư chết ngập —
người xử lý bỏ đọc luôn cả vé người gõ, tức tính năng này phá đúng thứ nó định giúp.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget.api.feedback import collect

DU_AN = "kiemthu-vemay"


class TestVeMay(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self._don()

	def tearDown(self):
		self._don()

	def _don(self):
		frappe.db.delete("Feedback Comment", {"project": DU_AN})
		frappe.db.commit()

	def _ve(self, msg, man="#/lsx", ten="Lệnh SX", nguon="auto"):
		return collect(project=DU_AN, screen_id=man, screen_name=ten, message=msg,
		               source=nguon, submitter="(máy)",
		               context={"app": {"endpoint": "shopfloor.pick_material_for_stage"}})

	def test_cung_chu_ky_thi_GOP_chu_khong_de_ve_moi(self):
		a = self._ve("[KHACCUON] Băng A-B1 của cuộn A — lệnh xả từ cuộn B")
		b = self._ve("[KHACCUON] Băng C-B9 của cuộn C — lệnh xả từ cuộn D", man="#/viec", ten="Việc của tôi")
		self.assertEqual(a["name"], b["name"])
		self.assertTrue(b.get("merged"))
		self.assertEqual(frappe.db.count("Feedback Comment", {"project": DU_AN}), 1)
		d = frappe.db.get_value("Feedback Comment", a["name"],
		                        ["occurrences", "affected_screens", "marker", "source"], as_dict=True)
		self.assertEqual(d.occurrences, 2)
		self.assertEqual(d.marker, "KHACCUON")
		self.assertEqual(d.source, "auto")
		# Hai màn khác nhau cùng dính: đây là câu trả lời cho "lỗi này rộng tới đâu"
		self.assertIn("Việc của tôi", d.affected_screens)

	def test_hai_loai_khac_nhau_thi_HAI_ve(self):
		self._ve("[KHACCUON] Băng của cuộn khác")
		self._ve("[MAYBAN] Máy đang chạy cuộn khác")
		self.assertEqual(frappe.db.count("Feedback Comment", {"project": DU_AN}), 2)

	def test_ve_da_DONG_ma_loi_quay_lai_thi_mo_ve_MOI(self):
		"""Hồi quy phải nhìn thấy được. Cộng dồn vào vé cũ là giấu nó đi."""
		a = self._ve("[THIEUCAN] Chưa cân đủ đầu ra")
		frappe.db.set_value("Feedback Comment", a["name"], "status", "Resolved")
		frappe.db.commit()
		b = self._ve("[THIEUCAN] Chưa cân đủ đầu ra")
		self.assertNotEqual(a["name"], b["name"])
		self.assertEqual(frappe.db.count("Feedback Comment", {"project": DU_AN}), 2)

	def test_ve_NGUOI_go_khong_bao_gio_bi_gop(self):
		"""Hai người góp ý giống chữ vẫn là hai tiếng nói — gộp là xoá mất một người."""
		a = collect(project=DU_AN, screen_id="#/lsx", screen_name="Lệnh SX",
		            message="Màn này chậm quá", submitter="Anh A")
		b = collect(project=DU_AN, screen_id="#/lsx", screen_name="Lệnh SX",
		            message="Màn này chậm quá", submitter="Chị B")
		self.assertNotEqual(a["name"], b["name"])
		self.assertIsNone(frappe.db.get_value("Feedback Comment", a["name"], "signature"))
