"""Kịch bản màn — endpoint cho widget (spec §5, §6). Người dùng là NGƯỜI ĐANG ĐĂNG NHẬP;
không endpoint nào nhận "người dùng" làm tham số.

Mọi DocType của kịch bản chỉ System Manager đọc được (cố ý) — người dùng đi qua đây, và
mọi truy vấn ở đây lọc theo chính `frappe.session.user`.
"""

from datetime import timedelta

import frappe
from frappe.utils import cint, get_datetime, getdate, now_datetime

from feedback_widget import diem, kich_ban as kb, nhac
from feedback_widget.cai_dat import cai_dat, khong_xep_hang

TRANG_THAI_HUONG_DAN = ("Chưa xem", "Đang xem", "Đã xem", "Bỏ qua")


def _bat() -> bool:
	return bool(cint(cai_dat().get("kb_bat")))


def _toi():
	u = frappe.session.user
	return None if not u or u == "Guest" else u


def _so_phien_truoc(user, man, moc, tru_phien=None) -> int:
	where = ["user = %s", "screen_id LIKE %s", "ts < %s", "session_id IS NOT NULL", "session_id != ''"]
	args = [user, kb.mau_like(man), get_datetime(moc)]
	if tru_phien:
		where.append("session_id != %s"); args.append(tru_phien)
	return cint(frappe.db.sql(f"""SELECT COUNT(DISTINCT session_id) FROM `tabFeedback Event`
	                              WHERE {' AND '.join(where)}""", args)[0][0])


def _goi_cam_nhan(k, p) -> list:
	"""Chặng xong trong 7 ngày qua, có `hoi_cam_nhan`, chưa trả lời."""
	da = kb._j(p.cam_nhan)
	xong = kb._j(p.chang_xong)
	ra = []
	for c in k.chang:
		luc = xong.get(c.ma)
		if (c.loai == "Một lần" and cint(c.hoi_cam_nhan) and luc and c.ma not in da
				and get_datetime(luc) >= now_datetime() - timedelta(days=7)):
			ra.append({"chang": c.ma, "ten_chang": c.ten})
	return ra


