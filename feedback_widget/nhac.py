"""Kịch bản màn — nhắc khi chậm mục tiêu / chậm tiến độ (spec §7).

Mỗi lời nhắc là MỘT `Feedback Notice` phạm vi "Một người" có `kich_ban` + `loai_nhac`: chính
Notice là sổ nhắc, và `Feedback Notice Seen.da_bam` đo được lời nhắc nào có tác dụng.

Luật chống ồn đặt TRƯỚC mọi lần gửi, vì người nhận ba lời nhắc vô ích sẽ đóng cái thứ tư mà
không đọc — và kéo theo cả thông báo thật (đo prod 20/10: 7 thông báo, 0 lượt bấm).
"""

from datetime import datetime, timedelta

import frappe
from frappe.utils import cint, get_datetime, get_time, now_datetime

from feedback_widget.cai_dat import cai_dat

# Ưu tiên khi vượt trần: N4 > N3 > N5 > N2 > N1 (số nhỏ = gửi trước).
UU_TIEN = {"N4": 0, "N3": 1, "N5": 2, "N2": 3, "N1": 4}


def _ngay_lam(ct=None) -> set:
	ct = ct or cai_dat()
	return {cint(x) for x in str(ct.get("ngay_lam_viec") or "1,2,3,4,5,6").split(",") if str(x).strip().isdigit()}


def trong_gio_lam(luc) -> bool:
	ct = cai_dat()
	luc = get_datetime(luc)
	if luc.isoweekday() not in _ngay_lam(ct):
		return False
	return get_time(ct.get("gio_lam_tu") or "08:00") <= luc.time() < get_time(ct.get("gio_lam_den") or "18:00")


def gio_lam_ke_tiep(luc) -> datetime:
	"""Đầu giờ làm của ngày làm việc KẾ TIẾP sau `luc` (không phải hôm nay)."""
	ct = cai_dat()
	tu = get_time(ct.get("gio_lam_tu") or "08:00")
	d = get_datetime(luc).date() + timedelta(days=1)
	for _i in range(8):
		if d.isoweekday() in _ngay_lam(ct):
			break
		d += timedelta(days=1)
	return datetime.combine(d, tu)


def _het_han(luc) -> datetime:
	ct = cai_dat()
	return datetime.combine(gio_lam_ke_tiep(luc).date(), get_time(ct.get("gio_lam_den") or "18:00"))


def _nhac_hom_nay(user, luc, kich_ban=None, loai=None, nhiem_vu=None) -> int:
	d = get_datetime(luc).date()
	where = ["n.loai_nhac IS NOT NULL", "n.loai_nhac != ''", "u.user = %s", "DATE(n.bat_dau) = %s"]
	args = [user, d]
	if kich_ban:
		where.append("n.kich_ban = %s"); args.append(kich_ban)
	if loai:
		where.append("n.loai_nhac = %s"); args.append(loai)
	if nhiem_vu:
		where.append("n.nhiem_vu = %s"); args.append(nhiem_vu)
	return cint(frappe.db.sql(f"""SELECT COUNT(DISTINCT n.name) FROM `tabFeedback Notice` n
	                              JOIN `tabFeedback Notice User` u ON u.parent = n.name
	                                AND u.parenttype = 'Feedback Notice'
	                              WHERE {' AND '.join(where)}""", args)[0][0])


def da_gui_bao_gio(user, loai, nhiem_vu) -> bool:
	return bool(frappe.db.sql("""SELECT 1 FROM `tabFeedback Notice` n
	                             JOIN `tabFeedback Notice User` u ON u.parent = n.name AND u.parenttype = 'Feedback Notice'
	                             WHERE n.loai_nhac = %s AND n.nhiem_vu = %s AND u.user = %s LIMIT 1""",
	                          (loai, nhiem_vu, user)))


