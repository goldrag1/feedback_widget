"""Chặn ĐÚNG LUẬT mà đã biết trước thì ghi sổ, đừng đẻ vé.

Đo prod HTS 27/08: "Không đủ quyền cho Item Price" — 17 trong 27 người hoạt động mở được
mã hàng nhưng không xem được giá, và chủ đầu tư CỐ Ý giữ nguyên quyền đó. Mỗi lượt vấp
lại đẻ một vé "chặn" và bắn Telegram lúc 4h sáng cho thứ không ai định sửa.

Khai bằng DỮ LIỆU (`Feedback Settings.khong_de_ve`, mỗi dòng một mẫu) để người vận hành
tự tắt tiếng, không phải sửa mã rồi deploy ba bench. Hai chiều đều phải khoá: khai thì
im, không khai thì mọi thứ vẫn vào vé như cũ.
"""

import unittest
from unittest import mock

from feedback_widget.api import feedback


class TestChanDaBiet(unittest.TestCase):
    def _voi(self, khai):
        return mock.patch("feedback_widget.cai_dat.cai_dat", return_value={"khong_de_ve": khai})

    def test_khong_khai_thi_khong_bo_gi(self):
        with self._voi(""):
            self.assertFalse(feedback._la_chan_da_biet("Không đủ quyền cho Item Price"))

    def test_khai_thi_khop_dung_cau(self):
        with self._voi("Không đủ quyền cho Item Price"):
            self.assertTrue(feedback._la_chan_da_biet("Không đủ quyền cho <strong>Item Price</strong>"))

    def test_khong_phan_biet_hoa_thuong(self):
        with self._voi("không đủ quyền cho item price"):
            self.assertTrue(feedback._la_chan_da_biet("KHÔNG ĐỦ QUYỀN CHO ITEM PRICE"))

    def test_cau_khac_van_vao_ve(self):
        """Khoá chiều ngược: tắt tiếng một luật không được làm câm luật khác."""
        with self._voi("Không đủ quyền cho Item Price"):
            self.assertFalse(feedback._la_chan_da_biet("Không đủ quyền cho Sales Invoice"))
            self.assertFalse(feedback._la_chan_da_biet("Kho không đủ nguyên liệu để ghi nhận"))

    def test_nhieu_dong_moi_dong_mot_mau(self):
        with self._voi("Item Price\nKho không đủ nguyên liệu"):
            self.assertTrue(feedback._la_chan_da_biet("Không đủ quyền cho Item Price"))
            self.assertTrue(feedback._la_chan_da_biet("Kho không đủ nguyên liệu để ghi nhận: phiếu lấy 5.466"))

    def test_thong_diep_rong_khong_no(self):
        with self._voi("Item Price"):
            self.assertFalse(feedback._la_chan_da_biet(None))
            self.assertFalse(feedback._la_chan_da_biet(""))