@frappe.whitelist(methods=["POST"])
def cua_toi(screen_id: str = None, phien: str = None):
	"""Kịch bản của màn đang mở + tiến độ của tôi + mẹo tại chỗ + những gì chưa báo."""
	user = _toi()
	if not _bat() or not user or not screen_id:
		return None
	ten = kb.kich_ban_cua_man(screen_id)
	if not ten:
		return {"kich_ban": None, "chua_bao": diem.chua_bao(user)}
	k = frappe.get_doc("Feedback Playbook", ten)
	p = kb.tien_do(ten, user, tao=True)
	moi = []
	try:
		moi = kb.cham(ten, user)
	except Exception:
		frappe.log_error(title=f"kich_ban.cua_toi cham {ten}"[:140], message=frappe.get_traceback())
	p.reload()
	luc = now_datetime()
	moc = get_datetime(p.bat_dau)
	buoc_xong, chang_xong, duy_tri = kb._j(p.buoc_xong), kb._j(p.chang_xong), kb._j(p.duy_tri)

	da_quen = _so_phien_truoc(user, k.man, p.creation, phien) >= cint(cai_dat().get("phien_da_quen"))
	tu_bat = p.huong_dan == "Chưa xem" and not da_quen and bool(k.huong_dan)

	chang = []
	for c in sorted(k.chang, key=lambda x: cint(x.thu_tu)):
		ds = []
		ky = kb.ky_hien_tai(c, luc) if c.loai == "Duy trì" else None
		for b in sorted([b for b in k.buoc if b.chang == c.ma], key=lambda b: cint(b.idx)):
			if c.loai == "Duy trì":
				dem = kb.dem_buoc(b, k.man, user, max(ky[0], moc), ky[1]) if ky else (0, 0)
				xong = bool(ky) and dem[0] >= max(cint(b.so_lan), 1)
			else:
				xong = b.name in buoc_xong
				dem = (max(cint(b.so_lan), 1), max(cint(b.so_ngay), 1)) if xong else kb.dem_buoc(b, k.man, user, moc)
			ds.append({"mo_ta": b.mo_ta, "loai": b.loai, "xong": xong, "so_lan": dem[0], "so_ngay": dem[1],
			           "can_lan": max(cint(b.so_lan), 1), "can_ngay": max(cint(b.so_ngay), 1),
			           "diem": cint(b.diem) or cint(cai_dat().get("diem_buoc"))})
		muc = {"ma": c.ma, "ten": c.ten, "loai": c.loai, "xong": c.ma in chang_xong,
		       "hien_tai": c.ma == p.chang_hien_tai, "buoc": ds,
		       "diem": cint(c.diem) or cint(cai_dat().get("diem_chang" if c.loai == "Một lần" else "diem_ky_duy_tri"))}
		if c.loai == "Duy trì":
			tt = duy_tri.get(c.ma) or {}
			muc.update({"chuoi": kb.chuoi_hien_tai(c, tt, luc), "chuoi_dai_nhat": cint(tt.get("chuoi_dai_nhat")),
			            "han_hom_nay": ky[1].strftime("%H:%M") if ky else None, "hom_nay_nghi": not ky,
			            "dat_ky_nay": bool(ky and tt.get("ky_cuoi_dat") and get_datetime(tt["ky_cuoi_dat"]) == ky[0])})
		chang.append(muc)

	nv = frappe.db.sql("""SELECT m.name, m.chang_muc_tieu, m.chuoi_muc_tieu, m.het_han, a.trang_thai
	                      FROM `tabFeedback Mission Assignee` a JOIN `tabFeedback Mission` m ON m.name = a.parent
	                      WHERE m.kich_ban = %s AND a.user = %s ORDER BY m.creation DESC LIMIT 1""",
	                   (ten, user), as_dict=True)

	meo = []
	try:
		meo = nhac.meo_tai_cho(ten, user, screen_id)
	except Exception:
		frappe.log_error(title=f"kich_ban.meo_tai_cho {ten}"[:140], message=frappe.get_traceback())
	for m in moi:
		if m.get("loai") != "buoc":
			continue
		thu_tu = next((cint(b.idx) for b in k.buoc if b.mo_ta == m.get("mo_ta")), 0)
		t = next((t for t in k.meo if t.khi == "Xong bước" and cint(t.dieu_kien) == thu_tu), None)
		if t:
			meo.append({"loai": "meo", "noi_dung": t.noi_dung, "chi_vao": t.chi_vao, "khoa": f"buoc-{thu_tu}"})

	return {
		"kich_ban": ten, "ten": k.ten, "ly_do": k.ly_do, "duong_dan": k.duong_dan,
		"huong_dan": {"tu_bat": tu_bat, "trang_thai": p.huong_dan, "the": cint(p.huong_dan_the),
		              "cac_the": [{"tieu_de": h.tieu_de, "noi_dung": h.noi_dung, "chi_vao": h.chi_vao,
		                           "vi_tri": h.vi_tri} for h in sorted(k.huong_dan, key=lambda h: cint(h.thu_tu))]},
		"chang": chang,
		"nhiem_vu": ({"ten": nv[0].name, "chang_muc_tieu": nv[0].chang_muc_tieu, "trang_thai": nv[0].trang_thai,
		              "chuoi_muc_tieu": cint(nv[0].chuoi_muc_tieu),
		              "con_ngay": max((get_datetime(nv[0].het_han) - luc).days, 0) if nv[0].het_han else None}
		             if nv else None),
		"meo": meo,
		"hoi_cam_nhan": _goi_cam_nhan(k, p),
		"chua_bao": diem.chua_bao(user),
	}