def gui_nhac(user, kich_ban, loai, tieu_de, noi_dung, duong_dan, nhiem_vu=None, luc=None,
             bo_qua_tran=False):
	"""Gửi một lời nhắc nếu luật chống ồn cho phép. Trả tên Notice, hoặc None nếu bị chặn.
	`bo_qua_tran` (thẻ "được mời", thẻ tổng hợp cho người giao): bỏ qua giờ làm + trần, vẫn
	không gửi trùng trong ngày."""
	ct = cai_dat()
	luc = get_datetime(luc) if luc else now_datetime()
	if not cint(ct.get("kb_bat")) or not user or not frappe.db.get_value("User", user, "enabled"):
		return None
	if _nhac_hom_nay(user, luc, kich_ban, loai, nhiem_vu):
		return None                                     # cùng loại, cùng kịch bản, đã gửi hôm nay
	if not bo_qua_tran:
		if not trong_gio_lam(luc):
			return None
		if kich_ban:
			p = frappe.db.get_value("Feedback Playbook Progress", {"kich_ban": kich_ban, "user": user},
			                        ["nhac_tam_hoan_den", "so_lan_bo_qua_lien"], as_dict=True)
			if p and p.nhac_tam_hoan_den and get_datetime(p.nhac_tam_hoan_den) > luc:
				return None
			if p and cint(p.so_lan_bo_qua_lien) >= max(cint(ct.get("nhac_dung_sau_bo_qua")), 1):
				return None
		if _nhac_hom_nay(user, luc) >= cint(ct.get("nhac_toi_da_ngay")):
			return None
		if kich_ban and _nhac_hom_nay(user, luc, kich_ban) >= cint(ct.get("nhac_toi_da_kb_ngay")):
			return None
	tb = frappe.get_doc({
		"doctype": "Feedback Notice", "tieu_de": tieu_de[:140], "noi_dung": noi_dung, "duong_dan": duong_dan,
		"pham_vi": "Một người", "cac_nguoi": [{"user": user}], "dang_bat": 1,
		"bat_dau": luc, "het_han": _het_han(luc),
		"kich_ban": kich_ban, "loai_nhac": loai, "nhiem_vu": nhiem_vu,
		"project": ct.get("project_name") or frappe.local.site,
	})
	tb.insert(ignore_permissions=True)
	if kich_ban:
		frappe.db.set_value("Feedback Playbook Progress", {"kich_ban": kich_ban, "user": user},
		                    "lan_nhac_cuoi", luc, update_modified=False)
	return tb.name


def _ten(user) -> str:
	return frappe.db.get_value("User", user, "full_name") or user


def _ung_vien(m, kb, a, p, luc, ct) -> list:
	"""Các lời nhắc N1–N5 mà MỘT người được giao đang đủ điều kiện nhận, chưa lọc trần."""
	from feedback_widget import kich_ban as k

	ra = []
	bd, hh = get_datetime(m.bat_dau), get_datetime(m.het_han)
	dai = max((hh - bd).total_seconds(), 1)
	da_troi = (luc - bd).total_seconds() / dai
	ch_mt = next((c for c in kb.chang if c.ma == m.chang_muc_tieu), None)
	if not ch_mt:
		return ra
	chang_xong, duy_tri = k._j(p.chang_xong), k._j(p.duy_tri)
	buoc_xong = k._j(p.buoc_xong)
	ten_kb = kb.ten

	if luc > hh:
		ra.append(("N4", f"«{ten_kb}» đã quá hạn — vẫn làm tiếp được",
		           "Phần đã xong vẫn được giữ và tính điểm. Mở để làm nốt →"))
		return ra
	if (hh - luc) <= timedelta(hours=cint(ct.get("nhac_sap_het_gio"))) and not da_gui_bao_gio(a.user, "N3", m.name):
		ra.append(("N3", f"Còn {max(int((hh - luc).total_seconds() // 3600), 1)} giờ để xong «{ch_mt.ten}» của «{ten_kb}»",
		           "Mở để làm nốt các bước còn lại →"))
	if ch_mt.loai == "Duy trì":
		ky = k.ky_hien_tai(ch_mt, luc)
		if ky and ky[1] - timedelta(hours=2) <= luc < ky[1]:
			tt = duy_tri.get(ch_mt.ma) or {}
			if not (tt.get("ky_cuoi_dat") and get_datetime(tt["ky_cuoi_dat"]) == ky[0]):
				chuoi = k.chuoi_hien_tai(ch_mt, tt, luc)
				them = f" — chuỗi {chuoi} ngày đang chờ" if chuoi else ""
				ra.append(("N5", f"Hôm nay chưa xong «{ten_kb}»{them}",
				           f"Hạn hôm nay {ky[1].strftime('%H:%M')}. Mở để làm ngay →"))
	co_mo = bool(frappe.db.sql("""SELECT 1 FROM `tabFeedback Event` WHERE user = %s AND ts >= %s
	                              AND screen_id LIKE %s LIMIT 1""", (a.user, bd, k.mau_like(kb.man))))
	if not co_mo and (luc - bd) >= timedelta(hours=cint(ct.get("nhac_chua_mo_gio"))):
		ra.append(("N1", f"Anh/chị được mời dùng thử «{ten_kb}»",
		           "Bắt đầu bằng hướng dẫn 1 phút →"))
	if ch_mt.loai == "Một lần" and da_troi >= 0.4 and ch_mt.ma not in chang_xong:
		thu_tu_mt = cint(ch_mt.thu_tu)
		can = [b for b in kb.buoc if any(c.ma == b.chang and c.loai == "Một lần" and cint(c.thu_tu) <= thu_tu_mt
		                                 for c in kb.chang)]
		xong = [b for b in can if b.name in buoc_xong]
		if can and len(xong) / len(can) < da_troi - cint(ct.get("nhac_cham_bien")) / 100:
			ke = next((b for b in sorted(can, key=lambda b: cint(b.idx)) if b.name not in buoc_xong), None)
			con = max((hh - luc).days, 0)
			ra.append(("N2", f"«{ten_kb}»: xong {len(xong)}/{len(can)} bước, còn {con} ngày",
			           f"Bước kế: {ke.mo_ta} →" if ke else "Mở để làm tiếp →"))
	return ra


