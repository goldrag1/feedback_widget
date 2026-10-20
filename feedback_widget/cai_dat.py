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
    "giay_tu_dong_dong": 20,
    # thu thập tự động (bản 25/08)
    "auto_report": 1,
    # Có trong DocType từ 27/08 nhưng THIẾU ở đây, nên `gieo_mac_dinh` bản cũ (gọi
    # `doc.save()`) ghi chết 0 vào nó lần đầu có khoá mới cần gieo — đo trên mirror 20/10:
    # thêm khoá kịch bản màn là "Tự báo vé đã xử lý" tắt ngay, không một dòng lỗi.
    "tu_dong_bao_ve": 1,
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
    # Những câu CHẶN đã biết là ĐÚNG LUẬT: vẫn ghi vào sổ sự kiện (để còn đếm được ai
    # đang vấp), nhưng KHÔNG đẻ vé và không bắn Telegram. Mỗi dòng một mẫu, so khớp
    # không phân biệt hoa thường trên nội dung thông điệp.
    "khong_de_ve": "",
    # Kịch bản màn (bản 20/10/2026, spec docs/specs/2026-10-20-kich-ban-man-design.md §4.10).
    # Công tắc tổng TẮT mặc định: app dùng chung bench với site khác, bật từng site một.
    "kb_bat": 0,
    "diem_buoc": 10,
    "diem_chang": 30,
    "diem_ky_duy_tri": 5,
    "diem_nhiem_vu": 30,
    "diem_mo_duong": 20,
    "gio_mo_duong": 48,
    "diem_co_ich": 20,
    "diem_cai_tien": 50,
    "diem_cam_nhan": 5,
    "nguong_thanh_thao": 100,
    "nguong_key_user": 300,
    "nguong_dai_su": 700,
    "tuan_chuyen_can": 4,
    "phien_da_quen": 3,
    "gio_lam_tu": "08:00",
    "gio_lam_den": "18:00",
    "ngay_lam_viec": "1,2,3,4,5,6",
    "nhac_toi_da_ngay": 3,
    "nhac_toi_da_kb_ngay": 1,
    "nhac_dung_sau_bo_qua": 3,
    "nhac_chua_mo_gio": 24,
    "nhac_cham_bien": 25,
    "nhac_sap_het_gio": 24,
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


def vai_duoc_thay_nut(user: str = None, noi: str = "desk") -> int:
    """Người này có được THẤY nút 💬 không (phạm vi vai trò của bản 24/08).

    `noi` là NƠI hỏi: `"desk"` hay `"portal"`. Trước 20/09/2026 hàm chỉ đọc
    `enable_on_desk`, nên ô `enable_on_portal` trong Cài đặt **không có ai đọc** — một
    công tắc tồn tại mà không điều khiển gì, và người vận hành tắt nó đi thì không có gì
    đổi. Mặc định giữ `"desk"` để mọi lời gọi cũ chạy y như trước.
    """
    ct = cai_dat()
    khoa_noi = "enable_on_portal" if noi == "portal" else "enable_on_desk"
    if not (int(ct.get("enabled") or 0) and int(ct.get(khoa_noi) or 0)):
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


def payload_cho_trinh_duyet(user: str = None, noi: str = "desk") -> dict:
    """Phần cài đặt trình duyệt cần biết. Không chứa gì bí mật.

    `show_widget` và `auto_report`/`collect_usage` ĐỘC LẬP với nhau: ẩn nút mà vẫn thu là
    một chế độ có chủ đích, không phải hệ quả phụ.
    """
    ct = cai_dat()
    return {
        "show_widget": vai_duoc_thay_nut(user, noi),
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
        "giay_tu_dong_dong": int(ct.get("giay_tu_dong_dong") or 0),
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
    # GHI THẲNG từng dòng còn thiếu, KHÔNG `doc.save()`: lưu cả Single là ghi luôn 0 cho
    # mọi ô Check/Int chưa ai chạm mà không nằm trong MAC_DINH (đã tắt mất `tu_dong_bao_ve`
    # trên mirror 20/10). `tabSingles` không có khoá unique ⇒ chỉ INSERT khoá chưa có.
    da_khai = {r[0] for r in frappe.db.sql(
        """SELECT field FROM `tabSingles` WHERE doctype = %s""", DOCTYPE)}
    co_o = {f.fieldname for f in frappe.get_meta(DOCTYPE).fields}
    thieu = [k for k in MAC_DINH if k not in da_khai and k in co_o]
    for k in thieu:
        frappe.db.sql("""INSERT INTO `tabSingles` (doctype, field, value) VALUES (%s, %s, %s)""",
                      (DOCTYPE, k, MAC_DINH[k]))
    if thieu:
        frappe.clear_document_cache(DOCTYPE, DOCTYPE)
        frappe.db.commit()
    return thieu


def khong_xep_hang() -> set:
    """Người KHÔNG hiện trên bảng vàng (bảng con — không nằm trong `tabSingles` nên
    `cai_dat()` không thấy). Chưa ai khai thì mặc định: Administrator."""
    try:
        ds = frappe.db.sql(
            """SELECT user FROM `tabFeedback Notice User`
                WHERE parenttype = %s AND parentfield = 'khong_xep_hang'""", DOCTYPE)
    except Exception:
        ds = ()
    return {r[0] for r in ds if r[0]} | {"Administrator"}
