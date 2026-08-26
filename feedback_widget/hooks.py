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

# HAI KHOÁ boot khác nhau, mỗi khoá một cửa — KHÔNG phải hai bản của một luật:
#   `extend_bootinfo` → `boot.feedback_widget_settings`  (HIỂN THỊ: bật/tắt, vai, màu)
#   `boot_session`    → `boot.feedback_widget`           (THU THẬP: collect_usage, throttle…)
# Chú thích cũ ở đây từng cấm thêm `boot_session`; luật đó đúng khi hai hàm nhồi CÙNG một
# khoá, và sai ở đây — bỏ cửa dưới là bundle rơi vào nhánh an toàn "boot rỗng ⇒ KHÔNG tự
# thu": đo trên gương HTS 26/08 sau khi cài từ HEAD, nút góp ý hiện và vé gửi được nhưng sổ
# sự kiện đứng im 0 dòng, không một lỗi nào. `test_boot_payload.py` khoá lại việc này bằng
# cách đọc CHÍNH bundle: mọi khoá `ct.<x>` nó dùng đều phải có người nhồi.
# Khi bản gộp một cửa của phiên khác lên (extend_bootinfo tự gọi payload thu thập), xoá dòng
# `boot_session` — lúc ấy nó mới thành bản chép thứ hai.
extend_bootinfo = "feedback_widget.api.feedback.extend_bootinfo"
boot_session = "feedback_widget.cai_dat.boot_session"

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
