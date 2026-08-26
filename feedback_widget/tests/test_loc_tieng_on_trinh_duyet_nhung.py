"""Lỗi của trình duyệt NHÚNG không được đẻ vé — nhưng lỗi thật trên cùng trang thì phải.

Trình duyệt trong ứng dụng Zalo chèn mã riêng vào mọi trang mở từ Zalo (`?zarsrc=`), mã
đó ném `zaloJSV2 is not defined` ở dòng 1. Đo prod HTS 26/08: hai người khác nhau, mỗi
lượt một vé "blocker", trong khi cùng phiên màn giao hàng ghi hàng trăm lượt `ok`.

Khoá ở NGUỒN (bundle) vì đây là thứ chỉ trình duyệt mới thấy; và khoá hai chiều, kẻo bộ
lọc nuốt luôn lỗi thật của trang khi trang được mở từ Zalo.
"""

import os
import re
import unittest

_GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CORE = os.path.join(_GOC, "public", "js", "feedback_widget_core.js")


def _than_ham(ten: str) -> str:
    src = open(_CORE, encoding="utf-8").read()
    i = src.index(f"{ten}(msg, nguon)")
    return src[i: src.index("\n    _hookErrors()", i)]


class TestLocTiengOnTrinhDuyetNhung(unittest.TestCase):
    def setUp(self):
        self.than = _than_ham("_laTiengOnTrinhDuyetNhung")

    def test_ham_ton_tai_va_bat_zalojsv2(self):
        self.assertIn("zaloJSV2", self.than)

    def test_can_ca_dau_hieu_zarsrc(self):
        """Không chỉ chặn theo một cái tên: mã nhúng có thể đổi tên biến."""
        self.assertIn("zarsrc", self.than)

    def test_khong_bo_moi_ReferenceError(self):
        """Chỉ bỏ ReferenceError mang tiền tố `zalo`, không bỏ mọi ReferenceError."""
        self.assertRegex(self.than, r"ReferenceError: zalo")
        self.assertNotRegex(self.than, r"/\^Uncaught ReferenceError/[im]*\.test")

    def test_ca_hai_cua_deu_goi_bo_loc(self):
        src = open(_CORE, encoding="utf-8").read()
        i = src.index("_hookErrors() {")
        khoi = src[i: src.index("\n    }", src.index("unhandledrejection", i))]
        self.assertEqual(len(re.findall(r"_laTiengOnTrinhDuyetNhung\(", khoi)), 2,
                         "cả cửa `error` lẫn cửa `unhandledrejection` phải lọc")
