"""Gieo lại mặc định cho những khoá bảng gộp mới sinh ra.

`v1` đã nằm trong Patch Log của mọi site đang chạy nên nó KHÔNG chạy lại — mà lượt gộp
26/08 lại thêm hàng loạt khoá mới (hiển thị: `enable_on_desk`, `enable_on_portal`,
`allow_all_roles`, màu…). Kết quả đo trên prod ngay sau lượt gộp:

    màn Cài đặt:  enable_on_desk = 0 · enable_on_portal = 0 · allow_all_roles = 0
    cai_dat():    enable_on_desk = 1 · enable_on_portal = 1 · allow_all_roles = 1

Với Single, `default` trong DocType JSON KHÔNG được áp khi thiếu dòng, nên giao diện nói
ngược với hành vi — và cú Save đầu tiên của người vận hành ghi chết mấy số 0 đó: widget
biến mất khỏi desk của tất cả mọi người, không một dòng lỗi. Patch này ghi thứ hệ ĐANG
dùng vào đúng chỗ giao diện đọc; khoá nào đã khai thì giữ nguyên.
"""

from feedback_widget.cai_dat import gieo_mac_dinh


def execute():
    thieu = gieo_mac_dinh()
    if thieu:
        print("feedback_widget: đã gieo mặc định cho", ", ".join(sorted(thieu)))
