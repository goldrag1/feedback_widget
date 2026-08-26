"""Cài đặt widget — MỘT bảng duy nhất (`Feedback Settings`), đọc một chỗ.

Bản 25/08 từng dựng thêm `Feedback Widget Settings` song song với bảng đã có từ 24/08:
hai bảng cho một việc, và người vận hành sẽ sửa nhầm bảng không ai đọc. Gộp về bảng cũ
(tên ngắn hơn, đã có phạm vi vai trò dạng bảng con), phần đo đạc thành một mục trong đó.

Đọc THẲNG `tabSingles` chứ không qua `get_single_value`/`doc.get`: với Single, cả hai trả
**0** cho ô Check dù người dùng đã tắt HAY chưa ai chạm tới. Đo được 25/08: một lượt
`set_single_value` cho MỘT ô làm mọi ô Check còn lại đọc thành "đã tắt", và cầu Error Log
ngừng chạy trong im lặng — đúng lớp lỗi mà sổ này sinh ra để bắt.
"""

import frappe

DOCTYPE = "Feedback Settings"

MAC_DINH = {
    # hiển thị (bản 24/08)
    "enabled": 1,
    "enable_on_desk": 1,
    "enable_on_portal": 1,
    "allow_all_roles": 1,
    "project_name": "",
    "primary_color": "#1f3a5f",
    "fab_color": "#047857",
    # khung góp ý (bản 26/08) — đo trên prod 164 vé do người bấm: ghim 139 (84%),
    # ảnh 8 (4%), phân loại 3 (2%), mức độ 1 (0,6%). Mặc định suy TỪ SỐ ĐO đó.
    "hien_tag": 0,
    "cho_dinh_anh": 1,
    # thu thập tự động (bản 25/08)
    "auto_report": 1,
    "telegram_first_seen": 1,
    "bridge_error_log": 1,
    "throttle_minutes": 10,
    "lap_lai_canh_bao": 3,
    "collect_usage": 1,
    "usage_sample_pct": 100,
    "max_events_per_minute": 120,
    "retention_days": 90,
    "digest_hour": 17,
    "redact_keys": "password,pwd,token,secret,api_key,key,pin,otp,csrf",
}


def cai_dat() -> dict:
    """Cài đặt hiện hành; site chưa migrate / chưa ai lưu → mặc định, KHÔNG ném lỗi."""
    ra = dict(MAC_DINH)
    try:
        rows = frappe.db.sql(
            """SELECT field, value FROM `tabSingles` WHERE doctype = %s""", DOCTYPE, as_dict=True)
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


def vai_duoc_thay_nut(user: str = None) -> int:
    """Người này có được THẤY nút 💬 không (phạm vi vai trò của bản 24/08)."""
    ct = cai_dat()
    if not (int(ct.get("enabled") or 0) and int(ct.get("enable_on_desk") or 0)):
        return 0
    if int(ct.get("allow_all_roles") or 0):
        return 1
    try:
        doc = frappe.get_cached_doc(DOCTYPE)
        cho_phep = {r.role for r in (doc.get("allowed_roles") or [])}
    except Exception:
        return 1
    if not cho_phep:
        return 1
    cua_toi = set(frappe.get_roles(user or frappe.session.user) or [])
    return 1 if cua_toi.intersection(cho_phep) else 0


def payload_cho_trinh_duyet(user: str = None) -> dict:
    """Phần cài đặt trình duyệt cần biết. Không chứa gì bí mật.

    `show_widget` và `auto_report`/`collect_usage` ĐỘC LẬP với nhau: ẩn nút mà vẫn thu là
    một chế độ có chủ đích, không phải hệ quả phụ.
    """
    ct = cai_dat()
    return {
        "show_widget": vai_duoc_thay_nut(user),
        "auto_report": int(ct.get("auto_report") or 0),
        "collect_usage": int(ct.get("collect_usage") or 0),
        "usage_sample_pct": int(ct.get("usage_sample_pct") or 0),
        "throttle_minutes": int(ct.get("throttle_minutes") or 0),
        "lap_lai_canh_bao": int(ct.get("lap_lai_canh_bao") or 0),
        "max_events_per_minute": int(ct.get("max_events_per_minute") or 0),
        "redact_keys": [k.strip() for k in (ct.get("redact_keys") or "").split(",") if k.strip()],
        "project": ct.get("project_name") or "",
        "primary_color": ct.get("primary_color") or "#1f3a5f",
        "fab_color": ct.get("fab_color") or "#047857",
        "hien_tag": int(ct.get("hien_tag") or 0),
        "cho_dinh_anh": int(ct.get("cho_dinh_anh") or 0),
    }


def gieo_mac_dinh() -> list:
    """Ghi vào `tabSingles` những khoá CHƯA ai khai, và trả về danh sách đã gieo.

    VÌ SAO CẦN: với Single, `default` khai trong DocType JSON KHÔNG được áp khi thiếu
    dòng — `frappe.get_single()` trả 0/None. Đo trên prod 26/08 sau lượt gộp: màn Cài đặt
    hiện `enable_on_desk = 0`, `enable_on_portal = 0`, `allow_all_roles = 0` trong khi
    `cai_dat()` (thứ hệ THẬT SỰ dùng) trả 1/1/1. Giao diện nói ngược với hành vi, và cú
    Save đầu tiên của người vận hành sẽ GHI CHẾT mấy con số 0 ấy: widget biến mất khỏi
    desk của tất cả mọi người, không một dòng lỗi.

    KHÔNG đè khoá đã khai — kể cả `enabled = 0` mà ai đó cố ý tắt.
    """
    doc = frappe.get_single(DOCTYPE)
    da_khai = {r[0] for r in frappe.db.sql(
        """SELECT field FROM `tabSingles` WHERE doctype = %s""", DOCTYPE)}
    thieu = [k for k in MAC_DINH if k not in da_khai]
    for k in thieu:
        doc.set(k, MAC_DINH[k])
    if thieu:
        doc.flags.ignore_permissions = True
        doc.save()
        frappe.db.commit()
    return thieu
