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

import json
import re
from datetime import datetime, time, timedelta

import frappe
from frappe.utils import cint, get_datetime, get_time, now_datetime

from feedback_widget.cai_dat import cai_dat
from feedback_widget.diem import ghi_diem, trao


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


# ---------------------------------------------------------------------------------------
# Chấm tiến độ
# ---------------------------------------------------------------------------------------

def _j(v, mac=None):
	if isinstance(v, dict):
		return v
	try:
		return json.loads(v) if v else (mac if mac is not None else {})
	except Exception:
		return mac if mac is not None else {}


def _ngay_lam(chang=None) -> set:
	s = (chang.get("ngay_lam_viec") if chang else None) or cai_dat().get("ngay_lam_viec") or "1,2,3,4,5,6"
	return {cint(x) for x in str(s).split(",") if str(x).strip().isdigit()}


def ky_hien_tai(chang, luc):
	"""Kỳ của chặng Duy trì chứa `luc`: (đầu kỳ, hạn kỳ). Ngày không làm việc ⇒ None.
	Ngày: [00:00, giờ hạn] — đạt SAU giờ hạn không tính cho hôm đó. Tuần: thứ Hai → thứ Hai."""
	luc = get_datetime(luc)
	if chang.get("chu_ky") == "Tuần":
		dau = datetime.combine((luc - timedelta(days=luc.isoweekday() - 1)).date(), time.min)
		return (dau, dau + timedelta(days=7))
	if luc.isoweekday() not in _ngay_lam(chang):
		return None
	dau = datetime.combine(luc.date(), time.min)
	gh = chang.get("gio_han")
	if gh:
		gh = get_time(gh)
		return (dau, datetime.combine(luc.date(), gh))
	return (dau, dau + timedelta(days=1))


def _ky_truoc(chang, dau_ky):
	"""Đầu kỳ làm việc NGAY TRƯỚC kỳ bắt đầu ở `dau_ky` (bỏ qua ngày nghỉ)."""
	if chang.get("chu_ky") == "Tuần":
		return dau_ky - timedelta(days=7)
	d = dau_ky - timedelta(days=1)
	for _i in range(8):
		if d.isoweekday() in _ngay_lam(chang):
			return d
		d -= timedelta(days=1)
	return d


def chuoi_hien_tai(chang, trang_thai: dict, luc) -> int:
	"""Chuỗi còn SỐNG lúc `luc`: kỳ đạt cuối là kỳ này hoặc kỳ làm việc ngay trước."""
	cuoi = trang_thai.get("ky_cuoi_dat")
	if not cuoi:
		return 0
	cuoi = get_datetime(cuoi)
	ky = ky_hien_tai(chang, luc)
	dau = ky[0] if ky else None
	if dau is None:   # hôm nay nghỉ: kỳ "hiện tại" coi như kỳ làm việc kế sau ngày đạt cuối
		return cint(trang_thai.get("chuoi"))
	if cuoi == dau or cuoi == _ky_truoc(chang, dau):
		return cint(trang_thai.get("chuoi"))
	return 0


def tien_do(kich_ban: str, user: str, tao: bool = True, luc=None):
	ten = frappe.db.get_value("Feedback Playbook Progress", {"kich_ban": kich_ban, "user": user}, "name")
	if ten:
		return frappe.get_doc("Feedback Playbook Progress", ten)
	if not tao:
		return None
	kb = frappe.get_cached_doc("Feedback Playbook", kich_ban)
	dau = sorted(kb.chang, key=lambda c: cint(c.thu_tu))
	try:
		d = frappe.get_doc({
			"doctype": "Feedback Playbook Progress", "kich_ban": kich_ban, "user": user,
			"bat_dau": get_datetime(luc) if luc else now_datetime(), "huong_dan": "Chưa xem",
			"chang_hien_tai": dau[0].ma if dau else None,
			"buoc_xong": "{}", "chang_xong": "{}", "duy_tri": "{}", "cam_nhan": "{}",
		}).insert(ignore_permissions=True)
	except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
		return frappe.get_doc("Feedback Playbook Progress",
		                      frappe.db.get_value("Feedback Playbook Progress", {"kich_ban": kich_ban, "user": user}))
	return d


def _diem_mac(buoc_or_chang, khoa_cai_dat):
	v = cint(buoc_or_chang.get("diem"))
	return v if v else cint(cai_dat().get(khoa_cai_dat))


