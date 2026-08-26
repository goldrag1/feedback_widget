"""Tên dự án của sổ không được mang tiền tố thương hiệu ghim trong mã.

Nhánh dự phòng (site chưa khai `project_name`) từng ghim "dcnet-", rồi ai đó cài cho
khách khác đổi thành "tamdinh-". Hệ quả đo được trên prod 26/08: vé của ducan mang BA tên
dự án cùng lúc — `dcnet-ducan…` 183 vé, `ducan…` 22 vé, `tamdinh-ducan…` 1 vé (sinh tối
đó) — nên mọi bảng gom theo dự án chẻ làm ba, và tin nhắn Telegram gọi khách này bằng tên
khách khác.

Tên site đã đủ nhận dạng. Muốn tên khác thì khai trong Cài đặt, không sửa mã.
"""

import os
import re
import unittest

_GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BUNDLE = os.path.join(_GOC, "public", "js", "feedback_widget.bundle.js")
_THUONG_HIEU = ("dcnet", "tamdinh", "nextstar", "hts", "ducan", "thanhcong", "diginext")


class TestTenDuAn(unittest.TestCase):
    def setUp(self):
        self.src = open(_BUNDLE, encoding="utf-8").read()
        m = re.search(r"const project = customProject \|\|(.*?);", self.src, re.S)
        self.assertIsNotNone(m, "không tìm thấy nhánh dự phòng đặt tên dự án")
        self.dong = m.group(1)

    def test_khong_ghim_ten_thuong_hieu(self):
        for th in _THUONG_HIEU:
            self.assertNotIn(f'"{th}-', self.dong.lower(),
                             f"nhánh dự phòng đang ghim tiền tố '{th}-'")

    def test_van_suy_tu_ten_site(self):
        self.assertIn("siteSlug()", self.dong)

    def test_van_uu_tien_cai_dat(self):
        """Khai `project_name` trong Cài đặt phải thắng — đó là đường đổi tên hợp lệ."""
        self.assertIn("customProject ||", self.src)
        self.assertRegex(self.src, r'customProject\s*=\s*\(settings\.project_name')
