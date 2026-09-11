"""Bộ kiểm không được để lại dòng nào trong sổ góp ý JSONL của site thật.

Sổ ấy là một tệp trên ĐĨA. `rollback()` ở tearDown chỉ với tới CSDL, nên dòng
`Feedback Comment` biến mất mà dòng trên đĩa ở lại — trỏ tới một vé không tồn
tại. Tệ hơn: bộ đếm dãy tên cũng lùi theo, nên mọi dòng rò sau đó mang CÙNG một
mã vé, và một người đọc sổ sẽ tưởng một vé được gửi nhiều lần.

Đo ngày 11/09/2026 trên site thật: 4 dòng rò, mỗi dòng đánh thức phiên tự trị
canh vé trên máy chủ và tiêu một lượt xử lý 30 phút — một lượt cho đúng chuỗi
"x" của `test_cat_do_dai`. Cùng một lý do đã chặn Telegram khi đang kiểm.
"""

import frappe
from frappe.tests.classes.integration_test_case import IntegrationTestCase

from feedback_widget.api import feedback as fb


class TestKhongGhiSoJsonlKhiKiem(IntegrationTestCase):
    def _so_dong(self) -> int:
        p = fb._jsonl_path("kind_heart")
        if not p.exists():
            return 0
        with open(p, encoding="utf-8") as f:
            return sum(1 for _ in f)

    def test_collect_khong_them_dong_nao_khi_dang_kiem(self):
        truoc = self._so_dong()
        fb.collect(
            project="kind_heart",
            message="Một dòng của bộ kiểm — KHÔNG được xuống sổ trên đĩa",
            type="question",
            severity="nice",
            screen_id="kiem-thu",
            screen_name="Kiểm thử",
        )
        self.assertEqual(
            self._so_dong(),
            truoc,
            "bộ kiểm vừa ghi một dòng vào sổ góp ý của site thật — dòng ấy sống "
            "sót qua rollback và sẽ đánh thức phiên canh vé",
        )

    def test_khong_khoa_theo_bien_moi_truong_dung_de_tat_telegram(self):
        """`FBW_KHONG_GUI` nghĩa là "đừng GỬI", không phải "đừng GHI".

        Nếu cửa chặn này đọc nó, một người tắt Telegram cho đỡ ồn sẽ mất luôn hộp
        thư JSONL của mình — mất dữ liệu, và im lặng. App dùng chung cho 15 bench
        nên cái bẫy ấy sẽ đi theo bản nâng cấp tới tận nơi.
        """
        with open(fb.__file__, encoding="utf-8") as f:
            nguon = f.read()
        # CHỈ đọc khối ghi sổ JSONL. Bước Telegram ngay bên dưới dùng
        # `dang_kiem_thu()` là ĐÚNG — nó mới là bước "gửi đi".
        dau = nguon.index("# 2) Mirror raw payload")
        cuoi = nguon.index("# 3) Telegram", dau)
        # Bỏ dòng chú thích trước khi soi, nếu không phép kiểm sẽ khớp đúng cái
        # chú thích GIẢI THÍCH vì sao không dùng hàm ấy — và đỏ vì lý do sai.
        khoi = "\n".join(
            d for d in nguon[dau:cuoi].splitlines() if not d.lstrip().startswith("#")
        )
        self.assertNotIn(
            "dang_kiem_thu()",
            khoi,
            "cửa chặn sổ JSONL đang đọc hàm cũng nhận FBW_KHONG_GUI — xem docstring",
        )
        self.assertIn("in_test", khoi, "khối ghi sổ JSONL không còn cửa chặn nào")
