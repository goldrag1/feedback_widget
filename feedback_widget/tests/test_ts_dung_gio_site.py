"""`ts` của vé phải là GIỜ CỦA SITE, không phải giờ UTC.

Widget gửi `ts` dạng ISO kết thúc bằng Z (UTC). Bản cũ bỏ tzinfo suông — tức GIỮ NGUYÊN giờ
UTC — nên `ts` lệch đúng offset của site so với `creation`. Đo prod 27/08/2026: **212/212**
vé lệch 420 phút, trong khi `Feedback Event.ts` khớp. Mọi báo cáo đọc `ts` (mục "hồi quy" so
`Event.ts` với mốc đóng vé, biểu đồ theo giờ) đọc lệch cả buổi mà không có dấu hiệu nào.

Test khoá ba nhánh: có Z (UTC) · không có múi giờ (coi như giờ site) · không gửi gì.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_system_timezone, now_datetime

from feedback_widget.api.feedback import collect

DAU = "THU TS GIO SITE"


class TestTsDungGioSite(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		for n in frappe.get_all("Feedback Comment", filters={"message": ["like", f"%{DAU}%"]}, pluck="name"):
			frappe.delete_doc("Feedback Comment", n, force=True, ignore_permissions=True)
		frappe.db.commit()

	def _gui(self, **kw):
		r = collect(project="thu", screen_id="#/x", screen_name="thu",
		            message=f"{DAU} — {kw.get('nhan', '')}", source="user", **{k: v for k, v in kw.items() if k != "nhan"})
		return frappe.db.get_value("Feedback Comment", r["name"], ["ts", "creation"], as_dict=True)

	def test_ts_ISO_ket_thuc_Z_phai_doi_sang_gio_site(self):
		bay_gio = now_addtz()
		d = self._gui(ts=bay_gio.isoformat().replace("+00:00", "Z"), nhan="utc")
		lech = abs((d.ts - d.creation).total_seconds())
		self.assertLess(lech, 120,
			f"ts={d.ts} vs creation={d.creation} — lệch {lech/3600:.1f} giờ; múi giờ site "
			f"{get_system_timezone()} đang bị bỏ qua")

	def test_ts_KHONG_co_mui_gio_thi_hieu_la_gio_site(self):
		"""Client cũ (hoặc script) gửi ISO trần — không được cộng/trừ gì thêm."""
		moc = now_datetime().replace(microsecond=0)
		d = self._gui(ts=moc.isoformat(), nhan="tran")
		self.assertLess(abs((d.ts - moc).total_seconds()), 5)

	def test_khong_gui_ts_thi_dong_dau_bay_gio(self):
		d = self._gui(nhan="rong")
		self.assertLess(abs((d.ts - now_datetime()).total_seconds()), 120)


def now_addtz():
	"""Giờ UTC tz-aware — đúng thứ trình duyệt gửi lên."""
	import datetime

	return datetime.datetime.now(datetime.timezone.utc)
