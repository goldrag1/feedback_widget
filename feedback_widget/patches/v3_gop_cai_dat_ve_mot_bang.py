"""Gộp `Feedback Widget Settings` (bản 25/08) vào `Feedback Settings` — MỘT bảng cài đặt.

Hai bảng cho một việc thì người vận hành sẽ sửa nhầm bảng không ai đọc, rồi kết luận
"tắt không ăn". Bảng cũ sống đúng một ngày; gộp thì phải MANG THEO thứ người ta đã khai,
nếu không một lượt "gộp cho gọn" âm thầm bật lại những ô họ đã tắt.

Đo trên prod trước khi viết (5 site có app): ducan + thanhcong chỉ có bảng CŨ (21 dòng,
toàn mặc định) và `v1` đã nằm trong Patch Log của cả hai — nên phần chuyển giá trị PHẢI
là patch mới, sửa v1 là sửa vào chỗ không bao giờ chạy lại. tamdinh có bảng MỚI với
`enabled = 0` (ai đó cố ý tắt) và KHÔNG có bảng cũ ⇒ patch này không ghi gì ở đó.

Đọc/ghi THẲNG `tabSingles`, không qua `frappe.get_single`: bảng cũ có thể đã bị
`remove_orphan_doctypes` của chính lượt migrate này xoá mất DocType, mà dữ liệu thì vẫn
nằm nguyên trong `tabSingles` — bám vào DocType là phần chuyển giá trị lặng lẽ thành
no-op đúng lúc cần nó nhất.
"""

import frappe

CU = "Feedback Widget Settings"
MOI = "Feedback Settings"

# Trường đổi tên giữa hai bảng.
DOI_TEN = {"show_widget": "enabled", "project": "project_name"}

# Siêu dữ liệu của Single, không phải cài đặt.
BO_QUA = {"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx"}


def execute():
    cu = {r[0]: r[1] for r in frappe.db.sql(
        """SELECT field, value FROM `tabSingles` WHERE doctype = %s""", CU)}
    if not cu:
        return

    da_khai = {r[0] for r in frappe.db.sql(
        """SELECT field FROM `tabSingles` WHERE doctype = %s""", MOI)}

    for field, value in cu.items():
        if field in BO_QUA:
            continue
        moi_ten = DOI_TEN.get(field, field)
        # `widget_roles` (danh sách vai dạng chuỗi) không có chỗ tương ứng dạng chuỗi ở
        # bảng mới — nó thành bảng con `allowed_roles`, xử riêng bên dưới.
        if moi_ten == "widget_roles" or moi_ten in da_khai or value in (None, ""):
            continue
        frappe.db.sql("""INSERT INTO `tabSingles` (doctype, field, value) VALUES (%s, %s, %s)""",
                      (MOI, moi_ten, value))
        da_khai.add(moi_ten)

    _chuyen_pham_vi_vai(cu.get("widget_roles") or "", da_khai)

    # Bảng cũ: xoá HẲN cả dữ liệu lẫn DocType. Để lại một bảng cài đặt không ai đọc là
    # mời người vận hành sửa nhầm chỗ.
    frappe.db.delete("Singles", {"doctype": CU})
    if frappe.db.exists("DocType", CU):
        frappe.delete_doc("DocType", CU, force=True, ignore_permissions=True)
    frappe.db.commit()


def _chuyen_pham_vi_vai(widget_roles: str, da_khai: set):
    """Bảng cũ giới hạn theo vai bằng MỘT ô nhiều dòng; bảng mới dùng `allow_all_roles`
    + bảng con. Bỏ qua bước này là NỚI quyền xem cho tất cả mà không ai thấy — nên khi
    có khai vai thì phải tắt `allow_all_roles` rồi mới chép sang bảng con."""
    vai = [v.strip() for v in widget_roles.splitlines() if v.strip()]
    if not vai:
        return
    if "allow_all_roles" not in da_khai:
        frappe.db.sql("""INSERT INTO `tabSingles` (doctype, field, value) VALUES (%s, 'allow_all_roles', '0')""",
                      (MOI,))
    else:
        frappe.db.sql("""UPDATE `tabSingles` SET value='0' WHERE doctype=%s AND field='allow_all_roles'""",
                      (MOI,))
    doc = frappe.get_single(MOI)
    dang_co = {r.role for r in (doc.get("allowed_roles") or [])}
    for r in vai:
        if r not in dang_co and frappe.db.exists("Role", r):
            doc.append("allowed_roles", {"role": r})
    doc.flags.ignore_permissions = True
    doc.save()
