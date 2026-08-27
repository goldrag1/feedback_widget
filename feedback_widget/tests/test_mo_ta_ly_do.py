"""Lý do bị từ chối phải ĐỌC ĐƯỢC — không được ra "[object Object]".

Đo prod Tâm Định 27/08/2026: một lượt lỗi của người dùng ghi đúng một dòng
"Promise: [object Object]", không có Error Log máy chủ nào kèm theo ⇒ không ai biết chị ấy
vấp cái gì, và cái vé ấy bằng không có vé. Nguyên nhân: `String(reason)` với mọi lý do
KHÔNG phải Error — mà Frappe từ chối bằng đối tượng thường `{exception, _server_messages}`
hoặc jqXHR.

Test này CHẠY THẬT hàm trong `feedback_widget_core.js` bằng node (trích theo cân bằng
ngoặc), không đọc chuỗi nguồn: khoá HÀNH VI chứ không khoá cách viết.
"""

import json
import os
import subprocess
import unittest

_GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_JS = os.path.join(_GOC, "public", "js", "feedback_widget_core.js")


def _trich_ham(ten: str) -> str:
    src = open(_JS, encoding="utf-8").read()
    i = src.index(ten + "(r) {")
    j = src.index("{", i)
    sau, k = 1, j + 1
    while sau and k < len(src):
        if src[k] == "{":
            sau += 1
        elif src[k] == "}":
            sau -= 1
        k += 1
    return src[i:k]


class TestMoTaLyDo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ham = _trich_ham("_moTaLyDo")

    def _chay(self, cac_ly_do):
        js = (
            "class T { " + self.ham + " }\n"
            "const t = new T();\n"
            "const vao = " + json.dumps(cac_ly_do) + ";\n"
            "console.log(JSON.stringify(vao.map((x) => t._moTaLyDo(x))));\n"
        )
        r = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_cau_cua_may_chu_duoc_boc_ra(self):
        sm = json.dumps([json.dumps({"message": "<b>Lô này</b> đã xuất kho rồi."})])
        ra = self._chay([
            {"_server_messages": sm},
            {"responseJSON": {"_server_messages": sm}},
        ])
        for x in ra:
            self.assertEqual(x, "Lô này đã xuất kho rồi.")

    def test_cac_hinh_dang_con_lai_deu_noi_duoc_dieu_gi_do(self):
        ra = self._chay([
            {"exception": "frappe.exceptions.ValidationError: thiếu kho"},
            {"message": "x is not a function"},
            {"status": 502, "statusText": "Bad Gateway"},
            {"khoa_la": 1, "khoa_khac": "abc"},
            "chuỗi thường",
        ])
        self.assertIn("thiếu kho", ra[0])
        self.assertEqual(ra[1], "x is not a function")
        self.assertIn("502", ra[2])
        self.assertIn("khoa_la", ra[3])
        self.assertEqual(ra[4], "chuỗi thường")

    def test_khong_bao_gio_tra_ve_object_object(self):
        """Kể cả đối tượng KHÔNG serialize được (vòng lặp tham chiếu, getter ném lỗi)."""
        js = (
            "class T { " + self.ham + " }\n"
            "const t = new T();\n"
            "const vong = { ten: 'a' }; vong.tu = vong;\n"
            "const nem = { get xau() { throw new Error('no'); }, ma: 7 };\n"
            "const rong = Object.create(null);\n"
            "const ra = [vong, nem, rong, null, undefined].map((x) => t._moTaLyDo(x));\n"
            "console.log(JSON.stringify(ra));\n"
        )
        r = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        ra = json.loads(r.stdout.strip().splitlines()[-1])
        for x in ra:
            self.assertNotIn("[object Object]", x or "")
        self.assertIn("ten", ra[0])   # vòng lặp: vẫn phải nêu được tên khoá
        self.assertIn("ma", ra[1])    # getter ném lỗi: vẫn phải nêu được tên khoá