def cham(kich_ban: str, user: str, luc=None) -> list:
	"""Chấm MỘT người trên MỘT kịch bản. Trả danh sách việc MỚI đạt ở lượt này.

	Khoá dòng tiến độ (`FOR UPDATE`) để cron và lượt mở màn không chấm chồng nhau; điểm thì
	đã an toàn nhờ khoá unique, khoá dòng ở đây giữ cho JSON tiến độ không bị ghi đè nhau."""
	luc = get_datetime(luc) if luc else now_datetime()
	kb = frappe.get_doc("Feedback Playbook", kich_ban)
	if not kb.dang_bat:
		return []
	p = tien_do(kich_ban, user, tao=True, luc=luc)
	frappe.db.sql("SELECT name FROM `tabFeedback Playbook Progress` WHERE name = %s FOR UPDATE", p.name)
	p.reload()
	moc = get_datetime(p.bat_dau)
	buoc_xong, chang_xong, duy_tri = _j(p.buoc_xong), _j(p.chang_xong), _j(p.duy_tri)
	moi = []
	chang = sorted(kb.chang, key=lambda c: cint(c.thu_tu))
	buoc_theo = {}
	for b in kb.buoc:
		buoc_theo.setdefault(b.chang, []).append(b)

	# --- chặng Một lần: theo thứ tự, chặng sau chỉ chấm khi chặng trước xong ---
	hien_tai = None
	for ch in chang:
		if ch.loai != "Một lần":
			continue
		if ch.ma in chang_xong:
			continue
		ds = buoc_theo.get(ch.ma, [])
		for b in ds:
			if b.name in buoc_xong:
				continue
			if buoc_dat(b, kb.man, user, moc, luc + timedelta(seconds=1)):
				buoc_xong[b.name] = str(luc)
				ghi_diem(user, _diem_mac(b, "diem_buoc"), "Bước", f"Bước|{kb.name}|{b.name}|{user}",
				         "Feedback Playbook", kb.name)
				moi.append({"loai": "buoc", "mo_ta": b.mo_ta, "chang": ch.ma})
		if ds and all(b.name in buoc_xong for b in ds):
			chang_xong[ch.ma] = str(luc)
			ghi_diem(user, _diem_mac(ch, "diem_chang"), "Chặng", f"Chặng|{kb.name}|{ch.ma}|{user}",
			         "Feedback Playbook", f"{kb.name}|{ch.ma}")
			moi.append({"loai": "chang", "chang": ch.ma, "ten": ch.ten, "hoi_cam_nhan": cint(ch.hoi_cam_nhan)})
			continue
		hien_tai = ch.ma
		break

	# --- chặng Duy trì: kỳ nào đạt đủ bước trong [đầu kỳ, hạn kỳ] thì cộng và nối chuỗi ---
	for ch in chang:
		if ch.loai != "Duy trì":
			continue
		ds = buoc_theo.get(ch.ma, [])
		if not ds:
			continue
		tt = duy_tri.setdefault(ch.ma, {"ky_cuoi_dat": None, "chuoi": 0, "chuoi_dai_nhat": 0})
		cac_ky = []
		d = luc
		for _i in range(14):           # nhìn lùi tối đa 14 kỳ — đủ cho cron chậm vài ngày
			ky = ky_hien_tai(ch, d)
			if ky and ky[1] > moc and (not tt["ky_cuoi_dat"] or ky[0] > get_datetime(tt["ky_cuoi_dat"])):
				if ky not in cac_ky:
					cac_ky.append(ky)
			d = d - timedelta(days=7 if ch.get("chu_ky") == "Tuần" else 1)
			if d < moc - timedelta(days=1):
				break
		for dau, han in sorted(cac_ky):
			if dau > luc:
				continue
			den = min(han, luc + timedelta(seconds=1))
			if all(buoc_dat(b, kb.man, user, max(dau, moc), den) for b in ds):
				truoc = tt["ky_cuoi_dat"]
				if truoc and get_datetime(truoc) == _ky_truoc(ch, dau):
					tt["chuoi"] = cint(tt["chuoi"]) + 1
				else:
					tt["chuoi"] = 1
				tt["ky_cuoi_dat"] = str(dau)
				tt["chuoi_dai_nhat"] = max(cint(tt["chuoi_dai_nhat"]), tt["chuoi"])
				ghi_diem(user, _diem_mac(ch, "diem_ky_duy_tri"), "Kỳ duy trì",
				         f"Kỳ duy trì|{kb.name}|{ch.ma}|{dau.date()}|{user}", "Feedback Playbook", kb.name)
				moi.append({"loai": "ky", "chang": ch.ma, "chuoi": tt["chuoi"]})
				for moc_chuoi in (10, 30):
					if tt["chuoi"] >= moc_chuoi:
						trao(user, f"chuoi-{moc_chuoi}", f"chuoi-{moc_chuoi}|{kb.name}|{ch.ma}|{user}",
						     "Feedback Playbook", kb.name)

	# --- 🎯 Thạo màn: mọi chặng Một lần xong + mọi chặng Duy trì từng có chuỗi ≥ 3 ---
	mot_lan = [c.ma for c in chang if c.loai == "Một lần"]
	duy = [c.ma for c in chang if c.loai == "Duy trì"]
	if chang and all(m in chang_xong for m in mot_lan) and all(
			cint(duy_tri.get(m, {}).get("chuoi_dai_nhat")) >= 3 for m in duy):
		if trao(user, "theo-man", f"theo-man|{kb.name}|{user}", "Feedback Playbook", kb.name):
			moi.append({"loai": "huan_chuong", "ma": "theo-man"})

	if hien_tai is None:
		hien_tai = next((c.ma for c in chang if c.loai == "Duy trì"), chang[-1].ma if chang else None)
	frappe.db.set_value("Feedback Playbook Progress", p.name, {
		"buoc_xong": json.dumps(buoc_xong, ensure_ascii=False),
		"chang_xong": json.dumps(chang_xong, ensure_ascii=False),
		"duy_tri": json.dumps(duy_tri, ensure_ascii=False, default=str),
		"chang_hien_tai": hien_tai,
	}, update_modified=False)
	p.buoc_xong, p.chang_xong, p.duy_tri = buoc_xong, chang_xong, duy_tri
	moi += _cap_nhat_nhiem_vu(kb, user, luc, chang_xong, duy_tri)
	return moi


