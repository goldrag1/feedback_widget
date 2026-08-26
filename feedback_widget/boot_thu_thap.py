"""Cửa boot cho cấu hình THU THẬP — chịu được cả hai hình dạng của `cai_dat`.

VÌ SAO CÓ TỆP NÀY: `hooks.boot_session` từng trỏ thẳng `cai_dat.boot_session`. Trên cây DÙNG
CHUNG (hardlink cho bench chính + mọi slot) đang có bản sửa dở đổi tên hàm ấy thành
`payload_cho_trinh_duyet`, nên hook trỏ vào hàm không tồn tại ⇒ `AttributeError` ⇒
`SessionBootFailed` ⇒ **mọi site trên máy trả 500 ở boot** (26/08, phiên slot 1 báo).

Một hook boot KHÔNG ĐƯỢC PHÉP ném lỗi: nó không phải tính năng, nó là cả cái desk. Nên cửa
này (a) tự dò tên hàm đang có, (b) nuốt mọi lỗi và ghi log. Khi bản gộp một cửa lên xong
(`extend_bootinfo` tự nhồi payload thu thập), XOÁ cả tệp này lẫn dòng `boot_session`.
"""

import frappe


def boot_session(bootinfo):
    try:
        from feedback_widget import cai_dat as _cd

        ham = getattr(_cd, "boot_session", None)
        if ham is not None:
            ham(bootinfo)
            return
        # Bản đang đổi tên: hàm trả payload thay vì tự gắn vào boot, và chữ ký có/không `user`.
        dung = getattr(_cd, "payload_cho_trinh_duyet", None)
        if dung is not None:
            try:
                bootinfo["feedback_widget"] = dung(frappe.session.user)
            except TypeError:
                bootinfo["feedback_widget"] = dung()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "feedback_widget boot_thu_thap")
