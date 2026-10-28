"""Lập / cập nhật kịch bản màn + giao việc từ một tệp JSON (spec §11, §12).

Chạy từ thư mục `sites/` của bench (mặc định CHỈ IN KẾ HOẠCH, không ghi gì):

    cd sites && ../env/bin/python ../apps/feedback_widget/scripts/lap_kich_ban.py \\
        --site erp.htsfood.com ../apps/feedback_widget/scripts/kich_ban/hts_dot1.json [--apply]

Lặp lại được (idempotent) theo `man`:
- Kịch bản đã có ⇒ cập nhật tại chỗ. Chặng khớp theo `ma`, bước khớp theo (chặng, mô tả): dòng
  bước GIỮ NGUYÊN `name` vì `Feedback Playbook Progress.buoc_xong` khoá theo tên dòng — xoá rồi
  tạo lại là xoá tiến độ của mọi người. Bước có trong máy mà không có trong tệp: chỉ báo, không xoá.
  Hướng dẫn và mẹo không mang tiến độ nên thay nguyên bảng.
- Giao việc: đã có nhiệm vụ cùng (kịch bản, người, chặng mục tiêu) thì bỏ qua. Người không mở
  được màn thì `Feedback Mission.validate` chặn (và ghi sổ) — script báo lý do rồi làm tiếp.
"""

import argparse
import json
import os
import sys

TRUONG_KB = ("ten", "duong_dan", "ly_do", "nguon", "moi_tu")


def _chuan(v):
	return "" if v is None else str(v)


def _thay_doi(doc, moi: dict, truong) -> list:
	return [f for f in truong if f in moi and _chuan(doc.get(f)) != _chuan(moi[f])]


def ke_hoach_kich_ban(frappe, kb: dict) -> dict:
	ten = frappe.db.get_value("Feedback Playbook", {"man": kb["man"]}, "name")
	if not ten:
		return {"man": kb["man"], "viec": "tạo", "ten": None}
	d = frappe.get_doc("Feedback Playbook", ten)
	co_buoc = {(b.chang, b.mo_ta) for b in d.buoc}
	moi_buoc = {(b["chang"], b["mo_ta"]) for b in kb.get("buoc", [])}
	return {"man": kb["man"], "viec": "cập nhật", "ten": ten,
	        "truong_doi": _thay_doi(d, kb, TRUONG_KB),
	        "chang_moi": [c["ma"] for c in kb.get("chang", []) if c["ma"] not in {x.ma for x in d.chang}],
	        "buoc_moi": sorted(moi_buoc - co_buoc), "buoc_thua_khong_xoa": sorted(co_buoc - moi_buoc)}


def ap_dung_kich_ban(frappe, kb: dict) -> str:
	ten = frappe.db.get_value("Feedback Playbook", {"man": kb["man"]}, "name")
	huong_dan = [dict(h, thu_tu=i + 1) for i, h in enumerate(kb.get("huong_dan", []))]
	if not ten:
		d = frappe.get_doc({"doctype": "Feedback Playbook", "man": kb["man"], "dang_bat": 1,
		                    **{f: kb.get(f) for f in TRUONG_KB}, "huong_dan": huong_dan,
		                    "chang": kb.get("chang", []), "buoc": kb.get("buoc", []), "meo": kb.get("meo", [])})
		d.insert(ignore_permissions=True)
		return d.name
	d = frappe.get_doc("Feedback Playbook", ten)
	for f in TRUONG_KB:
		if f in kb:
			d.set(f, kb[f])
	d.set("huong_dan", huong_dan)
	d.set("meo", kb.get("meo", []))
	cu_chang = {c.ma: c for c in d.chang}
	for c in kb.get("chang", []):
		if c["ma"] in cu_chang:
			cu_chang[c["ma"]].update(c)
		else:
			d.append("chang", c)
	cu_buoc = {(b.chang, b.mo_ta): b for b in d.buoc}
	for b in kb.get("buoc", []):
		dong = cu_buoc.get((b["chang"], b["mo_ta"]))
		if dong:
			dong.update(b)
		else:
			d.append("buoc", b)
	d.save(ignore_permissions=True)
	return d.name


def giao(frappe, g: dict, ten_kb: str, apply: bool) -> list:
	from frappe.utils import add_days, now_datetime

	ra = []
	for u in g["nguoi"]:
		co = frappe.db.sql("""SELECT m.name FROM `tabFeedback Mission` m JOIN `tabFeedback Mission Assignee` a
		                      ON a.parent = m.name WHERE m.kich_ban = %s AND a.user = %s AND m.chang_muc_tieu = %s""",
		                   (ten_kb, u, g["chang_muc_tieu"]))
		if co:
			ra.append(f"  = {u}: đã giao ({co[0][0]})")
			continue
		if not apply:
			ra.append(f"  + {u}: sẽ giao chặng «{g['chang_muc_tieu']}», hạn {g.get('so_ngay', 7)} ngày")
			continue
		luc = now_datetime()
		try:
			m = frappe.get_doc({"doctype": "Feedback Mission", "kich_ban": ten_kb, "chang_muc_tieu": g["chang_muc_tieu"],
			                    "chuoi_muc_tieu": g.get("chuoi_muc_tieu") or 3, "bat_dau": luc,
			                    "het_han": add_days(luc, g.get("so_ngay") or 7), "nhac": 1,
			                    "nguoi_nhan": [{"user": u}]}).insert(ignore_permissions=True)
			frappe.db.commit()
			ra.append(f"  + {u}: đã giao ({m.name})")
		except frappe.ValidationError as e:
			frappe.db.rollback()
			ra.append(f"  ! {u}: KHÔNG giao được — {frappe.utils.strip_html(str(e))}")
	return ra


def chay(frappe, du: dict, apply: bool) -> int:
	loi = 0
	for kb in du["kich_ban"]:
		kh = ke_hoach_kich_ban(frappe, kb)
		print(f"[{kh['viec']}] {kb['ten']} ({kb['man']})" + (f" = {kh['ten']}" if kh["ten"] else ""))
		for k in ("truong_doi", "chang_moi", "buoc_moi", "buoc_thua_khong_xoa"):
			if kh.get(k):
				print(f"    {k}: {kh[k]}")
		if apply:
			try:
				ten = ap_dung_kich_ban(frappe, kb)
				frappe.db.commit()
				print(f"    → đã ghi {ten}")
			except Exception as e:
				frappe.db.rollback()
				loi += 1
				print(f"    ! LỖI: {e}")
	for g in du.get("giao", []):
		ten_kb = frappe.db.get_value("Feedback Playbook", {"man": g["man"]}, "name")
		print(f"[giao] {g['man']} → {', '.join(g['nguoi'])}")
		if not ten_kb:
			print("  (kịch bản chưa có — chạy --apply để tạo trước)")
			continue
		for dong in giao(frappe, g, ten_kb, apply):
			print(dong)
			loi += dong.lstrip().startswith("!")
	print("ĐÃ GHI." if apply else "CHỈ IN KẾ HOẠCH — thêm --apply để ghi.")
	return loi


def main():
	p = argparse.ArgumentParser()
	p.add_argument("tep")
	p.add_argument("--site", required=True)
	p.add_argument("--apply", action="store_true")
	a = p.parse_args()
	du = json.load(open(a.tep, encoding="utf-8"))
	import frappe

	frappe.init(site=a.site, sites_path=os.getcwd())
	frappe.connect()
	frappe.set_user("Administrator")
	try:
		sys.exit(1 if chay(frappe, du, a.apply) else 0)
	finally:
		frappe.destroy()


if __name__ == "__main__":
	main()