@frappe.whitelist(methods=["POST"])
def huong_dan(kich_ban: str, trang_thai: str, the: int = 0) -> dict:
	user = _toi()
	if not _bat() or not user or trang_thai not in TRANG_THAI_HUONG_DAN:
		return {"ok": False}
	p = kb.tien_do(kich_ban, user, tao=True)
	frappe.db.set_value("Feedback Playbook Progress", p.name,
	                    {"huong_dan": trang_thai, "huong_dan_the": cint(the)}, update_modified=False)
	return {"ok": True}


@frappe.whitelist(methods=["POST"])
def cam_nhan(kich_ban: str, chang: str, y: str, chu: str = "", screen_id: str = None) -> dict:
	"""Thẻ "Màn này dùng thấy sao?" (spec §6.4). Chỉ 👍 không chữ ⇒ không tạo góp ý (khỏi
	đẩy Telegram vì một cú chạm); 👎 hoặc có chữ ⇒ góp ý thật, đi đúng đường của widget.
	`y = "bo_qua"` ⇒ ghi là đã hỏi để không hỏi lại chặng đó, KHÔNG cộng điểm (bỏ qua mà
	có điểm thì cú chạm "bỏ qua" thành cách lấy điểm rẻ nhất)."""
	user = _toi()
	if not _bat() or not user or y not in ("👍", "👎", "bo_qua"):
		return {"ok": False}
	k = frappe.get_doc("Feedback Playbook", kich_ban)
	if chang not in [c.ma for c in k.chang]:
		return {"ok": False}
	p = kb.tien_do(kich_ban, user, tao=True)
	da = kb._j(p.cam_nhan)
	if chang in da:
		return {"ok": True, "da_tra_loi": 1}
	da[chang] = y
	import json

	frappe.db.set_value("Feedback Playbook Progress", p.name, "cam_nhan",
	                    json.dumps(da, ensure_ascii=False), update_modified=False)
	if y == "bo_qua":
		return {"ok": True, "bo_qua": 1}
	diem.ghi_diem(user, cint(cai_dat().get("diem_cam_nhan")), "Cảm nhận",
	              f"Cảm nhận|{kich_ban}|{chang}|{user}", "Feedback Playbook", kich_ban)
	ve = None
	chu = (chu or "").strip()
	if y == "👎" or chu:
		from feedback_widget.api.feedback import collect

		ten_chang = next((c.ten for c in k.chang if c.ma == chang), chang)
		sid = screen_id or k.man.replace("*", "")
		frappe.flags.fbw_tu_cam_nhan = True
		try:
			r = collect(project=(cai_dat().get("project_name") or frappe.local.site),
			            screen_id=sid, screen_name=f"{k.ten} (cảm nhận sau chặng «{ten_chang}»)",
			            message=f"{y} {chu}".strip(), ts=now_datetime().isoformat(),
			            context={"route": sid, "nguon": "kich-ban-cam-nhan", "kich_ban": kich_ban, "chang": chang})
			ve = (r or {}).get("name")
		finally:
			frappe.flags.fbw_tu_cam_nhan = False
	return {"ok": True, "ve": ve}


@frappe.whitelist(methods=["POST"])
def da_bao() -> dict:
	user = _toi()
	if user:
		diem.danh_dau_da_bao(user)
	return {"ok": True}


