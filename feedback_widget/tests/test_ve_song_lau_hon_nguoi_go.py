"""Vé phải sống lâu hơn tài khoản người gõ nó.

Đo trên site asxh 10/09/2026: **10 trong 11 vé KHÔNG lưu được nữa**. `submitter_user`
là Link → User, và những tài khoản tạm (`nguoicho2995@asxh.local`, `quan1223@…`) đã bị
kịch bản gieo dữ liệu xoá đi. Từ giây đó, mọi thao tác xử lý vé — đổi trạng thái, ghi lý
do, trả lời — đều ném `LinkValidationError: Could not find Submitter User`, và câu ấy
không nói gì về góp ý cả. Người phân loại chỉ thấy một lỗi khung sườn ở đúng lúc họ định
trả lời người dùng.

Vé là **sổ ghi lời một người đã nói**. Nó quan sát tài khoản ấy, nó không được giam tài
khoản ấy (Link còn chặn cả việc xoá/vô hiệu hoá User), và nó không được chết theo. Nên
`submitter_user` là `Data`: vẫn lọc được, vẫn tra ngược được bằng `frappe.db.get_value`
khi tài khoản còn sống, mà mất tài khoản thì chỉ mất TÊN — không mất lời.

Thẻ cảm ơn đi kèm không cần vá: `can_bao()` hỏi `User.enabled`, tài khoản không còn thì
trả None và bỏ qua — mất người nhận thì không báo, chứ không phải nổ.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

DU_AN = "kiem-thu-vé-song-lau"
MA_NGUOI_DA_XOA = "khong-con-tai-khoan-nay@example.invalid"


class TestVeSongLauHonNguoiGo(FrappeTestCase):
	def tearDown(self):
		for n in frappe.get_all("Feedback Comment", filters={"project": DU_AN}, pluck="name"):
			frappe.delete_doc("Feedback Comment", n, force=True, ignore_permissions=True)
		frappe.db.commit()

	def _ve(self):
		return frappe.get_doc({
			"doctype": "Feedback Comment", "project": DU_AN, "source": "user",
			"message": "Chữ ở màn lịch sử hơi nhỏ", "status": "New",
			"screen_id": "nguoicho/lichsu", "screen_name": "Người cho — lịch sử",
			"submitter_user": MA_NGUOI_DA_XOA,
		}).insert(ignore_permissions=True)

	def test_ghi_duoc_ve_cua_tai_khoan_khong_con(self):
		self.assertFalse(frappe.db.exists("User", MA_NGUOI_DA_XOA),
		                 "phép kiểm này chỉ có nghĩa khi tài khoản THẬT SỰ không còn")
		ve = self._ve()   # nếu còn là Link thì chết ngay ở đây
		self.assertEqual(ve.submitter_user, MA_NGUOI_DA_XOA)

	def test_XU_LY_duoc_ve_cua_tai_khoan_khong_con(self):
		"""Đây mới là ca thật: vé đã nằm sẵn trên site, nay mới đến lượt xử lý."""
		ve = self._ve()
		ve.status = "Resolved"
		ve.status_note = "Đã tăng cỡ chữ lên 17px và đo lại trên máy thật."
		ve.save(ignore_permissions=True)      # đi qua đúng đường ghi của người phân loại
		self.assertEqual(frappe.db.get_value("Feedback Comment", ve.name, "status"), "Resolved")

	def test_truong_nay_khong_duoc_quay_lai_thanh_Link(self):
		"""Khoá bằng meta: đổi lại thành Link là làm hỏng mọi vé của tài khoản đã xoá."""
		f = frappe.get_meta("Feedback Comment").get_field("submitter_user")
		self.assertEqual(f.fieldtype, "Data",
		                 "submitter_user phải là Data — Link giam tài khoản và giết vé theo nó")
		self.assertFalse(f.options, "Data không được mang options")

	def test_van_loc_duoc_theo_nguoi_go(self):
		"""Đổi kiểu không được làm mất khả năng lọc — `nhung_ve_cua_toi` dựa vào nó."""
		ve = self._ve()
		self.assertIn(ve.name, frappe.get_all(
			"Feedback Comment", filters={"submitter_user": MA_NGUOI_DA_XOA}, pluck="name"))