def nhac_kich_ban(luc=None) -> dict:
	"""Cron 15 phút: tính lời nhắc cho mọi người được giao, theo ưu tiên, qua luật chống ồn."""
	from feedback_widget import kich_ban as k

	ct = cai_dat()
	if not cint(ct.get("kb_bat")):
		return {"tat": 1}
	luc = get_datetime(luc) if luc else now_datetime()
	gui, tong_hop = [], {}
	theo_nguoi = {}
	for m in frappe.get_all("Feedback Mission", filters={"nhac": 1},
	                        fields=["name", "kich_ban", "chang_muc_tieu", "bat_dau", "het_han", "nguoi_giao", "owner"]):
		if not m.bat_dau or not m.het_han or not frappe.db.get_value("Feedback Playbook", m.kich_ban, "dang_bat"):
			continue
		kb = frappe.get_cached_doc("Feedback Playbook", m.kich_ban)
		for a in frappe.get_all("Feedback Mission Assignee", filters={"parent": m.name, "parenttype": "Feedback Mission"},
		                        fields=["name", "user", "trang_thai"]):
			if a.trang_thai == "Hoàn thành":
				continue
			p = k.tien_do(m.kich_ban, a.user, tao=True, luc=m.bat_dau)
			if luc > get_datetime(m.het_han):
				if a.trang_thai != "Quá hạn":
					frappe.db.set_value("Feedback Mission Assignee", a.name, "trang_thai", "Quá hạn", update_modified=False)
				giao = m.nguoi_giao or m.owner
				buoc_xong = k._j(p.buoc_xong)
				ke = next((b.mo_ta for b in sorted(kb.buoc, key=lambda b: cint(b.idx)) if b.name not in buoc_xong), "")
				tong_hop.setdefault(giao, []).append(
					f"{_ten(a.user)} — «{kb.ten}»: kẹt ở «{ke}»" + (
						f", đã bỏ qua {cint(p.so_lan_bo_qua_lien)} lời nhắc — có thể cần nói chuyện trực tiếp"
						if cint(p.so_lan_bo_qua_lien) >= cint(ct.get("nhac_dung_sau_bo_qua")) else ""))
				if da_gui_bao_gio(a.user, "N4", m.name):
					continue
			elif cint(p.so_lan_bo_qua_lien) >= cint(ct.get("nhac_dung_sau_bo_qua")):
				giao = m.nguoi_giao or m.owner
				tong_hop.setdefault(giao, []).append(
					f"{_ten(a.user)} đã bỏ qua {cint(p.so_lan_bo_qua_lien)} lời nhắc «{kb.ten}» — có thể cần nói chuyện trực tiếp")
				continue
			for loai, td, nd in _ung_vien(m, kb, a, p, luc, ct):
				theo_nguoi.setdefault(a.user, []).append((UU_TIEN[loai], loai, m, kb, td, nd))
	for user, ds in theo_nguoi.items():
		for _ut, loai, m, kb, td, nd in sorted(ds, key=lambda x: x[0]):
			ten = gui_nhac(user, kb.name, loai, td, nd, kb.duong_dan, nhiem_vu=m.name, luc=luc)
			if ten:
				gui.append((user, loai, ten))
	for giao, dong in tong_hop.items():
		if giao and dong and trong_gio_lam(luc):
			ten = gui_nhac(giao, None, "N4-tong-hop", f"{len(dong)} người đang chậm kịch bản được giao",
			               "\n".join(dong), "/app/query-report/Tien Do Kich Ban", luc=luc, bo_qua_tran=True)
			if ten:
				gui.append((giao, "N4-tong-hop", ten))
	return {"gui": gui}


