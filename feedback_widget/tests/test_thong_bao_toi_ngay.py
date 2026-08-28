"""Thông báo phải tới NGAY, không chờ người dùng tải lại trang.

Vì sao có tệp này: trước 28/08 widget chỉ hỏi máy chủ ĐÚNG MỘT LẦN mỗi lần tải trang, nên
gửi thông báo xong người nhận không thấy gì cho tới lúc họ tự F5 — không lỗi, không dấu vết,
và người gửi tưởng đã báo rồi. Ba tính chất khoá ở đây, mỗi cái từng là một cách hỏng thật:

 1. **Máy chủ phải bắn phao** khi thông báo được tạo/bật lại — nếu không, cả cơ chế realtime
    chỉ là mã chết bên trình duyệt.
 2. **Phao không được mang nội dung**: "Nhóm vai"/"Tất cả" phải phát vào phòng chung của
    site (Frappe không có phòng theo vai), nên nhét tiêu đề vào phao là rò thông báo riêng
    của một người sang mọi máy đang mở.
 3. **Hai bên gọi CÙNG một tên sự kiện, và vẫn còn đường lui khi socket chết** — đổi tên một
    bên, hoặc bỏ nhịp hỏi lại, đều đưa tính năng về đúng cái bệnh nó chữa mà không ai thấy.

Chạy:
  cd <gốc bench> && env/bin/python -m unittest feedback_widget.tests.test_thong_bao_toi_ngay
"""

import json
import os
import re
import unittest

import frappe

# .../<bench>/apps/feedback_widget/feedback_widget/tests/<file>.py → lên 4 cấp là gốc bench.
# SUY RA, không đóng đinh: mã nguồn còn được sửa trong slot phiên, tên đóng đinh sẽ khiến
# test chạy ở slot mà ghi vào site của bench chính.
_GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH_ROOT = os.path.abspath(os.path.join(_GOC_APP, "..", "..", ".."))
SITES_PATH = os.path.join(BENCH_ROOT, "sites")
BUNDLE = os.path.join(_GOC_APP, "public", "js", "feedback_widget.bundle.js")


def _site() -> str:
	with open(os.path.join(SITES_PATH, "common_site_config.json")) as fh:
		return json.load(fh)["default_site"]


def _khoi_dong_frappe():
	if not getattr(frappe.local, "site", None):
		os.chdir(SITES_PATH)          # Frappe ghi log theo đường dẫn tương đối
		frappe.init(site=_site(), sites_path=SITES_PATH)
		frappe.connect()


NGUOI_A = "thu-tbn-a@kiemthu.local"
NGUOI_B = "thu-tbn-b@kiemthu.local"


class BatPhao:
	"""Thay `frappe.publish_realtime` để ĐẾM phao, thay vì tin là nó có được gọi.

	Bắt ở đúng chỗ mã sản xuất gọi (`frappe.publish_realtime`), nên nó chứng minh cả dây
	nối controller → hàm bắn, không chỉ chứng minh hàm bắn tự nó chạy được.
	"""

	def __enter__(self):
		from feedback_widget.api.thong_bao import SU_KIEN

		self.tat_ca = []
		self._su_kien = SU_KIEN
		self._cu = frappe.publish_realtime
		frappe.publish_realtime = lambda *a, **kw: self.tat_ca.append((a, kw))
		return self

	def __exit__(self, *_e):
		frappe.publish_realtime = self._cu
		return False

	@property
	def goi(self) -> list:
		"""CHỈ phao của mình. Frappe tự bắn `doc_update`/`list_update` cho mọi lượt lưu —
		đếm cả chúng thì mọi ca đều 'có bắn' và bộ test này không chứng minh gì."""
		return [(a, kw) for a, kw in self.tat_ca if a and a[0] == self._su_kien]


