"""Sổ điểm, cấp bậc, huân chương — thưởng ẢO, danh dự (chủ đầu tư chốt 20/10/2026).

Sổ chỉ THÊM, không sửa: mọi điểm đi qua `ghi_diem` (hoặc `dat_diem` cho thứ bật/tắt được),
mỗi dòng có `khoa` unique nên chấm lại bao nhiêu lần cũng không cộng đôi — cron 15 phút,
lượt mở màn và hook góp ý có thể cùng chấm một việc trong cùng một phút.
"""

import frappe
from frappe.utils import add_days, cint, get_datetime, now_datetime

from feedback_widget.cai_dat import cai_dat

DANH_MUC_HUAN_CHUONG = {
	"mo-duong": "🚀 Người mở đường",
	"mat-tinh": "🦅 Mắt tinh",
	"nguoi-goi-y": "💡 Người gợi ý",
	"chuyen-can": "🔥 Chuyên cần",
	"theo-man": "🎯 Thạo màn",
	"chuoi-10": "📅 Chuỗi 10",
	"chuoi-30": "📅 Chuỗi 30",
}

CAP = ("Tập sự", "Thành thạo", "Key user", "Đại sứ chuyển đổi số")


def ghi_diem(user, diem: int, ly_do: str, khoa: str, nguon_doctype=None, nguon_name=None) -> bool:
	"""Ghi một dòng điểm. Đã có dòng cùng `khoa` ⇒ False, không ném."""
	if not user or not khoa or frappe.db.exists("Feedback Point", {"khoa": khoa}):
		return False
	try:
		frappe.get_doc({
			"doctype": "Feedback Point", "user": user, "diem": cint(diem), "ly_do": ly_do,
			"khoa": khoa[:140], "nguon_doctype": nguon_doctype, "nguon_name": nguon_name,
		}).insert(ignore_permissions=True)
	except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
		return False
	return True


def _con_lai(khoa: str) -> int:
	"""Điểm RÒNG còn lại của một khoản bật/tắt được (gốc + cấp lại + thu hồi)."""
	r = frappe.db.sql("""SELECT IFNULL(SUM(diem), 0) FROM `tabFeedback Point`
	                     WHERE khoa = %s OR khoa LIKE %s OR khoa LIKE %s""",
	                  (khoa, khoa + "|lai%", "Thu hồi|" + khoa + "|%"))
	return cint(r[0][0])


def dat_diem(user, diem: int, ly_do: str, khoa: str, co: bool, nguon_doctype=None, nguon_name=None) -> int:
	"""Đưa khoản điểm `khoa` về đúng trạng thái `co` (bật = có điểm, tắt = không). Trả số điểm
	đã ghi thêm (âm khi thu hồi). Dùng cho thứ người duyệt bật/tắt được (góp ý có ích…)."""
	rong = _con_lai(khoa)
	if co and rong <= 0:
		dem = frappe.db.count("Feedback Point", {"khoa": ["like", khoa + "|lai%"]})
		k = khoa if not frappe.db.exists("Feedback Point", {"khoa": khoa}) else f"{khoa}|lai{dem + 1}"
		return cint(diem) if ghi_diem(user, diem, ly_do, k, nguon_doctype, nguon_name) else 0
	if not co and rong > 0:
		dem = frappe.db.count("Feedback Point", {"khoa": ["like", "Thu hồi|" + khoa + "|%"]})
		ok = ghi_diem(user, -rong, "Thu hồi", f"Thu hồi|{khoa}|{dem + 1}", nguon_doctype, nguon_name)
		return -rong if ok else 0
	return 0


def thu_hoi(khoa_goc: str) -> bool:
	"""Thu hồi khoản điểm `khoa_goc` (nếu còn). Gọi lại lần hai không trừ thêm."""
	u = frappe.db.get_value("Feedback Point", {"khoa": khoa_goc}, "user")
	return bool(u and dat_diem(u, 0, "Thu hồi", khoa_goc, False))


def tong_diem(user, chi_da_bao: bool = False, tu=None, den=None) -> int:
	where, args = ["user = %s"], [user]
	if chi_da_bao:
		where.append("da_bao = 1")
	if tu:
		where.append("creation >= %s"); args.append(get_datetime(tu))
	if den:
		where.append("creation < %s"); args.append(get_datetime(den))
	r = frappe.db.sql(f"SELECT IFNULL(SUM(diem), 0) FROM `tabFeedback Point` WHERE {' AND '.join(where)}", args)
	return cint(r[0][0])


def nguong() -> list:
	ct = cai_dat()
	return [cint(ct["nguong_thanh_thao"]), cint(ct["nguong_key_user"]), cint(ct["nguong_dai_su"])]


def cap(tong: int) -> str:
	i = sum(1 for n in nguong() if cint(tong) >= n)
	return CAP[i]


def nguong_ke(tong: int):
	"""Ngưỡng của cấp kế tiếp, hoặc None nếu đã ở cấp cao nhất."""
	for n in nguong():
		if cint(tong) < n:
			return n
	return None


def trao(user, huan_chuong: str, khoa: str, nguon_doctype=None, nguon_name=None) -> bool:
	if huan_chuong not in DANH_MUC_HUAN_CHUONG or not user:
		return False
	if frappe.db.exists("Feedback Badge Award", {"khoa": khoa}):
		return False
	try:
		frappe.get_doc({
			"doctype": "Feedback Badge Award", "user": user, "huan_chuong": huan_chuong,
			"luc": now_datetime(), "khoa": khoa[:140],
			"nguon_doctype": nguon_doctype, "nguon_name": nguon_name,
		}).insert(ignore_permissions=True)
	except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
		return False
	return True


