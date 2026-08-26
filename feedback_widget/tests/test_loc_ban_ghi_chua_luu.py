"""Vé giả từ bản ghi CHƯA LƯU không được chen vào hàng đợi vé thật.

Desk hỏi quyền cho biểu mẫu mới qua `frappe.realtime.has_permission` với tên cục bộ
(`new-sales-order-ppggarjhfe`); Frappe ném `DoesNotExistError` và cầu Error Log biến nó
thành vé "blocker". Đo prod HTS 26/08: **9 trong 22 vé đang mở** là loại này, mỗi vé mang
một mã ngẫu nhiên riêng nên bộ gộp theo chữ ký không dồn được — hàng đợi trông như 22 sự
cố trong khi chỉ có 13.

Khoá hai chiều: đúng cặp (tên chưa lưu + không-tìm-thấy) thì bỏ; mọi thứ khác giữ, kể cả
lỗi THẬT xảy ra trên chính bản ghi chưa lưu đó (người dùng đang nhập dở và bị chặn).
"""

import unittest

from feedback_widget.tac_vu import _la_ban_ghi_chua_luu


class TestLocBanGhiChuaLuu(unittest.TestCase):
    def test_bo_dung_ca_desk_hoi_quyen(self):
        self.assertTrue(_la_ban_ghi_chua_luu(
            "frappe.exceptions.DoesNotExistError: Đơn bán hàng new-sales-order-ppggarjhfe không tìm thấy",
            "Đơn bán hàng new-sales-order-ppggarjhfe không tìm thấy"))

    def test_bo_ca_doctype_nhieu_tu(self):
        self.assertTrue(_la_ban_ghi_chua_luu(
            "frappe.exceptions.DoesNotExistError: Purchase Receipt new-purchase-receipt-jcqbjehadj not found", ""))

    def test_giu_loi_that_tren_ban_ghi_chua_luu(self):
        """Người dùng đang nhập dở và BỊ CHẶN — đó là vé thật, không phải tiếng ồn."""
        self.assertFalse(_la_ban_ghi_chua_luu(
            "frappe.exceptions.ValidationError: Công ty là bắt buộc",
            "new-sales-order-ppggarjhfe"))

    def test_giu_khong_tim_thay_tren_ban_ghi_THAT(self):
        """Chứng từ đã lưu mà 'không tìm thấy' là sự cố thật — dữ liệu hoặc quyền."""
        self.assertFalse(_la_ban_ghi_chua_luu(
            "frappe.exceptions.DoesNotExistError: Đơn bán hàng SO-2026-00123 không tìm thấy", ""))

    def test_giu_khi_khong_co_ten_ban_ghi(self):
        self.assertFalse(_la_ban_ghi_chua_luu("frappe.exceptions.DoesNotExistError: Report not found", ""))

    def test_khong_nham_voi_chuoi_co_chu_new(self):
        """`newsletter-abc` hay `new-item` (thiếu đuôi 10 ký tự) không phải tên cục bộ."""
        self.assertFalse(_la_ban_ghi_chua_luu(
            "frappe.exceptions.DoesNotExistError: Newsletter new-item không tìm thấy", ""))
