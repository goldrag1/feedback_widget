"""Ai đã XEM / đã BẤM một thông báo — để đo, không phải để trang trí.

Không đo thì không trả lời được câu quan trọng nhất: gửi xong có ai bấm vào xem thử không.
0 lượt bấm nghĩa là gửi sai người hoặc viết sai lời, không phải "người dùng thờ ơ".
"""

from frappe.model.document import Document


class FeedbackNoticeSeen(Document):
	pass
