"""Mọi khoá cấu hình bundle ĐỌC đều phải có người NHỒI vào boot.

Vì sao có tệp này: bundle cố ý có nhánh an toàn "boot rỗng ⇒ KHÔNG tự thu" (không bao giờ
bật một thứ ghi dữ liệu bằng suy đoán). Nhánh ấy đúng, nhưng nó biến "quên nối cửa boot"
thành một tính năng câm: đo trên gương HTS 26/08 sau khi cài từ HEAD — nút góp ý hiện, vé gửi
được, sổ sự kiện 0 dòng, 0 lỗi console, 0 request hỏng. Không có phép kiểm nào bắt được, vì
mọi thứ đều "chạy".
"""

import importlib
import os
import re

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget import hooks

_GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BUNDLE = os.path.join(_GOC, "public", "js", "feedback_widget.bundle.js")


def _khoa_bundle_doc() -> set[str]:
	"""`ct.<khoá>` mà bundle đọc — `ct` là cấu hình THU THẬP lấy từ boot."""
	src = open(_BUNDLE, encoding="utf-8").read()
	return set(re.findall(r"\bct\.([a-z_][a-z0-9_]*)\b", src))


def _boot_sau_moi_cua() -> frappe._dict:
	"""Chạy MỌI hook boot khai trong hooks.py, đúng như Frappe làm."""
	boot = frappe._dict()
	for ten in ("extend_bootinfo", "boot_session"):
		duong = getattr(hooks, ten, None)
		if not duong:
			continue
		mod, fn = duong.rsplit(".", 1)
		ham = getattr(importlib.import_module(mod), fn, None)
		# Hook trỏ tới hàm KHÔNG tồn tại là trạng thái chuyển tiếp hợp lệ (26/08: một phiên
		# khác đang đổi tên `cai_dat.boot_session`), và Frappe cũng chỉ ghi log rồi đi tiếp.
		# Ca này đo KẾT QUẢ — payload có hay không — chứ không đo cửa nào sinh ra nó.
		if ham is None:
			continue
		ham(boot)
	return boot


class TestBootPayload(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_bundle_doc_khoa_nao_thi_boot_phai_co_khoa_do(self):
		boot = _boot_sau_moi_cua()
		thu = boot.get("feedback_widget")
		self.assertIsInstance(thu, dict, "không cửa boot nào nhồi `feedback_widget` (payload THU THẬP)")
		thieu = sorted(k for k in _khoa_bundle_doc() if k not in thu)
		self.assertEqual(thieu, [], f"bundle đọc khoá không ai nhồi: {thieu}")

	def test_van_con_payload_HIEN_THI(self):
		"""Hai payload song song — thêm cửa này không được làm mất cửa kia."""
		boot = _boot_sau_moi_cua()
		ht = boot.get("feedback_widget_settings")
		self.assertIsInstance(ht, dict)
		for k in ("enabled", "is_eligible"):
			self.assertIn(k, ht)

	def test_cong_tac_thu_thap_ve_dung_KIEU(self):
		"""`collectUsage: !!ct.collect_usage` — trả chuỗi/None là bật/tắt sai mà không ai thấy."""
		thu = _boot_sau_moi_cua().get("feedback_widget") or {}
		self.assertIn(type(thu.get("collect_usage")), (int, bool),
			f"collect_usage kiểu {type(thu.get('collect_usage'))}")
