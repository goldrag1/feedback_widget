app_name = "feedback_widget"
app_title = "Feedback Widget"
app_publisher = "NextStar"
app_description = (
    "Drop-in floating feedback widget with element pointer + tag chips + context bundle. "
    "Stores comments as Feedback Comment DocType and mirrors raw payload to "
    "sites/<site>/private/feedback/<project>.jsonl for AI coding agents."
)
app_email = "long@nextstar.vn"
app_license = "ISC"
app_version = "1.1.0"

# Bundle that auto-mounts the widget on every desk page with Frappe-aware
# callbacks. Cache-bust via content hash from assets.json — no ?version= suffix.
app_include_js = ["feedback_widget.bundle.js"]

# MỘT cửa boot duy nhất: `extend_bootinfo` (bản 24/08) — không thêm `boot_session` song
# song, vì hai hàm cùng nhồi cài đặt vào boot là hai bản của một luật, và trình duyệt sẽ
# đọc bản nào là do thứ tự nạp quyết định.
extend_bootinfo = "feedback_widget.api.feedback.extend_bootinfo"

scheduler_events = {
    "cron": {
        # 15 phút/lần: đủ nhanh để người trực biết trong ca, đủ thưa để không phải
        # nghĩ về tải. Mốc đọc lưu ở db.set_global nên chạy lại không nhân đôi vé.
        "*/15 * * * *": ["feedback_widget.tac_vu.bac_cau_error_log"],
        # Tổng kết tự kiểm giờ trong hàm (cấu hình được, không đúc vào cron).
        "0 * * * *": ["feedback_widget.tac_vu.tong_ket_ngay"],
    },
    "daily": ["feedback_widget.tac_vu.don_so_cu"],
}
