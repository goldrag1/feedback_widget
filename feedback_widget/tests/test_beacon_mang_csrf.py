"""Lượt xả sổ lúc RỜI TRANG phải mang được CSRF, nếu không nó rơi im lặng.

`navigator.sendBeacon` không đặt được header ⇒ không có `X-Frappe-CSRF-Token` ⇒
Frappe trả 400 `CSRFTokenError` trước khi vào endpoint, nên KHÔNG có dòng nào trong
Error Log và sổ chỉ đơn giản là thiếu. Đo trên prod 26/08 (nginx access.log):
91 lượt 400 / 616 lượt POST `ghi_lo` = 15%, và đó đúng là những sự kiện cuối cùng
của mỗi màn — thứ nói lên người ta bỏ đi ở đâu.

Frappe đọc `form_dict.pop("csrf_token")` (frappe/auth.py) nên thân yêu cầu là chỗ
hợp lệ để mang mã. Phép kiểm này khoá lại điều đó ở NGUỒN: một lần "dọn dẹp" bỏ
khoá kia ra khỏi gói beacon là mất 15% sổ mà không ai thấy.
"""

import os
import re
import unittest

_GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CORE = os.path.join(_GOC, "public", "js", "feedback_widget_core.js")


def _than_ham(ten: str) -> str:
	src = open(_CORE, encoding="utf-8").read()
	i = src.index(f"{ten}(")
	# cắt tới hàm kế tiếp cùng mức thụt đầu dòng
	j = src.index("\n    _postJSON(", i)
	return src[i:j]


class TestBeaconMangCsrf(unittest.TestCase):
	def setUp(self):
		self.than = _than_ham("_flushEvents")

	def test_co_goi_sendBeacon(self):
		"""Nếu ai đó bỏ hẳn beacon thì phép kiểm dưới thành vô nghĩa — chốt trước."""
		self.assertIn("navigator.sendBeacon", self.than)

	def test_goi_beacon_co_csrf_token(self):
		self.assertRegex(self.than, r"csrf_token\s*=\s*ma|csrf_token['\"]?\]?\s*=")
		self.assertIn("X-Frappe-CSRF-Token", self.than)

	def test_csrf_nam_trong_goi_gui_cho_beacon(self):
		"""Mã phải được gắn vào chính đối tượng đem đi Blob, không phải biến rời."""
		m = re.search(r"sendBeacon\(\s*this\.cfg\.eventEndpoint,\s*\n?\s*new Blob\(\[JSON\.stringify\((\w+)\)\]",
					  self.than)
		self.assertIsNotNone(m, "không đọc được tên biến gói gửi cho beacon")
		bien = m.group(1)
		self.assertRegex(self.than, rf"{bien}\.csrf_token\s*=")

	def test_duong_fetch_khong_bi_nhet_them_khoa_la(self):
		"""`_postJSON` vẫn gửi gói GỐC: header đã có mã, thêm khoá vào thân là rủi ro thừa."""
		m = re.search(r"this\._postJSON\(this\.cfg\.eventEndpoint,\s*(\w+),", self.than)
		self.assertIsNotNone(m)
		self.assertNotEqual(m.group(1), "goiBeacon")
