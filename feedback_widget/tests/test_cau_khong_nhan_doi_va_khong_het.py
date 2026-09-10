"""Cầu Error Log: không nhân đôi vé, và không hét khi luật nghiệp vụ chạy đúng.

Hai lỗi đo được trên site `asxh` tối 10/09/2026, cùng một sự cố:

    FB-2026-00013  trình duyệt  "Chỉ ban điều hành mới xem được…"  annoying
    FB-2026-00014  cầu          "frappe.exceptions.PermissionError: Chỉ ban…"  blocker

Cùng giây, hai chữ ký, hai mức nặng. Và cả hai đều là một đường "vào nhầm vai" mà
GIAO DIỆN đã xử lý tử tế — người dùng được chỉ sang đúng màn của họ.

Hệ quả: tối đó hộp thư có 5 vé rác đỏ và 2 vé thật, trong đó vé thật là một lỗi
chặn hẳn đường mở tài khoản người nhận. Đỏ mà không phải việc gấp là cách chắc
chắn để người ta ngừng nhìn màu đỏ.

Cả hai phép chống đã có sẵn trong app — `_trinh_duyet_da_bao` viết cho SỔ sự kiện,
`_loai_su_kien` phân biệt `chan`/`loi` cho bảng xếp hạng — nhưng không phép nào
được áp cho VÉ. Bài kiểm này khoá cả hai lại.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget import tac_vu
from feedback_widget.tests.nen_cau import NenCau

CAU_CHAN = "Chỉ ban điều hành mới xem được danh sách chi trả"
CHAN = ("Traceback (most recent call last):\n  File \"x.py\", line 1\n"
        f"frappe.exceptions.PermissionError: {CAU_CHAN}")
HONG = ("Traceback (most recent call last):\n  File \"x.py\", line 1\n"
        "builtins.TypeError: cannot read properties of undefined")


class TestCauKhongNhanDoi(NenCau, FrappeTestCase):
	def setUp(self):
		self._giu_hien_truong()
		frappe.set_user("Administrator")
		# Giữ mốc cũ — xem tearDown.
		self._moc_cu = frappe.db.get_global(tac_vu.MOC)
		self._don()
		frappe.db.set_global(tac_vu.MOC, "")
		tac_vu.bac_cau_error_log()      # đặt mốc = bây giờ
		frappe.db.commit()

	def tearDown(self):
		self._tra_hien_truong()
		self._don()
		# Trả lại mốc: bỏ trắng thì lần chạy cầu tiếp theo trên site ấy đọc lại
		# TOÀN BỘ lịch sử Error Log và đẻ vé trùng cho lỗi đã xử lý xong.
		if self._moc_cu:
			frappe.db.set_global(tac_vu.MOC, self._moc_cu)
			frappe.db.commit()

	def _don(self):
		frappe.db.delete("Feedback Comment", {"screen_id": ["in", ("viec-nen", "man-thu")]})
		frappe.db.delete("Feedback Event", {"screen_id": ["in", ("viec-nen", "man-thu")]})
		frappe.db.commit()

	def _log(self, noi_dung, method="kiemthu"):
		d = frappe.get_doc({"doctype": "Error Log", "method": method,
		                    "error": noi_dung}).insert(ignore_permissions=True)
		frappe.db.commit()
		return d

	def _su_kien_trinh_duyet(self, cau, luc):
		"""Dòng sổ mà WIDGET ghi từ trình duyệt cho cùng sự cố."""
		frappe.get_doc({
			"doctype": "Feedback Event", "project": "kiemthu", "kind": "chan",
			"ts": luc, "user": "Administrator", "screen_id": "man-thu",
			"screen_name": "Màn thử", "endpoint": "app.api.mot_ham",
			"outcome": "chan", "signature": "CHUKY-TRINH-DUYET", "message": cau,
		}).insert(ignore_permissions=True)
		frappe.db.commit()

	# ---- 1. không nhân đôi vé -------------------------------------------
	def test_trinh_duyet_da_bao_thi_cau_KHONG_dung_them_ve(self):
		r = self._log(CHAN)
		self._su_kien_trinh_duyet(CAU_CHAN, r.creation)
		kq = tac_vu.bac_cau_error_log()
		self.assertEqual(kq["ve"], 0, "cùng một sự cố ra hai vé")
		self.assertEqual(frappe.db.count("Feedback Comment", {"screen_id": "viec-nen"}), 0)

	def test_trinh_duyet_KHONG_bao_thi_cau_van_dung_ve(self):
		"""Đường nền không có trình duyệt nào để tự báo — đó là lý do cầu tồn tại."""
		self._log(CHAN)
		kq = tac_vu.bac_cau_error_log()
		self.assertEqual(kq["ve"], 1, "cầu im lặng luôn thì mất điểm mù của đường nền")

	def test_su_co_KHAC_trong_cung_khoang_thoi_gian_van_dung_ve(self):
		"""Chống trùng không được nuốt một sự cố khác chỉ vì nó xảy ra cùng lúc."""
		r = self._log(HONG)
		self._su_kien_trinh_duyet(CAU_CHAN, r.creation)
		self.assertEqual(tac_vu.bac_cau_error_log()["ve"], 1)

	# ---- 2. mức nặng theo lớp lỗi ---------------------------------------
	def test_bi_chan_dung_luat_thi_KHONG_phai_blocker(self):
		self._log(CHAN)
		tac_vu.bac_cau_error_log()
		ve = frappe.get_all("Feedback Comment", filters={"screen_id": "viec-nen"},
		                    fields=["tag_severity", "message"])
		self.assertEqual(len(ve), 1)
		self.assertEqual(ve[0].tag_severity, "annoying",
		                 "luật nghiệp vụ chạy ĐÚNG vẫn bị gắn cờ đỏ")

	def test_phan_mem_HONG_van_la_blocker(self):
		self._log(HONG)
		tac_vu.bac_cau_error_log()
		ve = frappe.get_all("Feedback Comment", filters={"screen_id": "viec-nen"},
		                    fields=["tag_severity"])
		self.assertEqual(len(ve), 1)
		self.assertEqual(ve[0].tag_severity, "blocker",
		                 "phần mềm hỏng mà không còn báo đỏ thì cầu mất tác dụng")

	def test_muc_nang_khop_voi_phan_loai_cua_chinh_app(self):
		"""Một luật, một chỗ: `_muc_nang` phải đi theo `_loai_su_kien`, không tự nghĩ."""
		for cau, mong in ((f"frappe.exceptions.PermissionError: {CAU_CHAN}", "annoying"),
		                  ("frappe.exceptions.ValidationError: thiếu kho", "annoying"),
		                  ("builtins.TypeError: x", "blocker"),
		                  ("builtins.KeyError: 'a'", "blocker")):
			self.assertEqual(tac_vu._muc_nang(cau), mong, cau)


class TestBaiKiemKhongDeLaiDauChan(FrappeTestCase):
	"""Bài kiểm nào ĐỤNG vào mốc đọc thì phải TRẢ LẠI.

	Mốc là trạng thái toàn site, không phải trạng thái của bài kiểm. Bỏ trắng mà
	không trả lại thì lần chạy cầu tiếp theo — việc theo lịch, trên site thật —
	đọc lại toàn bộ lịch sử Error Log và đẻ vé trùng cho những lỗi đã xử lý xong.
	Đo trên site asxh 10/09/2026: chạy bộ kiểm xong, hộp thư có thêm 6 vé như thế,
	và không có gì trong bộ kiểm báo động.

	Không kiểm được bằng cách chạy — thứ tự bài kiểm không bảo đảm — nên đọc thẳng
	mã nguồn của chính thư mục này.
	"""

	def test_moi_bai_kiem_chay_cau_deu_dung_nen(self):
		import os, re
		thu_muc = os.path.dirname(os.path.abspath(__file__))
		pham = []
		for ten in sorted(os.listdir(thu_muc)):
			if not ten.startswith("test_") or not ten.endswith(".py"):
				continue
			nguon = open(os.path.join(thu_muc, ten), encoding="utf-8").read()
			chay_cau = re.search(r"bac_cau_error_log|khai_thac_lich_su", nguon)
			dung_moc = re.search(r"set_global\(\s*tac_vu\.MOC", nguon)
			if not (chay_cau or dung_moc):
				continue
			if "NenCau" not in nguon:
				pham.append(ten)
		self.assertEqual(pham, [],
		                 f"bài kiểm chạy cầu mà không dùng NenCau — sẽ để lại vé thật "
		                 f"của site trong hộp thư: {pham}")
