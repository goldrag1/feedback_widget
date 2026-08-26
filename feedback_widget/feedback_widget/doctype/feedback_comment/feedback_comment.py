import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class FeedbackComment(Document):
    def before_save(self):
        if self.is_new():
            if not self.status_changed_at:
                # ĐỒNG HỒ MÁY CHỦ, không lấy `self.ts`: `ts` do trình duyệt gửi (ISO, giờ UTC)
                # nên trên site VN nó sớm hơn sổ sự kiện 7 tiếng — mà mục "Hồi quy" so
                # `Event.ts > status_changed_at`, tức mọi sự kiện trong 7 tiếng ấy đọc thành
                # "lỗi quay lại sau khi đóng". Sổ sự kiện đã đóng dấu ở máy chủ; mốc này phải
                # cùng một chiếc đồng hồ với nó.
                self.status_changed_at = now_datetime()
            return
        if self.has_value_changed("status") or self.has_value_changed("status_note"):
            self.status_changed_at = now_datetime()
