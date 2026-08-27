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
            # Nhớ TRẠNG THÁI CŨ để `on_update` biết vé vừa được xử lý xong hay chỉ được
            # sửa vặt: sau khi lưu thì `has_value_changed` không còn trả lời được nữa.
            self.flags.vua_doi_trang_thai = True

    def on_update(self):
        # Vé xử lý xong thì người gõ phải biết — đo trên site thật: 74 vé Resolved, 0 lượt
        # báo ngược. Đặt ở `on_update` chứ không ở script đóng vé: Desk, API và script là
        # ba đường khác nhau, ba bản chép sẽ trôi lệch ngay lần đầu.
        if not self.flags.get("vua_doi_trang_thai"):
            return
        from feedback_widget.bao_ve_da_xu_ly import thu_bao

        thu_bao(self)
