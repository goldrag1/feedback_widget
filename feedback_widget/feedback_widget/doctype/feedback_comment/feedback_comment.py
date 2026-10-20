import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class FeedbackComment(Document):
    def before_save(self):
        self._co_ich_theo_trang_thai()
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

    def _co_ich_theo_trang_thai(self):
        """Kịch bản màn §8.2: vé người gõ vừa CHUYỂN sang Resolved thì mặc định là góp ý có
        ích — đợi người duyệt tick tay thì không ai tick, và đường thưởng chết y như kênh thông
        báo cũ (0 lượt bấm). Người duyệt vẫn tắt được: chỉ bật khi lượt lưu này không tự sửa ô."""
        if int(self.thanh_cai_tien or 0):
            self.co_ich = 1
        if (not self.is_new() and self.status == "Resolved" and self.has_value_changed("status")
                and not self.has_value_changed("co_ich") and self.source == "user"):
            self.co_ich = 1

    def after_insert(self):
        # Bước "Góp ý trên màn" của kịch bản màn: chấm nền, sau commit, không chặn lượt gửi vé.
        from feedback_widget.cai_dat import cai_dat

        if self.source != "user" or not int(cai_dat().get("kb_bat") or 0):
            return
        args = {"user": self.submitter_user, "screen_ids": [self.screen_id]}
        if frappe.flags.in_test:
            from feedback_widget.kich_ban import cham_theo_man

            cham_theo_man(**args)
        else:
            frappe.enqueue("feedback_widget.kich_ban.cham_theo_man", queue="short",
                           enqueue_after_commit=True, **args)

    def on_update(self):
        from feedback_widget.diem import theo_gop_y

        theo_gop_y(self)
        # Vé xử lý xong thì người gõ phải biết — đo trên site thật: 74 vé Resolved, 0 lượt
        # báo ngược. Đặt ở `on_update` chứ không ở script đóng vé: Desk, API và script là
        # ba đường khác nhau, ba bản chép sẽ trôi lệch ngay lần đầu.
        if not self.flags.get("vua_doi_trang_thai"):
            return
        from feedback_widget.bao_ve_da_xu_ly import thu_bao

        thu_bao(self)
