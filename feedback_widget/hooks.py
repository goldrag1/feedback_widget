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

# MỘT cửa boot duy nhất: `extend_bootinfo` nhồi CẢ HAI khoá —
#   `boot.feedback_widget_settings` (HIỂN THỊ: bật/tắt, vai, màu)
#   `boot.feedback_widget`          (THU THẬP: collect_usage, throttle, sample…)
# Bản 26/08 từng phải mở thêm cửa `boot_session` vì bản gộp còn dở; nay gộp xong thì cửa
# ấy là bản chép thứ hai (và một hook boot ném lỗi = mọi site 500 — đã xảy ra thật vì
# chính nó). Bỏ cửa dưới mà quên nhồi `boot.feedback_widget` thì bundle rơi vào nhánh an
# toàn "boot rỗng ⇒ KHÔNG tự thu": sổ sự kiện đứng im 0 dòng, không một lỗi nào.
# `tests/test_boot_payload.py` khoá lại đúng việc đó — nó đọc CHÍNH bundle, rút mọi khoá
# `ct.<x>` và đòi boot phải có đủ.
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
