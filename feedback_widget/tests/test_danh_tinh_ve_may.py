"""Vé máy sinh từ Error Log phải mang tên NGƯỜI VẤP LỖI, không phải Administrator.

Ca thật 03/09/2026: FB-2026-01571/01572 (site ducan) và FB-2026-00030 (site tamdinh) đều ghi
`submitter_user = Administrator` trong khi `Error Log.owner` là người thật
(`bien.quandoc@ducan.local`, `vungockhanh1607@gmail.com`) — 3 trong 6 vé của một lượt soi gọi
nhầm tên người. Đo lại cả 5 site prod: **36 vé** và **45 dòng sổ** ghi sai danh tính.

Hai gốc rễ, cùng một lớp lỗi "lấy danh tính của phiên đang chạy thay vì của bản ghi":
  1. `collect` đọc `frappe.session.user`, mà việc nền chạy dưới Administrator.
  2. Câu SELECT của cầu KHÔNG lấy cột `owner`, nên `r.owner` là None (`frappe._dict` trả None
     cho khoá thiếu) và sổ thô ghi Administrator cho mọi dòng — không một dòng lỗi nào.

Test khoá HÀNH VI ở cả hai đầu (vé + sổ thô) và khoá luôn ca ngược: log do Administrator chạy
thật thì vẫn phải là Administrator.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from feedback_widget import tac_vu

DAU = "THU DANH TINH VE MAY"


def _nguoi_that() -> tuple:
	"""MỘT người dùng thật đang bật trên site này, KHÔNG phải System Manager.

	Không tự dựng `User` mới: `User.insert` kéo theo `Contact` → `update_global_search`, và bộ
	test của Frappe cho nổ `assert not frappe.flags.in_test` ở đó — đỏ vì hạ tầng chứ không vì
	mã. Fixture cũng không được GÕ TAY một cái tên: đọc từ chính bảng User để test chạy được
	trên mọi site (dev, gương prod).
	"""
	dong = frappe.db.sql("""
		SELECT u.name, u.full_name FROM `tabUser` u
		 WHERE u.enabled = 1 AND u.name NOT IN ('Administrator', 'Guest')
		   AND u.name NOT IN (SELECT parent FROM `tabHas Role`
		                       WHERE parenttype='User' AND role IN ('System Manager','Administrator'))
		 ORDER BY u.creation LIMIT 1""")
	if not dong:
		raise AssertionError("site không có người dùng thường nào để đo — không thể khoá hành vi này")
	return dong[0][0], dong[0][1] or dong[0][0]


class TestDanhTinhVeMay(FrappeTestCase):
	def setUp(self):
		self.phien_cu = frappe.session.user
		self.moc_cu = frappe.db.get_global(tac_vu.MOC)
		frappe.set_user("Administrator")
		self.nguoi, self.ten = _nguoi_that()
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")
		for dt, f in (("Feedback Comment", {"message": ["like", f"%{DAU}%"]}),
		              ("Feedback Event", {"message": ["like", f"%{DAU}%"]}),
		              ("Error Log", {"error": ["like", f"%{DAU}%"]})):
			for n in frappe.get_all(dt, filters=f, pluck="name"):
				frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
		# `set_global(MOC, None)` ghi chuỗi "None" chứ không xoá — câu `creation > 'None'` sau đó
		# khớp 0 dòng và cầu im lặng ngừng đọc, làm module test khác đỏ oan.
		if self.moc_cu is None:
			frappe.db.sql("DELETE FROM `tabDefaultValue` WHERE defkey=%s AND parent='__default'",
			              (tac_vu.MOC,))
			frappe.cache.delete_key("defaults")
		else:
			frappe.db.set_global(tac_vu.MOC, self.moc_cu)
		frappe.db.commit()
		frappe.set_user(self.phien_cu)

	def _dung_log(self, chu: str, hau_to: str) -> str:
		"""Một dòng Error Log THUỘC VỀ `chu` — đúng hình dạng dòng do người dùng làm sinh ra."""
		e = frappe.get_doc({"doctype": "Error Log", "method": f"thu.viec_nen.{hau_to}",
		                    "error": f"Traceback\nValidationError: {DAU} {hau_to}"}
		                   ).insert(ignore_permissions=True)
		frappe.db.set_value("Error Log", e.name, "owner", chu, update_modified=False)
		frappe.db.commit()
		return e.name

	def _chay_cau(self, ten_log: str):
		moc = frappe.db.get_value("Error Log", ten_log, "creation")
		frappe.db.set_global(tac_vu.MOC, str(frappe.utils.add_to_date(moc, minutes=-1)))
		return tac_vu.bac_cau_error_log()

	def _ve(self, hau_to: str):
		ds = frappe.get_all("Feedback Comment", filters={"message": ["like", f"%{DAU} {hau_to}%"]},
		                    fields=["name", "submitter_user", "user_full_name", "affected_users",
		                            "user_roles", "signature"])
		self.assertEqual(len(ds), 1, f"cầu phải dựng đúng 1 vé cho '{hau_to}', đang có {len(ds)}")
		return ds[0]

	def _su_kien(self, hau_to: str):
		ds = frappe.get_all("Feedback Event", filters={"message": ["like", f"%{DAU} {hau_to}%"]},
		                    fields=["name", "user", "user_roles"])
		self.assertEqual(len(ds), 1, f"sổ thô phải có đúng 1 dòng cho '{hau_to}', đang có {len(ds)}")
		return ds[0]

	def test_ve_mang_ten_NGUOI_VAP_LOI_chu_khong_phai_Administrator(self):
		ten_log = self._dung_log(self.nguoi, "nguoithat")
		kq = self._chay_cau(ten_log)
		self.assertGreaterEqual(kq.get("ve", 0), 1, f"cầu không dựng vé nào: {kq}")

		ve = self._ve("nguoithat")
		self.assertEqual(ve.submitter_user, self.nguoi,
		                 f"vé ghi người gửi là {ve.submitter_user!r} trong khi chủ dòng log là {self.nguoi!r}")
		self.assertEqual(ve.user_full_name, self.ten)
		self.assertNotIn("Administrator", ve.affected_users or "",
		                 f"affected_users = {ve.affected_users!r} — đếm người bị chặn sẽ gọi nhầm tên")
		self.assertIn(self.ten, ve.affected_users or "")

	def test_so_tho_cung_mang_ten_do__cau_SELECT_phai_lay_cot_owner(self):
		ten_log = self._dung_log(self.nguoi, "sotho")
		self._chay_cau(ten_log)
		sk = self._su_kien("sotho")
		self.assertEqual(sk.user, self.nguoi,
		                 f"sổ thô ghi {sk.user!r}: mọi bảng xếp hạng 'ai đang bị chặn' đọc cột này")

	def test_log_do_Administrator_chay_that_thi_VAN_la_Administrator(self):
		"""Ca ngược — cổng phải chặn ĐÚNG một chiều, không đổi tên bừa cho việc nền thật."""
		ten_log = self._dung_log("Administrator", "viecnenthat")
		self._chay_cau(ten_log)
		ve = self._ve("viecnenthat")
		self.assertIn(ve.submitter_user, (None, "", "Administrator"))
		sk = self._su_kien("viecnenthat")
		self.assertEqual(sk.user, "Administrator")

	def test_chu_ky_KHONG_doi_theo_danh_tinh(self):
		"""Chữ ký chỉ tính từ (thông điệp, endpoint). Nếu danh tính lọt vào băm thì vé cũ và
		vé mới tách nhóm, và mục 'bao nhiêu lần' của mọi vé máy đang mở sẽ vỡ."""
		from feedback_widget.chu_ky import chu_ky

		self.assertEqual(chu_ky(f"ValidationError: {DAU} x", "thu.viec_nen.x"),
		                 chu_ky(f"ValidationError: {DAU} x", "thu.viec_nen.x"))
		ten_log = self._dung_log(self.nguoi, "chuky")
		self._chay_cau(ten_log)
		ve = self._ve("chuky")
		self.assertEqual(ve.signature,
		                 chu_ky(f"ValidationError: {DAU} chuky", "thu.viec_nen.chuky"))

	def test_may_khach_KHONG_the_gia_mao_danh_tinh_qua_HTTP(self):
		"""`nguoi_thay_mat` là ô của MÁY CHỦ. Người dùng thường gửi lên qua HTTP thì bị bỏ qua —
		nếu không, ai cũng gõ được một tấm vé mang tên người khác."""
		from feedback_widget.api import feedback as api_fb

		class _GiaLuotHTTP:
			pass

		self.assertEqual(api_fb._nguoi_thay_mat({"nguoi_thay_mat": self.nguoi}), self.nguoi,
		                 "đường trong máy chủ (không có request) phải khai hộ được")
		cu = getattr(frappe.local, "request", None)
		try:
			frappe.local.request = _GiaLuotHTTP()
			frappe.set_user(self.nguoi)          # người dùng thường, không phải System Manager
			self.assertIsNone(api_fb._nguoi_thay_mat({"nguoi_thay_mat": "Administrator"}),
			                  "lượt HTTP của người dùng thường KHÔNG được khai hộ ai cả")
		finally:
			frappe.set_user("Administrator")
			if cu is None:
				try:
					del frappe.local.request
				except Exception:
					frappe.local.request = None
			else:
				frappe.local.request = cu
