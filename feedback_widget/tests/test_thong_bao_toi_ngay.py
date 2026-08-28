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
 4. **Cắm tai nghe phải THỬ LẠI tới khi socket có thật, và chỉ cắm MỘT lần.** Bản 28/08 đo
    trên prod: `frappe.realtime.on` đã là hàm ở giây 1,95 nên widget gọi `on()` ở giây 2,60
    và tưởng xong, trong khi socket mãi giây 3,13 mới dựng — `RealTimeClient.on()` là
    `if (this.socket) {…}` nên nó KHÔNG đăng ký gì, không ném lỗi, không trả gì. Kết quả đo
    được: `socket.listeners("fbw_thong_bao_moi").length` = 0 trên máy đang mở, thẻ chỉ hiện
    sau F5 — đúng cái bệnh mục 1-3 tưởng đã chữa. Ca dưới CHẠY THẬT hàm đó bằng node với
    một `RealTimeClient` giả mang đúng ngữ nghĩa ấy, thay vì tin vào mắt đọc mã.

Chạy:
  cd <gốc bench> && env/bin/python -m unittest feedback_widget.tests.test_thong_bao_toi_ngay
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
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

	def _khoi_ham(self, ten: str) -> str:
		"""Cắt nguyên thân một hàm khỏi bundle bằng cách ĐẾM NGOẶC (không regex `.*?`).

		Cần bản gốc còn xuống dòng để chạy thật bằng node, nên đọc thẳng tệp chứ không
		dùng `_bundle()` (hàm kia ép mọi khoảng trắng về một dấu cách).
		"""
		with open(BUNDLE, encoding="utf-8") as fh:
			src = fh.read()
		i = src.index(f"function {ten}(")
		j = src.index("{", i)
		sau = 0
		for k in range(j, len(src)):
			if src[k] == "{":
				sau += 1
			elif src[k] == "}":
				sau -= 1
				if sau == 0:
					return src[i:k + 1]
		raise AssertionError(f"không cắt được thân hàm {ten}() — ngoặc không cân")

	def test_js_nghe_dung_ten_su_kien_cua_may_chu(self):
		from feedback_widget.api.thong_bao import SU_KIEN

		src = self._bundle()
		self.assertRegex(src, r'SU_KIEN_THONG_BAO\s*=\s*"' + re.escape(SU_KIEN) + '"',
		                 f"bundle phải khai đúng tên sự kiện '{SU_KIEN}' của máy chủ — lệch "
		                 "một bên là máy chủ bắn vào chỗ không ai nghe, không lỗi nào để lần ra")
		# Người nghe phải là REALTIME, và phải được NỐI DÂY: một hàm nghe khai xong mà
		# không ai gọi thì test vẫn xanh còn tính năng thì chết (lớp lỗi "0 chỗ gọi").
		than = self._khoi_ham("ngheRealtime")
		self.assertIn("frappe.realtime", than, "phải nghe qua `frappe.realtime`")
		self.assertRegex(than, r"\.on\(\s*SU_KIEN_THONG_BAO",
		                 "phải đăng ký `.on(SU_KIEN_THONG_BAO, …)`")
		goi = [m for m in re.finditer(r"(?<!function )\bngheRealtime\(\)", src)]
		self.assertGreaterEqual(len(goi), 1, "hàm nghe khai xong mà KHÔNG ai gọi")

	def test_js_co_vong_thu_lai_co_tran_khi_socket_chua_dung(self):
		"""Cắm hụt một lần rồi thôi chính là lỗi đo được trên prod 28/08 (0 tai nghe)."""
		src = self._bundle()
		self.assertRegex(src, r"if \(!ngheRealtime\(\)\) \{",
		                 "phải có nhánh 'cắm chưa được thì thử lại' — `on()` của Frappe im "
		                 "lặng khi socket chưa dựng, gọi một lần rồi thôi là không bao giờ nghe")
		self.assertRegex(src, r"setInterval\(function \(\) \{ lanThuNghe \+= 1;",
		                 "vòng thử lại phải chạy theo nhịp `setInterval`")
		self.assertRegex(src, r"lanThuNghe >= SO_LAN_THU_NGHE\) window\.clearInterval",
		                 "vòng thử lại phải có TRẦN và tự dọn — site tắt async thì socket "
		                 "không bao giờ có, để nó chạy mãi là rác trên mọi màn")
		self.assertRegex(src, r"SO_LAN_THU_NGHE\s*=\s*(\d+)", "thiếu khai số lần thử")
		so_lan = int(re.search(r"SO_LAN_THU_NGHE\s*=\s*(\d+)", src).group(1))
		nhip = int(re.search(r"NHIP_THU_NGHE_MS\s*=\s*(\d+)", src).group(1))
		self.assertGreaterEqual(so_lan * nhip, 30000,
		                        "cửa sổ thử lại phải ≥30 giây: đo trên prod socket dựng ở "
		                        "giây 3,1 với máy nhanh, máy xưởng chậm hơn nhiều")

	@unittest.skipUnless(shutil.which("node"), "không có node để chạy thật đoạn JS")
	def test_js_cam_dung_mot_lan_khi_socket_toi_va_hoi_lai_khi_noi_lai(self):
		"""CHẠY THẬT `ngheRealtime()` bằng node với `RealTimeClient` giả đúng ngữ nghĩa.

		Đọc mã không phân biệt được "đã đăng ký" với "gọi `on()` vào chỗ trống": chính chỗ
		đó làm bản trước chết câm. Bốn tính chất đo bằng số tai nghe THẬT trên socket giả.
		"""
		from feedback_widget.api.thong_bao import SU_KIEN

		harness = """
		var demSoLan = 0;
		function dem() { demSoLan += 1; }
		var SU_KIEN_THONG_BAO = %(su_kien)s;
		function socketGia() {
			var ev = {};
			return { connected: true,
			         on: function (n, cb) { (ev[n] = ev[n] || []).push(cb); },
			         listeners: function (n) { return ev[n] || []; } };
		}
		// Bản sao ngữ nghĩa `RealTimeClient.on` của Frappe v16 (socketio_client.js):
		// KHÔNG có socket ⇒ im lặng không đăng ký gì, không lỗi, không trả gì.
		var rt = { socket: null,
		           on: function (n, cb) { if (this.socket) { this.socket.on(n, cb); } } };
		var hen = 0;
		global.window = { frappe: { realtime: rt },
		                  setTimeout: function (f) { hen += 1; f(); } };
		%(ma)s
		var kq = { chua_co_socket: ngheRealtime(), nghe_khi_chua_co_socket: 0 };
		rt.socket = socketGia();
		kq.khi_socket_toi = ngheRealtime();
		kq.nghe_sau_khi_toi = rt.socket.listeners(SU_KIEN_THONG_BAO).length;
		for (var i = 0; i < 10; i++) { ngheRealtime(); }
		kq.nghe_sau_10_lan_goi_lai = rt.socket.listeners(SU_KIEN_THONG_BAO).length;
		kq.connect_sau_10_lan_goi_lai = rt.socket.listeners("connect").length;
		demSoLan = 0;
		rt.socket.listeners("connect").forEach(function (f) { f(); });
		kq.hoi_lai_khi_noi_lai = demSoLan;
		var cu = rt.socket;
		rt.socket = socketGia();
		kq.doi_socket = ngheRealtime();
		kq.nghe_tren_socket_moi = rt.socket.listeners(SU_KIEN_THONG_BAO).length;
		kq.nghe_tren_socket_cu = cu.listeners(SU_KIEN_THONG_BAO).length;
		console.log(JSON.stringify(kq));
		""" % {"su_kien": json.dumps(SU_KIEN),
		       "ma": "var socketDangNghe = null;\n" + self._khoi_ham("ngheRealtime")}

		with tempfile.TemporaryDirectory() as d:
			f = os.path.join(d, "thu_nghe.cjs")
			with open(f, "w", encoding="utf-8") as fh:
				fh.write(harness)
			r = subprocess.run(["node", f], capture_output=True, text=True, timeout=60)
		self.assertEqual(r.returncode, 0, f"node chạy hỏng: {r.stderr[-800:]}")
		kq = json.loads(r.stdout.strip().splitlines()[-1])

		self.assertFalse(kq["chua_co_socket"],
		                 "socket chưa dựng mà báo 'đã cắm' = vòng thử lại dừng sớm, và đó "
		                 "chính là lỗi prod: 0 tai nghe, không lỗi nào")
		self.assertTrue(kq["khi_socket_toi"], "socket có rồi mà vẫn không cắm được")
		self.assertEqual(kq["nghe_sau_khi_toi"], 1, "phải cắm đúng một tai nghe")
		self.assertEqual(kq["nghe_sau_10_lan_goi_lai"], 1,
		                 "gọi lại 10 lần vẫn phải là 1 tai nghe — cắm trùng thì mỗi phao đẻ "
		                 "N lượt hỏi máy chủ và N chồng thẻ")
		self.assertEqual(kq["connect_sau_10_lan_goi_lai"], 1,
		                 "tai nghe 'connect' cũng phải chống trùng")
		self.assertGreaterEqual(kq["hoi_lai_khi_noi_lai"], 1,
		                        "socket nối lại phải hỏi lại một nhịp: phao bắn trong lúc "
		                        "rớt mất hẳn, không ai gửi lại")
		self.assertEqual(kq["nghe_tren_socket_moi"], 1,
		                 "socket bị thay thì phải cắm sang cái mới")
		self.assertEqual(kq["nghe_tren_socket_cu"], 1, "không được cắm thêm vào socket cũ")

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
