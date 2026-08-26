"""Gieo cài đặt mặc định MỘT LẦN, để màn Cài đặt nói đúng thứ hệ đang làm.

`cai_dat()` đã tự lùi về mặc định khi chưa có dòng nào, nên hệ chạy đúng kể cả không có
patch này. Nhưng màn Cài đặt lúc ấy hiện các ô Check TRỐNG trong khi tính năng đang BẬT —
giao diện nói ngược với hành vi, và người vận hành sẽ tin vào giao diện.

CHỈ gieo khoá CHƯA ai khai: một giá trị người ta đã đặt (kể cả `enabled = 0`) không bao
giờ bị patch này bật lại. Việc chuyển giá trị từ bảng cũ nằm ở `v3` — KHÔNG nhét vào đây,
vì patch này đã có trong Patch Log của site đang chạy nên sửa nó là sửa vào chỗ không
bao giờ chạy lại.
"""

from feedback_widget.cai_dat import gieo_mac_dinh


def execute():
    gieo_mac_dinh()
