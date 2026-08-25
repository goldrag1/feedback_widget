"""Chữ ký phải GOM cùng một loại sự cố và TÁCH hai loại khác nhau.

Đây là trục của cả tính năng: gom sai thì hộp thư ngập vé trùng, tách sai thì hai lỗi
khác nhau đội lốt một vé và một trong hai không bao giờ được sửa.
"""

import unittest

from feedback_widget.chu_ky import chu_ky, chuan_hoa, dau_hieu


class TestChuKy(unittest.TestCase):
	def test_cung_luat_khac_ma_lo_thi_GOM(self):
		a = "[KHACCUON] Băng N102507938_01 xả ra từ cuộn N102507938_01 — lệnh xả từ cuộn N1025079"
		b = "[KHACCUON] Băng 66M22507260531 xả ra từ cuộn 66M22507260531 — lệnh xả từ cuộn 66M225"
		self.assertEqual(chu_ky(a, "ep", "chan"), chu_ky(b, "ep", "chan"))

	def test_cung_cau_khac_SO_thi_GOM(self):
		a = "Kho không đủ nguyên liệu: phiếu lấy 5,466.48 kg, lô 66M2220 chỉ 812 kg"
		b = "Kho không đủ nguyên liệu: phiếu lấy 1,200.00 kg, lô 39M1120 chỉ 44 kg"
		self.assertEqual(chu_ky(a, "ep", "chan"), chu_ky(b, "ep", "chan"))

	def test_hai_luat_khac_nhau_thi_TACH(self):
		a = "[KHACCUON] Băng của cuộn khác"
		b = "[MAYBAN] Máy đang chạy cuộn khác"
		self.assertNotEqual(chu_ky(a, "ep", "chan"), chu_ky(b, "ep", "chan"))

	def test_cung_dau_hieu_khac_ENDPOINT_thi_TACH(self):
		"""Một dấu hiệu dùng ở hai chỗ là hai chỗ tắc khác nhau với người đứng máy."""
		a = "[THIEUCAN] Chưa cân đủ đầu ra"
		self.assertNotEqual(chu_ky(a, "ghi_nhan", "chan"), chu_ky(a, "dong_bo", "chan"))

	def test_dau_hieu_may_doc(self):
		self.assertEqual(dau_hieu("[XINDUYET] Cân không khớp"), "XINDUYET")
		self.assertEqual(dau_hieu("không có dấu hiệu"), "")

	def test_bo_the_HTML_cua_frappe_throw(self):
		"""`frappe.throw` chèn <strong>/<a href> — hai lần cùng một lỗi khác link phải GOM."""
		a = 'Lô <strong><a href="/desk/batch/A1">A1</a></strong> âm kho'
		b = 'Lô <strong><a href="/desk/batch/B2">B2</a></strong> âm kho'
		self.assertEqual(chu_ky(a, "x", "chan"), chu_ky(b, "x", "chan"))
		# Kiểm THẺ đã bị bóc, không kiểm ký tự "<": chuỗi chuẩn hoá CÓ "<ma>"/"<so>" là
		# ký hiệu thay thế do chính hàm sinh ra (phép kiểm đầu tiên viết ra đã bắt nhầm nó).
		xong = chuan_hoa(a)
		for the in ("strong", "href", "</a>"):
			self.assertNotIn(the, xong)
