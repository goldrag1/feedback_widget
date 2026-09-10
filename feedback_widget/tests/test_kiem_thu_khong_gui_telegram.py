"""Bộ kiểm KHÔNG được gửi tin ra ngoài.

10/09/2026: chạy `bench run-tests --app feedback_widget` trên site thật đã bắn một loạt
tin Telegram vào máy chủ dự án. Chủ dự án đọc được cả những câu lấy từ dữ liệu MẪU của
một dự án khác — `[XINDUYET] Cân không khớp`, `RuntimeError: hỏng` — và hiểu chúng như
sự cố thật đang xảy ra trên hệ thống của mình.

Đây là hạng lỗi nặng hơn hẳn "vé rác trong sổ": vé thì xoá được, **tin đã gửi thì không
rút lại được**, và nó tiêu vào đúng thứ mà cả cái sổ góp ý này sinh ra để xây — lòng tin
rằng khi máy nhắn tin cho anh thì đó là chuyện có thật.

Cửa chặn nằm ở `notifier._post`, tức chỗ hẹp nhất mà MỌI lệnh gửi đều đi qua — chặn ở đó
thì không phụ thuộc vào việc người viết bài kiểm sau này có nhớ giả lập hay không.
"""

import os
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget import notifier


class TestKiemThuKhongGuiTelegram(FrappeTestCase):
	def test_dang_chay_bo_kiem_thi_KHONG_mo_ket_noi_nao(self):
		"""Ca thật: chính lúc này. Nếu `_post` mở kết nối, phép giả lập sẽ ném."""
		with patch("urllib.request.urlopen", side_effect=AssertionError(
				"bộ kiểm vừa gọi ra Internet — tin thật sắp tới máy người ta")):
			ok, tra_loi = notifier._post("https://api.telegram.org/botX/sendMessage",
			                             b"x", "text/plain")
		self.assertFalse(ok)
		self.assertEqual(tra_loi.get("bo_qua"), "dang_kiem_thu")

	def test_send_message_cung_khong_gui(self):
		"""Chặn ở `_post` phải phủ luôn các hàm bọc ngoài nó."""
		with patch("feedback_widget.notifier._load_config", return_value=("TOK", "-100")), \
		     patch("urllib.request.urlopen", side_effect=AssertionError("gửi thật")):
			self.assertFalse(notifier.send_message("thử"))

	def test_is_configured_tra_False_de_khong_XEP_HANG_viec_gui(self):
		"""Người gọi hỏi `is_configured()` trước khi `enqueue`. Trả False ở đây thì hàng
		đợi không nhận việc — và cái đó quan trọng, vì việc trong hàng đợi chạy ở TIẾN
		TRÌNH KHÁC, nơi `frappe.flags.in_test` đã tắt."""
		with patch("feedback_widget.notifier._load_config", return_value=("TOK", "-100")):
			self.assertFalse(notifier.is_configured())

	def test_ngoai_bo_kiem_thi_van_gui_binh_thuong(self):
		"""Chặn nhầm cả lúc chạy thật thì còn tệ hơn: hỏng im lặng đúng thứ cần báo động."""
		with patch.dict(os.environ, {}, clear=False), \
		     patch("feedback_widget.notifier.dang_kiem_thu", return_value=False), \
		     patch("feedback_widget.notifier._load_config", return_value=("TOK", "-100")):
			self.assertTrue(notifier.is_configured())
			goi = {}
			class GiaVo:
				status = 200
				def read(self): return b'{"ok": true}'
				def __enter__(self): return self
				def __exit__(self, *a): return False
			with patch("urllib.request.urlopen", lambda *a, **k: goi.setdefault("co", 1) and None or GiaVo()):
				self.assertTrue(notifier.send_message("tin thật"))
			self.assertTrue(goi.get("co"), "phải THỰC SỰ gọi đi khi không phải lúc kiểm")

	def test_bien_moi_truong_cung_chan_duoc(self):
		"""Cho tiến trình KHÁC (worker, script tay) tắt được đường gửi mà không sửa mã."""
		with patch("frappe.flags", frappe._dict(in_test=False)), \
		     patch.dict(os.environ, {"FBW_KHONG_GUI": "1"}):
			self.assertTrue(notifier.dang_kiem_thu())