def huan_chuong_cua(user) -> dict:
	"""{mã: số lần} của một người."""
	return {r.huan_chuong: cint(r.n) for r in frappe.db.sql(
		"""SELECT huan_chuong, COUNT(*) n FROM `tabFeedback Badge Award` WHERE user = %s
		   GROUP BY huan_chuong""", user, as_dict=True)}


def chua_bao(user) -> dict:
	"""Những gì người dùng CHƯA được báo: dòng điểm, huân chương, và lên cấp (suy từ hai tổng,
	không cần lưu cấp riêng: cấp trước = tổng các dòng đã báo, cấp sau = tổng mọi dòng)."""
	diem = frappe.get_all("Feedback Point", filters={"user": user, "da_bao": 0},
	                      fields=["name", "diem", "ly_do", "nguon_doctype", "nguon_name"], order_by="creation asc")
	hc = frappe.get_all("Feedback Badge Award", filters={"user": user, "da_bao": 0},
	                    fields=["name", "huan_chuong", "nguon_name"], order_by="creation asc")
	truoc, sau = tong_diem(user, chi_da_bao=True), tong_diem(user)
	return {
		"diem": diem,
		"huan_chuong": [dict(h, ten=DANH_MUC_HUAN_CHUONG.get(h.huan_chuong, h.huan_chuong)) for h in hc],
		"tong": sau, "cap_truoc": cap(truoc), "cap_sau": cap(sau),
	}


def danh_dau_da_bao(user) -> None:
	frappe.db.sql("UPDATE `tabFeedback Point` SET da_bao = 1 WHERE user = %s AND da_bao = 0", user)
	frappe.db.sql("UPDATE `tabFeedback Badge Award` SET da_bao = 1 WHERE user = %s AND da_bao = 0", user)


def _tuan(d) -> tuple:
	y, w, _wd = get_datetime(d).isocalendar()
	return (y, w)


def kiem_huan_chuong_ngay(luc=None) -> dict:
	"""Cron hằng ngày: 🔥 Chuyên cần — `tuan_chuyen_can` tuần ISO liên tiếp, tuần nào cũng có
	≥ 1 dòng điểm dương. Trao MỘT lần cho mỗi chuỗi: khoá là tuần BẮT ĐẦU chuỗi (khoá theo
	tuần kết thúc sẽ trao lại mỗi tuần chuỗi còn kéo dài)."""
	ct = cai_dat()
	if not cint(ct.get("kb_bat")) and not frappe.flags.in_test:
		return {"tat": 1}
	can = max(cint(ct.get("tuan_chuyen_can")), 1)
	luc = get_datetime(luc) if luc else now_datetime()
	# cửa sổ rộng: chuỗi dài hơn cửa sổ sẽ ra tuần bắt đầu khác mỗi tuần ⇒ trao lặp
	tu = add_days(luc, -7 * 60)
	trao_moi = 0
	rows = frappe.db.sql("""SELECT user, creation FROM `tabFeedback Point`
	                        WHERE diem > 0 AND creation >= %s AND creation <= %s""", (tu, luc), as_dict=True)
	theo_nguoi = {}
	for r in rows:
		theo_nguoi.setdefault(r.user, set()).add(_tuan(r.creation))
	for user, tuan in theo_nguoi.items():
		# đi lùi từ tuần hiện tại; tuần hiện tại chưa có điểm thì bắt đầu từ tuần trước
		cur = luc
		if _tuan(cur) not in tuan:
			cur = add_days(cur, -7)
		chuoi = []
		while _tuan(cur) in tuan:
			chuoi.append(_tuan(cur))
			cur = add_days(cur, -7)
		if len(chuoi) >= can:
			bd = chuoi[-1]
			if trao(user, "chuyen-can", f"chuyen-can|{bd[0]}-W{bd[1]:02d}|{user}"):
				trao_moi += 1
	return {"trao": trao_moi}


# ---------------------------------------------------------------------------------------
# Góp ý có ích / thành cải tiến
# ---------------------------------------------------------------------------------------

def theo_gop_y(ve) -> None:
	"""Đưa điểm + huân chương của MỘT góp ý về đúng trạng thái `co_ich` / `thanh_cai_tien`.
	Vé máy (`source='auto'`) không bao giờ được điểm. Gọi từ `on_update` của Feedback Comment;
	KHÔNG được làm hỏng lượt lưu vé."""
	try:
		user = ve.get("submitter_user")
		if ve.get("source") != "user" or not user or user in ("Guest", "Administrator"):
			return
		ct = cai_dat()
		dat_diem(user, cint(ct["diem_co_ich"]), "Góp ý có ích", f"Góp ý có ích|{ve.name}|{user}",
		         bool(cint(ve.get("co_ich"))), "Feedback Comment", ve.name)
		cai_tien = bool(cint(ve.get("thanh_cai_tien")))
		dat_diem(user, cint(ct["diem_cai_tien"]), "Góp ý thành cải tiến", f"Góp ý thành cải tiến|{ve.name}|{user}",
		         cai_tien, "Feedback Comment", ve.name)
		if cai_tien and ve.get("tag_type") in ("bug", "idea"):
			ma = "mat-tinh" if ve.get("tag_type") == "bug" else "nguoi-goi-y"
			trao(user, ma, f"{ma}|{ve.name}", "Feedback Comment", ve.name)
	except Exception:
		frappe.log_error(title=f"diem.theo_gop_y {ve.name}"[:140], message=frappe.get_traceback())
