"""Ghi mốc đọc Error Log KHÔNG được xoá trắng cache của site.

Vì sao có bài này (23/09/2026): `frappe.db.set_global` đi tới `frappe.clear_cache()` không tham
số = xoá MỌI khoá cache của site. Cùng lớp lỗi ở `misa_bridge` làm token đọc của trợ lý chết giữa
lượt hỏi ("kết nối lấy số liệu vừa hết hạn giữa chừng"). Đo ngược: với `set_global`, khoá cache
thử biến mất (None); với `_ghi_moc`, nó còn.
"""
import ast
import inspect
import unittest

import frappe

from feedback_widget import tac_vu


class TestMocKhongXoaCache(unittest.TestCase):
	def setUp(self):
		self.cu = frappe.db.get_global(tac_vu.MOC)

	def tearDown(self):
		if self.cu:
			tac_vu._ghi_moc(self.cu)
		else:
			frappe.db.delete("DefaultValue", {"parent": "__global", "defkey": tac_vu.MOC})
			frappe.cache_manager.clear_defaults_cache("__global")
		frappe.cache.delete_value("feedback_widget:thu:con_song")
		frappe.db.commit()

	def test_khoa_khac_con_song_va_doc_ra_ban_moi(self):
		frappe.cache.set_value("feedback_widget:thu:con_song", "con", expires_in_sec=60)
		tac_vu._ghi_moc("2026-09-23 00:00:00.000001")
		self.assertEqual(frappe.cache.get_value("feedback_widget:thu:con_song"), "con")
		self.assertEqual(frappe.db.get_global(tac_vu.MOC), "2026-09-23 00:00:00.000001")
		tac_vu._ghi_moc("2026-09-23 00:00:00.000002")      # ghi đè, không đẻ dòng thứ hai
		self.assertEqual(frappe.db.get_global(tac_vu.MOC), "2026-09-23 00:00:00.000002")
		self.assertEqual(frappe.db.count("DefaultValue",
			{"parent": "__global", "defkey": tac_vu.MOC}), 1)

	def test_tac_vu_khong_goi_set_global(self):
		goi = [n for n in ast.walk(ast.parse(inspect.getsource(tac_vu)))
		       if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		       and n.func.attr in ("set_global", "set_default")]
		self.assertEqual(goi, [], "tac_vu gọi set_global/set_default = xoá trắng cache site")
