import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class FeedbackComment(Document):
    def before_save(self):
        if self.is_new():
            if not self.status_changed_at:
                self.status_changed_at = self.ts or now_datetime()
            return
        if self.has_value_changed("status") or self.has_value_changed("status_note"):
            self.status_changed_at = now_datetime()