def dat_chang(kb, ma: str, chang_xong: dict, duy_tri: dict, luc, chuoi_can: int = 3) -> bool:
	ch = next((c for c in kb.chang if c.ma == ma), None)
	if not ch:
		return False
	if ch.loai == "Một lần":
		return ma in chang_xong
	return chuoi_hien_tai(ch, duy_tri.get(ma) or {}, luc) >= max(cint(chuoi_can), 1)


def _cap_nhat_nhiem_vu(kb, user, luc, chang_xong, duy_tri) -> list:
	moi = []
	rows = frappe.db.sql("""SELECT a.name row, m.name nv, m.chang_muc_tieu, m.chuoi_muc_tieu, m.bat_dau, a.trang_thai
	                        FROM `tabFeedback Mission Assignee` a
	                        JOIN `tabFeedback Mission` m ON m.name = a.parent
	                        WHERE m.kich_ban = %s AND a.user = %s AND a.trang_thai != 'Hoàn thành'""",
	                     (kb.name, user), as_dict=True)
	ct = cai_dat()
	for r in rows:
		if not dat_chang(kb, r.chang_muc_tieu, chang_xong, duy_tri, luc, r.chuoi_muc_tieu):
			continue
		frappe.db.set_value("Feedback Mission Assignee", r.row,
		                    {"trang_thai": "Hoàn thành", "hoan_thanh_luc": luc}, update_modified=False)
		ghi_diem(user, cint(ct.get("diem_nhiem_vu")), "Hoàn thành nhiệm vụ",
		         f"Hoàn thành nhiệm vụ|{r.nv}|{user}", "Feedback Mission", r.nv)
		moi.append({"loai": "nhiem_vu", "nhiem_vu": r.nv})
		if (r.trang_thai == "Đang làm" and r.bat_dau
				and (luc - get_datetime(r.bat_dau)) <= timedelta(hours=cint(ct.get("gio_mo_duong")))):
			ghi_diem(user, cint(ct.get("diem_mo_duong")), "Người mở đường",
			         f"Người mở đường|{r.nv}|{user}", "Feedback Mission", r.nv)
			if trao(user, "mo-duong", f"mo-duong|{r.nv}|{user}", "Feedback Mission", r.nv):
				moi.append({"loai": "huan_chuong", "ma": "mo-duong"})
	return moi


def cham_theo_man(user: str, screen_ids=None) -> int:
	"""Chạy nền sau mỗi lô sự kiện: chấm các kịch bản khớp những màn vừa có sự kiện."""
	if not cint(cai_dat().get("kb_bat")) or not user or user == "Guest":
		return 0
	da = set()
	for sid in set(screen_ids or []):
		k = kich_ban_cua_man(sid)
		if k and k not in da:
			da.add(k)
			try:
				cham(k, user)
			except Exception:
				frappe.log_error(title=f"kich_ban.cham {k} {user}"[:140], message=frappe.get_traceback())
	return len(da)


def cham_tat_ca(luc=None) -> dict:
	"""Cron 15 phút: chấm mọi dòng tiến độ của kịch bản đang bật."""
	if not cint(cai_dat().get("kb_bat")):
		return {"tat": 1}
	n = 0
	for r in frappe.db.sql("""SELECT p.kich_ban, p.user FROM `tabFeedback Playbook Progress` p
	                          JOIN `tabFeedback Playbook` k ON k.name = p.kich_ban
	                          JOIN tabUser u ON u.name = p.user
	                          WHERE k.dang_bat = 1 AND u.enabled = 1""", as_dict=True):
		try:
			cham(r.kich_ban, r.user, luc)
			frappe.db.commit()
			n += 1
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"kich_ban.cham_tat_ca {r.kich_ban} {r.user}"[:140], message=frappe.get_traceback())
	return {"cham": n}
