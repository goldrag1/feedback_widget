"""Tiến độ của MỘT người trên MỘT kịch bản. Bước đã xong giữ nguyên kể cả khi sổ sự kiện bị dọn."""

import frappe
from frappe.model.document import Document


class FeedbackPlaybookProgress(Document):
	pass


def on_doctype_update():
	# Một cặp (kịch bản, người) đúng một dòng — cron và lượt mở màn có thể cùng tạo.
	frappe.db.add_unique("Feedback Playbook Progress", ["kich_ban", "user"], constraint_name="fbw_kb_user")
