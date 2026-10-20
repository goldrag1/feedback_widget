"""Kịch bản màn — luật khớp bước và chấm tiến độ. MỘT định nghĩa duy nhất.

Spec: docs/specs/2026-10-20-kich-ban-man-design.md. Bảng vàng, hồ sơ, báo cáo và lời nhắc
đều gọi vào đây; viết SQL đếm riêng ở chỗ khác là hai luật cho một việc, và chúng sẽ trôi lệch.

Nguồn sự thật theo loại bước:
  * Mở màn / Bấm nút / Gọi máy chủ → `Feedback Event` (trình duyệt gửi lên, giả được bằng
    devtools — thưởng ở đây chỉ là danh dự nên chấp nhận);
  * Tạo chứng từ → chính bảng chứng từ (không giả được) — chỉ dùng khi doctype đó CHỈ màn
    này sinh ra, vì Stock Entry tạo chỗ khác cũng sẽ khớp;
  * Góp ý trên màn → `Feedback Comment` do người gõ, TRỪ góp ý sinh từ thẻ hỏi cảm nhận
    (một cú chạm không được ăn cả điểm bước lẫn điểm cảm nhận).
"""

import re

import frappe
from frappe.utils import cint, get_datetime


def mau_like(mau: str) -> str:
	"""Mẫu màn có `*` → mẫu LIKE. `%` và `_` có sẵn trong mẫu là chữ thường, không phải ký tự
	đại diện: `chot_ton` không được khớp `chotXton`."""
	s = (mau or "").replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
	return s.replace("*", "%")


def _dem_su_kien(where: str, args: list) -> tuple:
	r = frappe.db.sql(f"""SELECT COUNT(*), COUNT(DISTINCT DATE(ts)) FROM `tabFeedback Event`
	                      WHERE {where}""", args)
	return (cint(r[0][0]), cint(r[0][1]))


def dem_buoc(buoc, man: str, user: str, tu, den=None) -> tuple:
	"""(số lần khớp, số ngày khác nhau) của MỘT bước, cho `user`, trong [tu, den)."""
	tu = get_datetime(tu)
	den = get_datetime(den) if den else None
	loai = buoc.get("loai")

	if loai == "Tạo chứng từ":
		dt = buoc.get("doctype_ct")
		if not dt or not frappe.db.exists("DocType", dt):
			return (0, 0)
		where = ["owner = %s", "creation >= %s", "docstatus >= %s", "docstatus != 2"]
		args = [user, tu, cint(buoc.get("docstatus_toi_thieu"))]
		if den:
			where.append("creation < %s"); args.append(den)
		r = frappe.db.sql(f"""SELECT COUNT(*), COUNT(DISTINCT DATE(creation)) FROM `tab{dt}`
		                      WHERE {' AND '.join(where)}""", args)
		return (cint(r[0][0]), cint(r[0][1]))

	if loai == "Góp ý trên màn":
		where = ["source = 'user'", "submitter_user = %s", "ts >= %s", "IFNULL(tu_cam_nhan, 0) = 0",
		         "screen_id LIKE %s"]
		args = [user, tu, mau_like(man)]
		if den:
			where.append("ts < %s"); args.append(den)
		r = frappe.db.sql(f"""SELECT COUNT(*), COUNT(DISTINCT DATE(ts)) FROM `tabFeedback Comment`
		                      WHERE {' AND '.join(where)}""", args)
		return (cint(r[0][0]), cint(r[0][1]))

	where = ["user = %s", "ts >= %s"]
	args = [user, tu]
	if den:
		where.append("ts < %s"); args.append(den)
	if loai == "Mở màn":
		where.append("screen_id LIKE %s"); args.append(mau_like(man))
	elif loai == "Bấm nút":
		where += ["screen_id LIKE %s", "action_id LIKE %s", "outcome = 'ok'"]
		args += [mau_like(man), mau_like(buoc.get("nut") or "")]
	elif loai == "Gọi máy chủ":
		if not buoc.get("endpoint"):
			return (0, 0)
		where.append("endpoint = %s"); args.append(buoc.get("endpoint"))
		chan = (buoc.get("chap_nhan_chan") or "").strip()
		if chan:
			where.append("(outcome = 'ok' OR (outcome = 'chan' AND message LIKE %s))")
			args.append("%" + chan.replace("%", "\\%").replace("_", "\\_") + "%")
		else:
			where.append("outcome = 'ok'")
	else:
		return (0, 0)
	return _dem_su_kien(" AND ".join(where), args)


def buoc_dat(buoc, man: str, user: str, tu, den=None) -> bool:
	so_lan, so_ngay = dem_buoc(buoc, man, user, tu, den)
	return so_lan >= max(cint(buoc.get("so_lan")), 1) and so_ngay >= max(cint(buoc.get("so_ngay")), 1)


def khop_man(mau: str, screen_id: str) -> bool:
	"""Cùng nghĩa với `screen_id LIKE mau_like(mau)`, làm ở Python (danh sách kịch bản nhỏ)."""
	if not mau or not screen_id:
		return False
	return re.fullmatch(".*".join(re.escape(p) for p in mau.split("*")), screen_id, flags=re.S) is not None


def kich_ban_cua_man(screen_id: str):
	"""Kịch bản đang bật khớp `screen_id` (đúng chuỗi bundle gửi — có thể là `#/...`).
	Hai mẫu cùng khớp thì mẫu DÀI hơn (cụ thể hơn) thắng; validate đã cấm chồng lấn."""
	ds = frappe.get_all("Feedback Playbook", filters={"dang_bat": 1}, fields=["name", "man"])
	ung = [d for d in ds if khop_man(d.man, screen_id)]
	ung.sort(key=lambda d: -len(d.man))
	return ung[0].name if ung else None
