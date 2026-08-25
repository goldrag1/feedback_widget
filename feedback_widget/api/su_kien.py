"""Sổ THÔ: mỗi lần mở màn / bấm nút / bị chặn / lỗi là một dòng.

Vì sao tách khỏi `Feedback Comment`: vé là thứ NGƯỜI xử lý (vài chục cái), sự kiện là
thứ MÁY đếm (hàng nghìn). Trộn hai thứ vào một bảng thì hộp thư chết ngập và không ai
đọc nữa — kể cả vé người gõ. Vé trỏ về sổ; sổ không đẻ vé (trừ luật ở `collect`).

Trần và lấy mẫu nằm ở `Feedback Widget Settings`, không phải hằng số trong mã: mỗi site
một mức chịu đựng khác nhau, và người vận hành phải tự vặn được mà không cần deploy.
"""

from __future__ import annotations

import json

import frappe
from frappe.utils import cint, now_datetime

from feedback_widget.cai_dat import cai_dat
from feedback_widget.chu_ky import chu_ky as _tinh_chu_ky
from feedback_widget.chu_ky import dau_hieu as _tinh_dau_hieu

LOAI = ("dung", "chan", "loi")
TRAN_MOI_LUOT = 100          # số sự kiện tối đa trong MỘT lần gửi theo lô
TRAN_CHUOI = {"message": 1000, "screen_id": 200, "screen_name": 200, "action_id": 200,
              "endpoint": 200, "doc_ref": 200, "session_id": 64, "form_factor": 40}


def _cat(v, khoa: str) -> str | None:
    s = str(v or "").strip()
    if not s:
        return None
    return s[:TRAN_CHUOI.get(khoa, 200)]


def _che(obj, khoa_can_che: list[str]):
    """Che giá trị của những khoá nhạy cảm ở MỌI độ sâu, giữ nguyên hình dạng còn lại."""
    if isinstance(obj, dict):
        ra = {}
        for k, v in obj.items():
            if any(x and x in str(k).lower() for x in khoa_can_che):
                ra[k] = "***"
            else:
                ra[k] = _che(v, khoa_can_che)
        return ra
    if isinstance(obj, list):
        return [_che(x, khoa_can_che) for x in obj[:50]]
    if isinstance(obj, str):
        return obj[:2000]
    return obj


@frappe.whitelist(methods=["POST"])
def ghi_lo(events=None, project: str = None):
    """Nhận MỘT LÔ sự kiện từ trình duyệt. Trả {ok, nhan, bo_qua}.

    Cố ý KHÔNG ném lỗi khi một dòng hỏng: gửi sổ là việc phụ, làm hỏng thao tác của
    người dùng vì nó là đánh đổi sai. Dòng hỏng bị bỏ, phần còn lại vẫn vào.
    """
    ct = cai_dat()
    if not cint(ct.get("collect_usage")):
        return {"ok": True, "nhan": 0, "bo_qua": 0, "tat": 1}

    if isinstance(events, str):
        try:
            events = json.loads(events)
        except Exception:
            return {"ok": False, "loi": "events không phải JSON"}
    if not isinstance(events, list):
        return {"ok": False, "loi": "events phải là danh sách"}

    khoa_che = [k.strip().lower() for k in (ct.get("redact_keys") or "").split(",") if k.strip()]
    du_an = (project or ct.get("project") or frappe.local.site or "default")[:80]
    nguoi = frappe.session.user
    vai = ", ".join(sorted(r for r in (frappe.get_roles(nguoi) or []) if r not in ("All", "Guest")))[:500]

    nhan = bo_qua = 0
    for e in events[:TRAN_MOI_LUOT]:
        if not isinstance(e, dict):
            bo_qua += 1
            continue
        loai = str(e.get("kind") or "dung").strip().lower()
        if loai not in LOAI:
            bo_qua += 1
            continue
        msg = str(e.get("message") or "")
        try:
            ctx = _che(e.get("context") or {}, khoa_che)
            frappe.get_doc({
                "doctype": "Feedback Event",
                "project": du_an,
                "kind": loai,
                # Thời điểm do MÁY CHỦ đóng dấu: đồng hồ máy xưởng lệch vài phút là
                # chuyện thường, và một sổ mà thứ tự sai thì không truy được chuỗi thao tác.
                "ts": now_datetime(),
                "user": nguoi,
                "user_roles": vai,
                "screen_id": _cat(e.get("screen_id"), "screen_id"),
                "screen_name": _cat(e.get("screen_name"), "screen_name"),
                "action_id": _cat(e.get("action_id"), "action_id"),
                "endpoint": _cat(e.get("endpoint"), "endpoint"),
                "outcome": (e.get("outcome") if e.get("outcome") in ("ok", "chan", "loi", "huy") else None),
                "signature": _tinh_chu_ky(msg, str(e.get("endpoint") or ""), loai) if msg else None,
                "marker": _tinh_dau_hieu(msg) or None,
                "http_status": cint(e.get("http_status")),
                "duration_ms": cint(e.get("duration_ms")),
                "message": _cat(msg, "message"),
                "doc_ref": _cat(e.get("doc_ref"), "doc_ref"),
                "session_id": _cat(e.get("session_id"), "session_id"),
                "form_factor": _cat(e.get("form_factor"), "form_factor"),
                "context": json.dumps(ctx, ensure_ascii=False)[:20000] if ctx else None,
            }).insert(ignore_permissions=True)
            nhan += 1
        except Exception:
            bo_qua += 1
    frappe.db.commit()
    return {"ok": True, "nhan": nhan, "bo_qua": bo_qua}


