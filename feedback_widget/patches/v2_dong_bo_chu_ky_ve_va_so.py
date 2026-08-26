"""Tính lại chữ ký cho VÉ và SỔ theo công thức mới (bỏ `kind`/`source` khỏi băm).

VÌ SAO: hai bảng băm kèm hai giá trị khác nhau cho cùng một sự cố, nên chúng KHÔNG BAO GIỜ
nối được với nhau. Đo prod 26/08: 33 vé, 16 dòng sổ, 0 chữ ký dùng chung ⇒ mục "Hồi quy"
(vé đã đóng mà lỗi quay lại) cấu trúc là luôn rỗng, và vòng "đóng vé xong đo lại chữ ký"
so hai thứ khác nhau.

Bản vá mã (chu_ky.py) mà KHÔNG tính lại dữ liệu cũ thì tệ hơn: vé đang mở giữ khoá cũ, lượt
tái diễn tính ra khoá mới ⇒ không gộp được vào vé cũ ⇒ đẻ vé trùng. Hai thứ phải đi cùng.

Chạy lại vô hại: khoá là hàm thuần của (câu, endpoint) nên lượt sau tính ra đúng giá trị ấy.
"""

import json

import frappe

from feedback_widget.chu_ky import chu_ky


def _endpoint_cua_ve(context: str) -> str:
    """Endpoint mà `collect` đã dùng khi băm — nằm trong context.app.endpoint."""
    try:
        return str(((json.loads(context or "{}").get("app") or {}).get("endpoint")) or "")[:200]
    except Exception:
        return ""


def execute(chay_thu: int = 0):
    doi_ve = doi_so = 0
    for r in frappe.db.sql("""SELECT name, message, context, signature FROM `tabFeedback Comment`
                              WHERE source='auto' AND IFNULL(signature,'') <> ''""", as_dict=True):
        moi = chu_ky(r.message or "", _endpoint_cua_ve(r.context))
        if moi == r.signature:
            continue
        doi_ve += 1
        if not chay_thu:
            frappe.db.set_value("Feedback Comment", r.name, "signature", moi,
                                update_modified=False)

    for r in frappe.db.sql("""SELECT name, message, endpoint, signature FROM `tabFeedback Event`
                              WHERE IFNULL(signature,'') <> ''""", as_dict=True):
        moi = chu_ky(r.message or "", r.endpoint or "")
        if moi == r.signature:
            continue
        doi_so += 1
        if not chay_thu:
            frappe.db.set_value("Feedback Event", r.name, "signature", moi,
                                update_modified=False)

    if not chay_thu:
        frappe.db.commit()
    print(f"[dong_bo_chu_ky] vé đổi {doi_ve} · sổ đổi {doi_so}"
          f"{' (XEM TRƯỚC, chưa ghi)' if chay_thu else ''}")
    return {"ve": doi_ve, "so": doi_so}