@frappe.whitelist(methods=["GET", "POST"])
def thanh_tich() -> dict | None:
	user = _toi()
	if not _bat() or not user:
		return None
	tong = diem.tong_diem(user)
	hc = diem.huan_chuong_cua(user)
	ds = []
	for p in frappe.get_all("Feedback Playbook Progress", filters={"user": user},
	                        fields=["kich_ban", "chang_hien_tai", "chang_xong", "duy_tri"]):
		k = frappe.get_cached_doc("Feedback Playbook", p.kich_ban)
		if not k.dang_bat:
			continue
		xong = kb._j(p.chang_xong)
		dt = kb._j(p.duy_tri)
		ds.append({"ten": k.ten, "duong_dan": k.duong_dan,
		           "chang_xong": len([c for c in k.chang if c.ma in xong]), "so_chang": len(k.chang),
		           "chang_hien_tai": next((c.ten for c in k.chang if c.ma == p.chang_hien_tai), ""),
		           "chuoi_dai_nhat": max([cint(v.get("chuoi_dai_nhat")) for v in dt.values()] or [0])})
	return {"ten": frappe.db.get_value("User", user, "full_name") or user, "tong": tong,
	        "cap": diem.cap(tong), "nguong_ke": diem.nguong_ke(tong),
	        "huan_chuong": [{"ma": m, "ten": diem.DANH_MUC_HUAN_CHUONG.get(m, m), "so_lan": n} for m, n in hc.items()],
	        "kich_ban": ds}


def cong_ty_cua(users) -> dict:
	"""Công ty của từng người: Employee.company → User Permission Company (nếu đúng MỘT) →
	công ty mặc định toàn cục. Chịu được site không có HRMS (spec §6.6)."""
	ra = {}
	if not users:
		return ra
	if frappe.db.table_exists("Employee"):
		for r in frappe.db.sql("""SELECT user_id, company FROM `tabEmployee` WHERE user_id IN %s
		                          AND IFNULL(company, '') != '' ORDER BY status = 'Active' ASC""",
		                       (tuple(users),), as_dict=True):
			ra[r.user_id] = r.company
	thieu = [u for u in users if u not in ra]
	if thieu:
		for r in frappe.db.sql("""SELECT user, MIN(for_value) cty, COUNT(DISTINCT for_value) n FROM `tabUser Permission`
		                          WHERE allow = 'Company' AND user IN %s GROUP BY user""", (tuple(thieu),), as_dict=True):
			if cint(r.n) == 1:
				ra[r.user] = r.cty
	mac = frappe.db.get_default("company") or ""
	for u in users:
		ra.setdefault(u, mac)
	return ra


@frappe.whitelist(methods=["GET", "POST"])
def bang_vang(ky: str = "thang", cong_ty: str = None) -> dict | None:
	"""Ai cũng xem được (chủ đầu tư chốt 20/10). Không trả email; chỉ người có điểm > 0."""
	user = _toi()
	if not _bat() or not user:
		return None
	where, args = ["p.user NOT IN %s", "u.enabled = 1"], [tuple(khong_xep_hang()) or ("",)]
	if ky == "thang":
		d = getdate(now_datetime())
		where.append("p.creation >= %s"); args.append(d.replace(day=1))
	rows = frappe.db.sql(f"""SELECT p.user, u.full_name, SUM(p.diem) diem FROM `tabFeedback Point` p
	                         JOIN tabUser u ON u.name = p.user WHERE {' AND '.join(where)}
	                         GROUP BY p.user HAVING diem > 0 ORDER BY diem DESC""", args, as_dict=True)
	cty = cong_ty_cua([r.user for r in rows] + [user])
	cua_toi = cty.get(user) or ""
	loc = cua_toi if cong_ty is None else (None if cong_ty in ("", "__all__") else cong_ty)
	hang = []
	for r in rows:
		if loc and cty.get(r.user) != loc:
			continue
		tong = diem.tong_diem(r.user)
		hang.append({"hang": len(hang) + 1, "ten": r.full_name or "—", "cap": diem.cap(tong), "diem": cint(r.diem),
		             "la_toi": r.user == user,
		             "huan_chuong": [{"ma": m, "ten": diem.DANH_MUC_HUAN_CHUONG.get(m, m), "so_lan": n}
		                             for m, n in diem.huan_chuong_cua(r.user).items()]})
	return {"ky": ky, "cong_ty": loc or "__all__", "cong_ty_cua_toi": cua_toi,
	        "cac_cong_ty": sorted({c for c in cty.values() if c}), "hang": hang}
