"""Tên dự án khai ở Cài đặt phải là thứ MÁY CHỦ ghi vào sổ.

Bản gộp hai bảng cài đặt (26/08) đổi tên khoá `project` → `project_name`, còn bốn chỗ đọc
ở máy chủ (`su_kien.ghi_lo`, `kiem_ke_giao_dien`, `khai_danh_muc`, `tac_vu._du_an`) vẫn hỏi
khoá cũ: chúng lặng lẽ rơi về tên site, tức mọi bản ghi của một site khai tên riêng bị dồn
sang một rổ khác — không lỗi, không dòng log, chỉ là báo cáo đếm thiếu.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget import tac_vu
from feedback_widget.api import su_kien

TEN = "THU-du-an-khoa"
MAN = "kiem-thu-khoa"


class TestKhoaDuAn(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self._cu = frappe.db.get_single_value("Feedback Settings", "project_name")
		self._dat(TEN)

	def tearDown(self):
		frappe.db.delete("Feedback Event", {"screen_id": MAN})
		self._dat(self._cu or "")
		frappe.db.commit()

	def _dat(self, v):
		frappe.db.set_single_value("Feedback Settings", "project_name", v)
		frappe.clear_cache(doctype="Feedback Settings")
		frappe.db.commit()

	def test_tac_vu_doc_ten_du_an_da_khai(self):
		self.assertEqual(tac_vu._du_an(), TEN)

	def test_ghi_lo_khong_truyen_project_thi_lay_ten_da_khai(self):
		"""Trình duyệt cũ không gửi `project` — máy chủ phải tự khai đúng, không rơi về tên site."""
		su_kien.ghi_lo(events=[{"kind": "dung", "outcome": "ok", "screen_id": MAN}])
		frappe.db.commit()
		self.assertEqual(
			frappe.db.count("Feedback Event", {"project": TEN, "screen_id": MAN}), 1)
		self.assertEqual(
			frappe.db.count("Feedback Event", {"project": frappe.local.site, "screen_id": MAN}), 0)


class TestGieoMacDinh(FrappeTestCase):
	"""Màn Cài đặt phải hiện ĐÚNG thứ hệ đang làm.

	Với Single, `default` khai trong DocType JSON không được áp khi thiếu dòng: form trả
	0/None trong khi `cai_dat()` trả 1. Người vận hành mở màn ra rồi bấm Lưu là ghi chết
	số 0 ấy — widget tắt cho tất cả mọi người, không một dòng lỗi.
	"""

	KHOA = "enable_on_desk"

	def setUp(self):
		frappe.set_user("Administrator")
		self._cu = frappe.db.sql(
			"""SELECT value FROM `tabSingles` WHERE doctype='Feedback Settings' AND field=%s""",
			self.KHOA)
		frappe.db.sql("""DELETE FROM `tabSingles` WHERE doctype='Feedback Settings' AND field=%s""",
		              self.KHOA)
		frappe.clear_cache(doctype="Feedback Settings")
		frappe.db.commit()

	def tearDown(self):
		frappe.clear_cache(doctype="Feedback Settings")
		frappe.db.commit()

	def test_thieu_dong_thi_man_hinh_noi_nguoc_voi_hanh_vi(self):
		from feedback_widget.cai_dat import cai_dat
		self.assertEqual(int(frappe.get_single("Feedback Settings").get(self.KHOA) or 0), 0)
		self.assertEqual(int(cai_dat()[self.KHOA]), 1, "hệ vẫn coi là BẬT — đó là chỗ lệch")

	def test_gieo_xong_thi_hai_ben_khop(self):
		from feedback_widget.cai_dat import cai_dat, gieo_mac_dinh
		thieu = gieo_mac_dinh()
		self.assertIn(self.KHOA, thieu)
		frappe.clear_cache(doctype="Feedback Settings")
		self.assertEqual(int(frappe.get_single("Feedback Settings").get(self.KHOA) or 0),
		                 int(cai_dat()[self.KHOA]))

	def test_khong_de_khoa_da_khai(self):
		"""`enabled = 0` ai đó cố ý tắt không được patch bật lại."""
		from feedback_widget.cai_dat import gieo_mac_dinh
		frappe.db.set_single_value("Feedback Settings", "enabled", 0)
		frappe.db.commit()
		gieo_mac_dinh()
		self.assertEqual(int(frappe.db.get_single_value("Feedback Settings", "enabled") or 0), 0)
		frappe.db.set_single_value("Feedback Settings", "enabled", 1)
		frappe.db.commit()


class TestGiaTriHieuLuc(FrappeTestCase):
	"""Site MỚI CÀI chưa có dòng nào trong `tabSingles` vẫn phải gắn được widget.

	Đo trên gương HTS 26/08 sau lượt gộp: `enable_on_desk` + `allow_all_roles` vắng mặt
	⇒ `get_settings()` (đọc thẳng doc) trả False ⇒ `is_eligible` False ⇒ widget KHÔNG
	gắn ⇒ vừa mất nút vừa không thu được dòng nào, không một lỗi nào.
	"""

	VANG = ("enable_on_desk", "allow_all_roles")

	def setUp(self):
		frappe.set_user("Administrator")
		self._cu = {f: frappe.db.sql(
			"""SELECT value FROM `tabSingles` WHERE doctype='Feedback Settings' AND field=%s""", f)
			for f in self.VANG}
		for f in self.VANG:
			frappe.db.sql(
				"""DELETE FROM `tabSingles` WHERE doctype='Feedback Settings' AND field=%s""", f)
		frappe.clear_cache(doctype="Feedback Settings")
		frappe.db.commit()

	def tearDown(self):
		from feedback_widget.cai_dat import gieo_mac_dinh
		gieo_mac_dinh()
		frappe.clear_cache(doctype="Feedback Settings")
		frappe.db.commit()

	def test_thieu_dong_van_du_dieu_kien_gan_widget(self):
		from feedback_widget.api.feedback import get_settings
		ct = get_settings()
		self.assertTrue(ct["enable_on_desk"], "thiếu dòng KHÔNG có nghĩa là đã tắt")
		self.assertTrue(ct["allow_all_roles"])

	def test_boot_noi_dung_dieu_kien(self):
		from feedback_widget.api.feedback import extend_bootinfo
		boot = frappe._dict()
		extend_bootinfo(boot)
		self.assertTrue(boot.feedback_widget_settings["is_eligible"])
		self.assertTrue(boot.feedback_widget["show_widget"])