class TestThongBaoToiNgay(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		_khoi_dong_frappe()
		frappe.set_user("Administrator")
		for email in (NGUOI_A, NGUOI_B):
			if not frappe.db.exists("User", email):
				frappe.get_doc({"doctype": "User", "email": email, "send_welcome_email": 0,
				                "first_name": email.split("@")[0]}).insert(ignore_permissions=True)
		frappe.db.commit()

	def tearDown(self):
		for n in frappe.get_all("Feedback Notice", filters={"tieu_de": ["like", "THU-NGAY-%"]},
		                        pluck="name"):
			frappe.db.delete("Feedback Notice Seen", {"thong_bao": n})
			frappe.delete_doc("Feedback Notice", n, force=True, ignore_permissions=True)
		frappe.db.commit()

	def _tao(self, pham_vi, nguoi=None, bat=1):
		return frappe.get_doc({
			"doctype": "Feedback Notice", "tieu_de": "THU-NGAY-mot-thong-bao",
			"noi_dung": "Thẻ việc nay hiện KL còn lại.", "duong_dan": "#/viec-cua-toi",
			"pham_vi": pham_vi, "dang_bat": bat,
			"cac_nguoi": [{"user": u} for u in (nguoi or [])],
		}).insert(ignore_permissions=True)

	# --- 1. máy chủ có bắn phao không, và bắn tới ĐÚNG ai ---

	def test_mot_nguoi_thi_chi_ban_cho_nguoi_do(self):
		with BatPhao() as p:
			self._tao("Một người", nguoi=[NGUOI_A])
		nhan = [kw.get("user") for _a, kw in p.goi]
		self.assertEqual(nhan, [NGUOI_A],
		                 f"phao phải tới đúng một người nhận, đang thấy {nhan}")
		self.assertTrue(all(kw.get("after_commit") for _a, kw in p.goi),
		                "bắn trước khi commit: trình duyệt hỏi lại kịp trước lúc dòng có "
		                "trong CSDL và nhận về rỗng — thông báo lại chỉ tới sau F5")

	def test_tat_ca_thi_phat_phong_chung_va_KHONG_mang_noi_dung(self):
		with BatPhao() as p:
			self._tao("Tất cả")
		self.assertEqual(len(p.goi), 1, "phạm vi 'Tất cả' phải phát đúng một lượt")
		args, kw = p.goi[0]
		self.assertIsNone(kw.get("user"), "phát cho cả nhà thì không được gắn user")
		tin = json.dumps(args[1] if len(args) > 1 else kw.get("message") or {}, ensure_ascii=False)
		for ro in ("THU-NGAY", "Thẻ việc nay", "#/viec-cua-toi"):
			self.assertNotIn(ro, tin,
			                 "phao phát vào phòng chung mà mang nội dung = rò thông báo "
			                 "riêng sang mọi máy đang mở; phao chỉ được nói 'có cái mới'")

	def test_tat_thi_khong_ban(self):
		with BatPhao() as p:
			self._tao("Một người", nguoi=[NGUOI_A], bat=0)
		self.assertEqual(p.goi, [], "thông báo đang tắt mà vẫn bắn phao")

	def test_sua_vat_khong_ban_lai_nhung_bat_lai_thi_co(self):
		d = self._tao("Một người", nguoi=[NGUOI_A], bat=0)
		with BatPhao() as p:
			d.project = "thu-nghiem"
			d.save(ignore_permissions=True)
		self.assertEqual(p.goi, [], "sửa một trường người nhận không thấy mà vẫn nảy thẻ lần nữa")
		with BatPhao() as p:
			d.dang_bat = 1
			d.save(ignore_permissions=True)
		self.assertEqual([kw.get("user") for _a, kw in p.goi], [NGUOI_A],
		                 "bật lại một thông báo đã tắt thì phải tới ngay")

	def test_them_nguoi_nhan_thi_ban_cho_ca_hai(self):
		d = self._tao("Một người", nguoi=[NGUOI_A])
		with BatPhao() as p:
			d.append("cac_nguoi", {"user": NGUOI_B})
			d.save(ignore_permissions=True)
		self.assertEqual(sorted(kw.get("user") for _a, kw in p.goi), sorted([NGUOI_A, NGUOI_B]),
		                 "thêm người nhận là thay đổi bảng con — `has_value_changed` không "
		                 "thấy, phải so danh sách người nhận trước/sau")

	# --- 2. bên trình duyệt có nghe không, và có đường lui khi socket chết không ---

	def _bundle(self) -> str:
		with open(BUNDLE, encoding="utf-8") as fh:
			return re.sub(r"\s+", " ", fh.read())

	def test_js_nghe_dung_ten_su_kien_cua_may_chu(self):
		from feedback_widget.api.thong_bao import SU_KIEN

		src = self._bundle()
		self.assertRegex(src, r'SU_KIEN_THONG_BAO\s*=\s*"' + re.escape(SU_KIEN) + '"',
		                 f"bundle phải khai đúng tên sự kiện '{SU_KIEN}' của máy chủ — lệch "
		                 "một bên là máy chủ bắn vào chỗ không ai nghe, không lỗi nào để lần ra")
		# Người nghe phải là REALTIME, và phải được NỐI DÂY: một hàm nghe khai xong mà
		# không ai gọi thì test vẫn xanh còn tính năng thì chết (lớp lỗi "0 chỗ gọi").
		than = re.search(r"function ngheRealtime\(\) \{.*?\n?\s*\}\s*ngheRealtime\(\);", src)
		self.assertIsNotNone(than, "không thấy `ngheRealtime()` được khai VÀ được gọi")
		self.assertIn("frappe.realtime", than.group(0), "phải nghe qua `frappe.realtime`")
		self.assertRegex(than.group(0), r"\.on\(\s*SU_KIEN_THONG_BAO",
		                 "phải đăng ký `.on(SU_KIEN_THONG_BAO, …)`")

	def test_js_con_duong_lui_khi_socket_chet(self):
		src = self._bundle()
		self.assertIn("setInterval", src,
		              "mất nhịp hỏi lại thì site không có socketio (hoặc socket chết giữa "
		              "phiên) sẽ KHÔNG BAO GIỜ nhận được thông báo — đúng bệnh đang chữa")
		self.assertIn("visibilitychange", src, "quay lại tab phải hỏi lại")
		self.assertRegex(src, r"socketSong\(\)\s*\?\s*NHIP_LUOI_AN_TOAN_S\s*:\s*NHIP_MAT_SOCKET_S",
		                 "nhịp phải phụ thuộc socket còn sống hay không")
		self.assertIn("document.hidden", src, "tab ẩn thì đừng hỏi máy chủ")


if __name__ == "__main__":
	unittest.main()