@frappe.whitelist(methods=["POST"])
def kiem_ke_giao_dien(items=None, project: str = None):
    """Widget kiểm kê NÚT ĐANG HIỆN trên màn người dùng vừa mở.

    Vì sao không đọc mã nguồn để dựng danh mục: bộ đọc mã phải đoán nút nào thuộc màn
    nào (component dùng chung, nút dựng trong vòng lặp, nhãn ghép chuỗi) — sai lệch âm
    thầm và không ai kiểm được. Kiểm kê từ DOM là thứ NGƯỜI DÙNG thật sự nhìn thấy.

    Giới hạn đã biết, ghi ra để không ai hiểu nhầm số 0: nút chỉ vào danh mục khi có
    người MỞ màn ấy. Màn chưa ai mở thì không có nút nào — nhưng chính màn đó đã nằm
    trong danh mục màn (do app chủ khai) và sẽ hiện là "CHƯA AI DÙNG".

    Ai gọi cũng được (người dùng thường), nên chặn bằng TRẦN và cắt chuỗi chứ không bằng
    vai trò: đây là dữ liệu mô tả giao diện, không đọc/ghi nghiệp vụ.
    """
    ct = cai_dat()
    if not cint(ct.get("collect_usage")):
        return {"ok": True, "tat": 1}
    if isinstance(items, str):
        items = json.loads(items)
    if not isinstance(items, list):
        return {"ok": False, "loi": "items phải là danh sách"}
    du_an = (project or ct.get("project") or frappe.local.site or "default")[:80]

    them = 0
    for it in items[:60]:
        if not isinstance(it, dict):
            continue
        item_id = str(it.get("item_id") or "").strip()[:200]
        if not item_id:
            continue
        ten = f"{du_an}::action::{item_id}"[:140]
        if frappe.db.exists("Feedback Manifest Item", ten):
            continue
        try:
            d = frappe.get_doc({
                "doctype": "Feedback Manifest Item", "project": du_an, "kind": "action",
                "item_id": item_id, "item_name": str(it.get("item_name") or "")[:200],
                "screen_id": str(it.get("screen_id") or "")[:200],
                "section_hint": str(it.get("section") or "")[:200],
                "nguon": "runtime", "con_dung": 1,
            })
            d.flags.name = ten
            d.insert(ignore_permissions=True)
            them += 1
        except Exception:
            continue
    if them:
        frappe.db.commit()
    return {"ok": True, "them": them}


@frappe.whitelist(methods=["POST"])
def khai_danh_muc(items=None, project: str = None, nguon: str = ""):
    """App chủ khai DANH MỤC màn/nút của nó.

    Đây là điều kiện để trả lời "cái gì KHÔNG ai dùng": sổ chỉ thấy thứ ĐƯỢC bấm, nên
    không có danh mục thì nút chết và màn không ai vào là vô hình. Gọi lúc `after_migrate`
    của app chủ, hoặc bằng tay khi đổi giao diện.
    """
    frappe.only_for(("System Manager", "Administrator"))
    if isinstance(items, str):
        items = json.loads(items)
    if not isinstance(items, list):
        return {"ok": False, "loi": "items phải là danh sách"}
    du_an = (project or cai_dat().get("project") or frappe.local.site or "default")[:80]

    con = set()
    for it in items:
        if not isinstance(it, dict):
            continue
        kind = str(it.get("kind") or "").strip()
        item_id = str(it.get("item_id") or "").strip()
        if kind not in ("screen", "action") or not item_id:
            continue
        ten = f"{du_an}::{kind}::{item_id}"[:140]
        con.add(ten)
        gia_tri = {
            "project": du_an, "kind": kind, "item_id": item_id[:200],
            "item_name": str(it.get("item_name") or "")[:200],
            "screen_id": str(it.get("screen_id") or "")[:200],
            "section_hint": str(it.get("section") or "")[:200],
            "nguon": (nguon or "")[:200], "con_dung": 1,
        }
        if frappe.db.exists("Feedback Manifest Item", ten):
            frappe.db.set_value("Feedback Manifest Item", ten, gia_tri, update_modified=False)
        else:
            d = frappe.get_doc({"doctype": "Feedback Manifest Item", **gia_tri})
            d.flags.name = ten
            d.insert(ignore_permissions=True)

    # Mục cũ KHÔNG còn trong mã: đánh dấu thay vì xoá — lịch sử dùng của nó vẫn có ý
    # nghĩa ("màn này bị gỡ tháng trước, trước đó 12 người/ngày").
    cu = frappe.get_all("Feedback Manifest Item",
                        filters={"project": du_an, "con_dung": 1}, pluck="name")
    mat = [x for x in cu if x not in con]
    for x in mat:
        frappe.db.set_value("Feedback Manifest Item", x, "con_dung", 0, update_modified=False)
    frappe.db.commit()
    return {"ok": True, "khai": len(con), "khong_con_trong_ma": len(mat)}
