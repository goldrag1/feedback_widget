"""Tiếng ồn của TRÌNH DUYỆT không được đẻ vé.

Hai loại đã đo được trên site thật:
  • `zaloJSV2 is not defined` — trình duyệt trong Zalo chèn mã của họ vào mọi trang mở từ
    Zalo; trang vẫn chạy bình thường (prod HTS 26/08: 2 người, mỗi lượt một vé "blocker").
  • `ResizeObserver loop completed with undelivered notifications` — trình duyệt bắn khi vòng
    đo kích thước chưa xong trong một khung hình rồi tự chạy tiếp ở khung sau; không có gì
    hỏng, không ai mất thao tác (site demo 28/08: 1 vé của tài khoản giám đốc).

Một vé không nói được điều gì để sửa là vé làm loãng hàng đợi — và hàng đợi loãng thì người
ta thôi đọc. Test CHẠY THẬT hàm lọc trong bundle bằng node.
"""

import json
import os
import subprocess
import unittest

_GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_JS = os.path.join(_GOC, "public", "js", "feedback_widget_core.js")


def _trich(ten: str) -> str:
    src = open(_JS, encoding="utf-8").read()
    i = src.index(ten + "(msg, nguon) {")
    j = src.index("{", i)
    sau, k = 1, j + 1
    while sau and k < len(src):
        if src[k] == "{":
            sau += 1
        elif src[k] == "}":
            sau -= 1
        k += 1
    return src[i:k]


class TestTiengOnTrinhDuyet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ham = _trich("_laTiengOnTrinhDuyetNhung")

    def _loc(self, cap):
        js = ("global.location = { href: 'https://x.test/desk' };\n"
              "class T { " + self.ham + " }\n"
              "const t = new T();\n"
              "const vao = " + json.dumps(cap) + ";\n"
              "console.log(JSON.stringify(vao.map((x) => t._laTiengOnTrinhDuyetNhung(x[0], x[1]))));\n")
        r = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_bo_dung_tieng_on_da_biet(self):
        ra = self._loc([
            ["ResizeObserver loop completed with undelivered notifications.", ""],
            ["Uncaught ResizeObserver loop limit exceeded", ""],
            ["ReferenceError: zaloJSV2 is not defined", ""],
        ])
        self.assertEqual(ra, [True, True, True])

    def test_GIU_lai_loi_that(self):
        """Lọc quá tay còn tệ hơn: lỗi thật biến mất và không ai biết."""
        ra = self._loc([
            ["TypeError: x is not a function", ""],
            ["ReferenceError: boDau is not defined", ""],
            ["Uncaught (in promise) Error: Lỗi máy chủ", ""],
            ["ResizeObserver is not defined", ""],
        ])
        self.assertEqual(ra, [False, False, False, False],
                         "một lỗi THẬT vừa bị bộ lọc nuốt mất")
