"""Thanh bên (Workspace Sidebar) của module Feedback Widget — dọn và bổ sung sau migrate.

Workspace "Feedback" đã gỡ khỏi app (8560a89) nhưng thanh bên tự sinh của module vẫn giữ mục
"Home" trỏ vào nó. Desk v16 vẽ thanh bên theo MODULE cho mọi báo cáo/chứng từ không có mục
riêng, và `sidebar_item.js` đọc `frappe.workspaces[slug].public` ⇒ TypeError, trang báo cáo
trắng (đo trên mirror 20/10 với hai báo cáo kịch bản). Ghi thẳng dòng con, không `doc.save()`:
lưu cả thanh bên trong developer_mode là xuất ngược JSON ra đĩa.
"""

import frappe

MODULE = "Feedback Widget"
MUC_THEM = (  # (link_type, link_to, label) — lối vào của kịch bản màn (spec §6.7)
	("DocType", "Feedback Playbook", "Feedback Playbook"),
	("DocType", "Feedback Mission", "Feedback Mission"),
	("Report", "Tien Do Kich Ban", "Tien Do Kich Ban"),
	("Report", "Man Chua Ai Dung", "Man Chua Ai Dung"),
)


def don_va_bo_sung() -> dict:
	ra = {"xoa": 0, "them": 0}
	if not frappe.db.table_exists("Workspace Sidebar"):
		return ra
	for sb in frappe.get_all("Workspace Sidebar", filters={"module": MODULE}, pluck="name"):
		for it in frappe.get_all("Workspace Sidebar Item", filters={"parent": sb, "link_type": "Workspace"},
		                         fields=["name", "link_to"]):
			if not it.link_to or not frappe.db.exists("Workspace", it.link_to):
				frappe.db.delete("Workspace Sidebar Item", {"name": it.name})
				ra["xoa"] += 1
		idx = frappe.db.sql("SELECT IFNULL(MAX(idx), 0) FROM `tabWorkspace Sidebar Item` WHERE parent = %s", sb)[0][0]
		for loai, dich, nhan in MUC_THEM:
			if not frappe.db.exists(loai, dich):
				continue
			if frappe.db.exists("Workspace Sidebar Item", {"parent": sb, "link_type": loai, "link_to": dich}):
				continue
			idx += 1
			frappe.get_doc({"doctype": "Workspace Sidebar Item", "parent": sb, "parenttype": "Workspace Sidebar",
			                "parentfield": "items", "type": "Link", "link_type": loai, "link_to": dich,
			                "label": nhan, "idx": idx}).db_insert()
			ra["them"] += 1
	if ra["xoa"] or ra["them"]:
		frappe.db.commit()
		frappe.cache.delete_key("bootinfo")
	return ra