def meo_tai_cho(kich_ban, user, screen_id, luc=None) -> list:
	"""N6 (kẹt vì bị chặn) + N7 (hướng dẫn bỏ dở) + mẹo "Mở lần thứ": thẻ TẠI CHỖ, hiện cho mọi
	người đang mở màn, không qua trần (không phải nhắc đẩy)."""
	from feedback_widget import kich_ban as k

	luc = get_datetime(luc) if luc else now_datetime()
	kb = frappe.get_cached_doc("Feedback Playbook", kich_ban)
	p = k.tien_do(kich_ban, user, tao=False)
	ra = []
	chan = frappe.db.sql("""SELECT IFNULL(signature, message) sig, MAX(message) message, COUNT(*) n
	                        FROM `tabFeedback Event` WHERE user = %s AND kind = 'chan' AND ts >= %s
	                          AND screen_id LIKE %s GROUP BY IFNULL(signature, message) HAVING n >= 3""",
	                     (user, luc - timedelta(hours=1), k.mau_like(kb.man)), as_dict=True)
	for r in chan:
		meo = next((t for t in kb.meo if t.khi == "Bị chặn" and t.dieu_kien
		            and (t.dieu_kien in (r.message or "") or t.dieu_kien in (r.sig or ""))), None)
		if meo:
			ra.append({"loai": "N6", "noi_dung": meo.noi_dung, "chi_vao": meo.chi_vao, "khoa": r.sig})
		else:
			ra.append({"loai": "N6", "noi_dung": "Có vẻ đang vướng ở đây. Gửi góp ý (đã kèm sẵn màn) →",
			           "hanh_dong": "gop_y", "khoa": r.sig})
	if p and p.huong_dan == "Đang xem":
		con = max(len(kb.huong_dan) - cint(p.huong_dan_the), 1)
		ra.append({"loai": "N7", "noi_dung": f"Xem tiếp hướng dẫn (còn {con} thẻ)?", "hanh_dong": "huong_dan"})
	lan = cint(frappe.db.sql("""SELECT COUNT(DISTINCT session_id) FROM `tabFeedback Event`
	                            WHERE user = %s AND screen_id LIKE %s""", (user, k.mau_like(kb.man)))[0][0])
	for t in kb.meo:
		if t.khi == "Mở lần thứ" and cint(t.dieu_kien) and cint(t.dieu_kien) == lan:
			ra.append({"loai": "meo", "noi_dung": t.noi_dung, "chi_vao": t.chi_vao, "khoa": f"lan-{lan}"})
	return ra


def theo_da_xem(thong_bao, user, da_bam: int, tam_hoan: int, luc=None) -> None:
	"""Nối từ `api.thong_bao.da_xem`: thẻ nhắc của kịch bản đổi trạng thái chống ồn của người đó.
	Mở ⇒ đếm bỏ qua về 0 · "Để mai" ⇒ hoãn tới giờ làm kế tiếp · ✕ ⇒ +1 lần bỏ qua.
	Thẻ tự ẩn sau vài giây KHÔNG gọi vào đây, nên không tính là bỏ qua."""
	tb = frappe.db.get_value("Feedback Notice", thong_bao, ["kich_ban", "loai_nhac"], as_dict=True)
	if not tb or not tb.kich_ban or not tb.loai_nhac:
		return
	ten = frappe.db.get_value("Feedback Playbook Progress", {"kich_ban": tb.kich_ban, "user": user}, "name")
	if not ten:
		return
	if cint(da_bam):
		frappe.db.set_value("Feedback Playbook Progress", ten, "so_lan_bo_qua_lien", 0, update_modified=False)
	elif cint(tam_hoan):
		frappe.db.set_value("Feedback Playbook Progress", ten, "nhac_tam_hoan_den",
		                    gio_lam_ke_tiep(luc or now_datetime()), update_modified=False)
	else:
		n = cint(frappe.db.get_value("Feedback Playbook Progress", ten, "so_lan_bo_qua_lien"))
		frappe.db.set_value("Feedback Playbook Progress", ten, "so_lan_bo_qua_lien", n + 1, update_modified=False)
