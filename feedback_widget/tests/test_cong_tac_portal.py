"""`enable_on_portal` phải THẬT SỰ điều khiển một thứ gì đó.

Trước 20/09/2026 ô này có trong Cài đặt, có mặc định, có trong bản vá gieo lại — và
**không một dòng mã nào đọc nó**. `vai_duoc_thay_nut` chỉ hỏi `enable_on_desk`, nên người
vận hành tắt "Hiển thị trên Mobile / Portal" thì không có gì đổi, và bật lại cũng vậy. Một
công tắc không điều khiển gì là lời hứa suông trên màn Cài đặt.

Phép này giữ hai chiều: tắt portal thì trang portal KHÔNG thấy nút, mà desk VẪN thấy —
nếu chỉ kiểm một chiều thì một bản sửa "luôn trả 0" cũng qua được.
"""

import unittest

import frappe

from feedback_widget.cai_dat import DOCTYPE, payload_cho_trinh_duyet, vai_duoc_thay_nut


class TestCongTacPortal(unittest.TestCase):
    def setUp(self):
        self.doc = frappe.get_single(DOCTYPE)
        self.cu = {k: self.doc.get(k) for k in ("enabled", "enable_on_desk", "enable_on_portal")}

    def tearDown(self):
        for k, v in self.cu.items():
            frappe.db.set_single_value(DOCTYPE, k, v)
        frappe.clear_cache()

    def _dat(self, **kw):
        for k, v in kw.items():
            frappe.db.set_single_value(DOCTYPE, k, v)
        frappe.clear_cache()

    def test_tat_portal_thi_portal_mat_nut_con_desk_van_co(self):
        self._dat(enabled=1, enable_on_desk=1, enable_on_portal=0)
        self.assertEqual(vai_duoc_thay_nut(noi="portal"), 0,
                         "tắt enable_on_portal mà trang portal vẫn thấy nút")
        self.assertEqual(vai_duoc_thay_nut(noi="desk"), 1,
                         "tắt portal KHÔNG được làm desk mất nút")

    def test_tat_desk_thi_desk_mat_nut_con_portal_van_co(self):
        self._dat(enabled=1, enable_on_desk=0, enable_on_portal=1)
        self.assertEqual(vai_duoc_thay_nut(noi="desk"), 0)
        self.assertEqual(vai_duoc_thay_nut(noi="portal"), 1,
                         "tắt desk KHÔNG được làm portal mất nút")

    def test_mac_dinh_van_la_desk(self):
        """Mọi lời gọi cũ không truyền `noi` phải chạy y như trước."""
        self._dat(enabled=1, enable_on_desk=1, enable_on_portal=0)
        self.assertEqual(vai_duoc_thay_nut(), vai_duoc_thay_nut(noi="desk"))

    def test_payload_portal_mang_du_khoa_thu_thap(self):
        """Thiếu một khoá là bundle rơi vào nhánh 'không tự thu' — sổ 0 dòng, không lỗi."""
        self._dat(enabled=1, enable_on_desk=1, enable_on_portal=1)
        p = payload_cho_trinh_duyet(noi="portal")
        for k in ("show_widget", "collect_usage", "usage_sample_pct", "throttle_minutes",
                  "max_events_per_minute", "auto_report", "project"):
            self.assertIn(k, p, f"payload portal thiếu khoá `{k}`")
        self.assertEqual(p["show_widget"], 1)
