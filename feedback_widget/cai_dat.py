"""Cài đặt widget — đọc một chỗ, dùng cho cả máy chủ lẫn trình duyệt.

Trả về DICT thuần (không phải Document) để `boot_session` nhồi thẳng vào boot: trình
duyệt không phải gọi thêm một vòng mạng chỉ để biết có được ghi sổ hay không.
"""

import frappe

MAC_DINH = {
    "show_widget": 1,
    "widget_roles": "",
    "project": "",
    "auto_report": 1,
    "telegram_first_seen": 1,
    "throttle_minutes": 10,
    "lap_lai_canh_bao": 3,
    "collect_usage": 1,
    "usage_sample_pct": 100,
    "max_events_per_minute": 120,
    "retention_days": 90,
    "redact_keys": "password,pwd,token,secret,api_key,key,pin,otp,csrf",
    "bridge_error_log": 1,
    "digest_hour": 17,
}


def cai_dat() -> dict:
    """Cài đặt hiện hành. Site chưa migrate / chưa ai lưu → mặc định, KHÔNG ném lỗi.

    Đọc THẲNG `tabSingles` chứ không qua `get_single_value`/`doc.get`: với Single, cả hai
    trả **0** cho ô Check dù người dùng đã tắt HAY chưa ai chạm tới. Hậu quả đo được
    25/08: một lượt `set_single_value` cho MỘT ô làm mọi ô Check còn lại đọc thành "đã
    tắt", và cầu Error Log ngừng chạy trong im lặng — đúng lớp lỗi mà sổ này sinh ra để
    bắt. Ở đây: khoá nào CÓ DÒNG trong `tabSingles` mới tính là người ta đã khai.
    """
    ra = dict(MAC_DINH)
    try:
        rows = frappe.db.sql("""SELECT field, value FROM `tabSingles`
                                 WHERE doctype = 'Feedback Widget Settings'""", as_dict=True)
    except Exception:
        return ra
    for r in rows:
        if r.field not in MAC_DINH:
            continue
        v = r.value
        if v is None or v == "":
            continue
        mac = MAC_DINH[r.field]
        ra[r.field] = int(v) if isinstance(mac, int) and str(v).lstrip("-").isdigit() else v
    return ra


def _duoc_hien_nut(ct: dict, user: str) -> int:
    if not int(ct.get("show_widget") or 0):
        return 0
    vai = [v.strip() for v in (ct.get("widget_roles") or "").splitlines() if v.strip()]
    if not vai:
        return 1
    cua_toi = set(frappe.get_roles(user) or [])
    return 1 if cua_toi.intersection(vai) else 0


def payload_cho_trinh_duyet(user: str = None) -> dict:
    """Phần cài đặt trình duyệt cần biết. Không chứa gì bí mật."""
    ct = cai_dat()
    user = user or frappe.session.user
    return {
        "show_widget": _duoc_hien_nut(ct, user),
        "auto_report": int(ct.get("auto_report") or 0),
        "collect_usage": int(ct.get("collect_usage") or 0),
        "usage_sample_pct": int(ct.get("usage_sample_pct") or 0),
        "throttle_minutes": int(ct.get("throttle_minutes") or 0),
        "max_events_per_minute": int(ct.get("max_events_per_minute") or 0),
        "redact_keys": [k.strip() for k in (ct.get("redact_keys") or "").split(",") if k.strip()],
        "project": ct.get("project") or "",
    }


def boot_session(bootinfo):
    """Hook `boot_session` — gắn cài đặt vào boot của desk."""
    try:
        bootinfo["feedback_widget"] = payload_cho_trinh_duyet()
    except Exception:
        # Boot HỎNG là cả desk trắng màn. Một tính năng ghi sổ không được phép làm điều đó.
        frappe.log_error(frappe.get_traceback(), "feedback_widget boot_session")
