# Copyright (c) 2026, DCNET and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FeedbackSettings(Document):
	def on_update(self):
		frappe.clear_document_cache("Feedback Settings")
