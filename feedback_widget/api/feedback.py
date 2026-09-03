"""Whitelisted collect endpoint for the feedback widget.

Dual-write contract:
  1. Insert a Feedback Comment DocType row (canonical, queryable, permissioned).
  2. Append the raw payload as a JSONL line at
     sites/<site>/private/feedback/<project>.jsonl
     so AI coding agents can grep/jq/cat the inbox without DB access.

Validation + size limits live in the shared feedback_handler module
(~/.claude/skills/feedback-widget/feedback_handler.py). Re-using that module
keeps the validation rules identical across HTML mockups, SPA, and Frappe.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime, convert_utc_to_system_timezone

# Make the shared validator importable. The skill lives outside the bench so
# both standalone HTML demos and this app share the same rules.
SHARED_PATH = pathlib.Path.home() / ".claude" / "skills" / "feedback-widget"
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

try:
    from feedback_handler import validate_payload, append_jsonl, FeedbackError, default_telegram_summary  # type: ignore
except Exception as e:  # pragma: no cover — dev-time guard
    raise ImportError(
        f"feedback_widget requires shared validator at {SHARED_PATH}/feedback_handler.py "
        f"(install or symlink the feedback-widget skill from ~/.claude/skills/). Original: {e}"
    )

# Local Telegram notifier (stdlib multipart for sendPhoto / sendMediaGroup)
from feedback_widget import notifier  # type: ignore
from feedback_widget.cai_dat import cai_dat
from feedback_widget.chu_ky import chu_ky as _tinh_chu_ky
from feedback_widget.chu_ky import dau_hieu as _tinh_dau_hieu


def _gop_danh_sach(cu: str, moi: str, tran: int = 500) -> str:
    """Gộp một tên vào danh sách phân tách bằng '; ', không trùng, không tràn cột.

    Vì sao cần: câu hỏi hữu ích nhất của một vé máy là "có mấy NGƯỜI dính, hay chỉ một
    người bấm nhầm" — đếm lần không trả lời được, danh sách người thì có.
    """
    ds = [x.strip() for x in (cu or "").split(";") if x.strip()]
    moi = (moi or "").strip()
    if moi and moi not in ds:
        ds.append(moi)
    ra = "; ".join(ds)
    return ra[:tran]


def _normalise_payload(form_dict) -> dict:
    """Frappe form_dict can carry the JSON body in several shapes depending on
    how the client posted (Content-Type, fetch vs frappe.call, etc). Tolerate
    them all so the widget JS does not need to know."""
    if isinstance(form_dict, dict) and "data" in form_dict and isinstance(form_dict["data"], str):
        try:
            return json.loads(form_dict["data"])
        except Exception:
            pass
    if isinstance(form_dict, dict):
        # Strip Frappe's request-flavoured keys before validation
        return {k: v for k, v in form_dict.items() if k not in ("cmd", "_")}
    return dict(form_dict or {})


def _jsonl_path(project: str) -> pathlib.Path:
    safe = "".join(c for c in project if c.isalnum() or c in "_.-")[:80] or "default"
    return pathlib.Path(frappe.get_site_path("private", "feedback", f"{safe}.jsonl"))


def _nguoi_thay_mat(payload) -> str | None:
    """Danh tính người THẬT khi máy chủ ghi vé HỘ họ (cầu Error Log · khai thác lịch sử).

    VÌ SAO: việc nền chạy dưới Administrator, nên `frappe.session.user` ở đây là
    Administrator chứ không phải người vấp lỗi. Đo prod 03/09/2026: vé máy sinh từ
    Error Log ghi `submitter_user = Administrator` trong khi chủ dòng log là người thật
    (FB-2026-01571/01572 ← bien.quandoc@ducan.local), tức mọi câu "ai đang bị chặn" gọi
    nhầm tên người — và không có dấu hiệu nào để người đọc nghi ngờ.

    Chỉ nhận khai hộ khi lượt gọi KHÔNG phải HTTP (việc nền, `bench execute`) hoặc người
    gọi là System Manager. Trình duyệt của người dùng thường gửi lên thì bị BỎ QUA, nên
    ô này không mở đường giả mạo danh tính — quy tắc "không tin dữ liệu từ máy khách"
    của `collect` giữ nguyên.
    """
    nguoi = str((payload or {}).get("nguoi_thay_mat") or "").strip()
    if not nguoi:
        return None
    if getattr(frappe.local, "request", None) is not None:
        if "System Manager" not in (frappe.get_roles() or []):
            return None
    # Người đã bị xoá khỏi bảng User: đừng ghi tên ma vào cột Link — vé sẽ không mở được.
    if not frappe.db.exists("User", nguoi):
        return None
    return nguoi


def _la_chan_da_biet(thong_diep: str) -> bool:
    """Thông điệp này có nằm trong danh sách "chặn đúng luật, đừng đẻ vé" không.

    Khai ở `Feedback Settings.khong_de_ve`, mỗi dòng một mẫu — DỮ LIỆU, để người vận hành
    tắt tiếng một luật mà không phải sửa mã rồi deploy ba bench.
    """
    from feedback_widget.cai_dat import cai_dat

    mau = [d.strip().lower() for d in (cai_dat().get("khong_de_ve") or "").splitlines() if d.strip()]
    if not mau:
        return False
    van = frappe.utils.strip_html(str(thong_diep or "")).lower()
    return any(m in van for m in mau)


@frappe.whitelist(allow_guest=False, methods=["POST"])
def collect(**kwargs):
    """Accept a feedback payload from the widget. Returns {ok, name, saved_as}.

    Authenticated users only — guests would let the widget be spammed against
    any login URL. For public demos, deploy a separate stdlib collector with
    rate-limiting + Cloudflare Turnstile in front.
    """
    payload = _normalise_payload(kwargs)
    try:
        entry = validate_payload(payload)
    except FeedbackError as e:
        frappe.local.response["http_status_code"] = 400
        return {"ok": False, "error": str(e)}

    # Chặn ĐÚNG LUẬT mà đã biết trước thì đừng đẻ vé: nó đẩy vé thật xuống dưới và bắn
    # Telegram lúc nửa đêm cho thứ không ai định sửa. Sự kiện vẫn vào sổ qua
    # `su_kien.ghi_lo`, nên vẫn đếm được bao nhiêu người vấp và vấp ở màn nào.
    # Đo prod HTS 27/08: "Không đủ quyền cho Item Price" — 17/27 người mở được mã hàng mà
    # không được xem giá, và chủ đầu tư CỐ Ý giữ nguyên quyền đó.
    if _la_chan_da_biet(entry.get("message")):
        return {"ok": True, "bo_qua": "chan_da_biet"}

    # 1) Insert DocType row — flatten the rich blobs into Code (JSON) cells
    # ─── Pointed elements — widget may send either:
    #   - `pointed_elements`: array of element objects (v1.4+ multi-pin)
    #   - `pointed_element`: single object (v1.3 and earlier)
    # Normalise to a list for storage; keep first one in the Data summary cols
    # so list views remain useful.
    pe_list_raw = entry.get("pointed_elements")
    if isinstance(pe_list_raw, list):
        pe_list = [p for p in pe_list_raw if isinstance(p, dict)]
    else:
        single = entry.get("pointed_element")
        pe_list = [single] if isinstance(single, dict) and single else []
    pe = pe_list[0] if pe_list else {}
    ctx = entry.get("context") or {}
    tags = entry.get("tags") or {}

    # ─── Server-authoritative identity ─────────────────────────────────────
    # Never trust client-supplied user/role data — re-derive from session.
    # The widget DOES collect these in ctx.app for HTML-mockup parity, but
    # for Frappe we overwrite them so a malicious client cannot impersonate.
    # `nguoi_thay_mat` chỉ đổi DANH TÍNH ghi vào vé; quyền vẫn chạy dưới phiên thật
    # (Administrator ở đường việc nền), nên không có ca "vé mất vì người ấy thiếu quyền".
    session_user = _nguoi_thay_mat(payload) or frappe.session.user
    is_authed = session_user and session_user != "Guest"
    user_full_name = None
    user_roles_csv = None
    if is_authed:
        user_full_name = frappe.db.get_value("User", session_user, "full_name") or session_user
        # frappe.get_roles() returns roles for current user including All/Guest
        roles = [r for r in (frappe.get_roles(session_user) or []) if r not in ("All", "Guest")]
        user_roles_csv = ", ".join(sorted(roles))[:500]
        # Stamp into ctx.app too so the JSONL mirror carries server-trusted identity
        if not isinstance(ctx, dict):
            ctx = {}
        app = ctx.get("app") if isinstance(ctx.get("app"), dict) else {}
        app["user"] = session_user
        app["user_full_name"] = user_full_name
        app["roles"] = roles[:20]  # cap to keep JSONL line size sane
        ctx["app"] = app
        entry["context"] = ctx  # propagate to raw_payload + jsonl below
    # ────────────────────────────────────────────────────────────────────────

    # Widget gửi `ts` dạng ISO 8601 kết thúc bằng Z (UTC). MySQL `datetime` từ chối cả hậu
    # tố múi giờ lẫn datetime tz-aware, nên phải bỏ tzinfo — NHƯNG bỏ suông là GIỮ NGUYÊN
    # GIỜ UTC, tức lệch đúng bằng offset của site (VN: 7 tiếng) so với `creation`.
    #
    # Đo trên prod 27/08/2026: **212/212** vé lệch 420 phút, trong khi `Feedback Event.ts`
    # thì khớp. Mọi báo cáo đọc `ts` (mục "hồi quy" so `Event.ts` với mốc đóng vé, biểu đồ
    # theo giờ) đọc lệch cả buổi làm việc — và không có dấu hiệu nào để ai đó nghi ngờ.
    # Đổi sang giờ hệ thống TRƯỚC khi bỏ tzinfo.
    ts_iso = entry.get("ts") or ""
    try:
        ts_dt = get_datetime(ts_iso) if ts_iso else now_datetime()
        if ts_dt and getattr(ts_dt, "tzinfo", None) is not None:
            ts_dt = convert_utc_to_system_timezone(ts_dt).replace(tzinfo=None)
    except Exception:
        ts_dt = now_datetime()

    # ─── Attachments — widget pre-uploads each image to /api/method/upload_file
    # then includes [{file_url, file_name, file_size, mime}] here. The actual
    # binaries are already living as Frappe File records; we just persist refs.
    attachments_in = payload.get("attachments")
    attachments_clean: list = []
    if isinstance(attachments_in, list):
        for a in attachments_in[:10]:  # cap at 10 (Telegram media group limit)
            if not isinstance(a, dict):
                continue
            url = (a.get("file_url") or "").strip()
            if not url or not url.startswith("/"):
                continue
            attachments_clean.append({
                "file_url":  url[:500],
                "file_name": (a.get("file_name") or "")[:200],
                "file_size": int(a.get("file_size") or 0),
                "mime":      (a.get("mime") or "")[:100],
            })
    entry["attachments"] = attachments_clean  # propagate to raw_payload + jsonl

    # ─── v1.6 — VÉ MÁY (source="auto") ────────────────────────────────────
    # Máy tự ghi khi máy chủ TỪ CHỐI hoặc màn hình LỖI. Hai luật ở đây, và cả hai đều
    # là điều kiện để tính năng dùng được thật:
    #   1. GOM theo chữ ký — nếu không, một lỗi lặp 40 lần đẻ 40 vé và hộp thư của
    #      người xử lý chết ngập, đúng cách để họ bỏ đọc luôn (kể cả vé người gõ).
    #   2. Vé đã ĐÓNG mà chữ ký tái xuất thì mở vé MỚI, không cộng dồn vào vé cũ:
    #      đó là hồi quy, phải nhìn thấy là một sự kiện riêng.
    source = str(payload.get("source") or "user").strip().lower()
    if source not in ("user", "auto"):
        source = "user"
    marker = _tinh_dau_hieu(entry["message"])
    endpoint_ctx = ""
    try:
        endpoint_ctx = str(((ctx.get("app") or {}).get("endpoint")) or "")[:200]
    except Exception:
        endpoint_ctx = ""
    signature = _tinh_chu_ky(entry["message"], endpoint_ctx, source) if source == "auto" else None

    if source == "auto" and signature:
        cu = frappe.db.get_value(
            "Feedback Comment",
            {"project": entry["project"], "signature": signature,
             "status": ["in", ("New", "Triaged", "In Progress")]},
            ["name", "occurrences", "affected_users", "affected_screens"], as_dict=True)
        if cu:
            nguoi = _gop_danh_sach(cu.affected_users, user_full_name or session_user)
            man = _gop_danh_sach(cu.affected_screens, entry.get("screen_name") or entry["screen_id"])
            frappe.db.set_value("Feedback Comment", cu.name, {
                "occurrences": (cu.occurrences or 1) + 1,
                "last_seen": ts_dt,
                "affected_users": nguoi,
                "affected_screens": man,
            }, update_modified=False)
            frappe.db.commit()
            # KHÔNG đẩy Telegram lại: tin thứ hai trở đi không mang thông tin mới, chỉ
            # dạy người ta tắt thông báo.
            return {"ok": True, "name": cu.name, "merged": True,
                    "occurrences": (cu.occurrences or 1) + 1, "saved_as": ""}

    doc = frappe.get_doc({
        "doctype": "Feedback Comment",
        "project": entry["project"],
        "submitter": entry.get("submitter") or user_full_name or "(anon)",
        "submitter_user": session_user if is_authed else None,
        "user_full_name": user_full_name,
        "user_roles": user_roles_csv,
        "ts": ts_dt,
        "status": "New",
        "screen_id": entry["screen_id"],
        "screen_name": entry["screen_name"],
        "message": entry["message"],
        "tag_type": tags.get("type") or None,
        "tag_severity": tags.get("severity") or None,
        "pointed_selector": (pe.get("selector") or "")[:600] or None,
        "pointed_text": (pe.get("text") or "")[:200] or None,
        "pointed_element": json.dumps(pe_list if len(pe_list) > 1 else pe, ensure_ascii=False) if pe_list else None,
        "url": (ctx.get("url") or "")[:500] or None,
        "user_agent": entry.get("user_agent") or None,
        "context": json.dumps(ctx, ensure_ascii=False) if ctx else None,
        "attachments": json.dumps(attachments_clean, ensure_ascii=False) if attachments_clean else None,
        "telegram_pushed": 0,
        "source": source,
        "signature": signature,
        "marker": marker or None,
        "occurrences": 1,
        "last_seen": ts_dt,
        "affected_users": (user_full_name or session_user or "")[:500] or None,
        "affected_screens": (entry.get("screen_name") or entry["screen_id"] or "")[:500] or None,
        "raw_payload": json.dumps(entry, ensure_ascii=False),
    })
    doc.flags.ignore_permissions = False
    doc.insert()

    # 2) Mirror raw payload to JSONL inbox for AI agent consumption
    saved_path = ""
    try:
        jpath = _jsonl_path(entry["project"])
        # Stamp the row name so agents can cross-reference jsonl line ↔ DocType
        mirror = dict(entry)
        mirror["_doc_name"] = doc.name
        mirror["_site"] = frappe.local.site
        saved_path = append_jsonl(jpath, mirror)
    except Exception as e:
        # Log but don't fail the request — DocType insert already succeeded.
        frappe.log_error(message=str(e), title="feedback_widget jsonl mirror failed")

    # 3) Telegram push — async via the worker queue so the HTTP response
    # returns immediately. Soft-fail: the worker logs errors but never affects
    # the saved comment. Skipped silently if Telegram isn't configured.
    _ct = cai_dat()
    _duoc_day = True
    if source == "auto" and not int(_ct.get("telegram_first_seen") or 0):
        _duoc_day = False
    try:
        if _duoc_day and notifier.is_configured():
            frappe.enqueue(
                "feedback_widget.api.feedback._push_telegram_for_doc",
                queue="short",
                doc_name=doc.name,
                enqueue_after_commit=True,  # don't push for a row that hasn't committed
            )
    except Exception as e:
        frappe.log_error(message=str(e), title="feedback_widget telegram enqueue failed")

    return {
        "ok": True,
        "name": doc.name,
        "saved_as": os.path.basename(saved_path) if saved_path else "",
    }


def _push_telegram_for_doc(doc_name: str) -> None:
    """Worker job — fetch a Feedback Comment by name and push to Telegram with
    rich-format caption + any attached images. Marks `telegram_pushed=1` on
    success. Silent (logged) failure on any error.
    """
    try:
        doc = frappe.get_doc("Feedback Comment", doc_name)
    except Exception as e:
        frappe.log_error(message=str(e), title=f"feedback_widget telegram: load {doc_name}")
        return

    # Reconstruct the entry shape default_telegram_summary expects from the
    # stored DocType row + JSON columns
    entry = {
        "project": doc.project,
        "screen_id": doc.screen_id,
        "screen_name": doc.screen_name,
        "message": doc.message,
        "submitter": doc.submitter,
        "ts": doc.ts.isoformat() if hasattr(doc.ts, "isoformat") else str(doc.ts),
    }
    if doc.tag_type or doc.tag_severity:
        entry["tags"] = {
            "type": doc.tag_type, "severity": doc.tag_severity,
        }
    try:
        if doc.pointed_element:
            entry["pointed_element"] = json.loads(doc.pointed_element)
        if doc.context:
            entry["context"] = json.loads(doc.context)
    except Exception:
        pass

    site_url = ""
    try:
        # Build a clickable site URL — prefer the public hostname from request
        # Host header if available; fall back to local site name.
        site_url = f"https://{frappe.local.site}/app/feedback-comment/{doc_name}"
    except Exception:
        pass
    summary_fn = default_telegram_summary(
        project_name=doc.project or "",
        base_url=site_url,
    )
    caption = summary_fn(entry)

    # Resolve attachment paths from the JSON column. Frappe File records have
    # file_url like "/private/files/xxx" (private) or "/files/xxx" (public);
    # both map to the site's public/ or private/files/ on disk.
    attachment_paths: list = []
    try:
        atts = json.loads(doc.attachments or "[]")
        for a in atts:
            url = a.get("file_url") or ""
            if not url:
                continue
            # Resolve to absolute filesystem path
            if url.startswith("/private/files/"):
                p = frappe.get_site_path("private", "files", url.split("/private/files/", 1)[1])
            elif url.startswith("/files/"):
                p = frappe.get_site_path("public", "files", url.split("/files/", 1)[1])
            else:
                continue
            attachment_paths.append(p)
    except Exception as e:
        frappe.log_error(message=str(e), title=f"feedback_widget telegram: parse attachments {doc_name}")

    ok = notifier.push_feedback(caption, attachment_paths=attachment_paths)
    try:
        frappe.db.set_value("Feedback Comment", doc_name, "telegram_pushed", 1 if ok else 0,
                            update_modified=False)
        frappe.db.commit()
    except Exception:
        pass


@frappe.whitelist(allow_guest=False, methods=["GET", "POST"])
def status_for_names(names=None, project: str = None):
    """Return status info for the given Feedback Comment names, scoped to
    those submitted by the current user.

    Used by the widget to fetch fresh status + status_note updates so users
    can see when their feedback has been Triaged / Resolved / etc. The widget
    sends the local names it has cached; we return only the ones the caller
    actually owns so a malicious client can't probe for other users' rows.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return {"items": []}

    # Parse names: JSON array string, comma-separated string, or list
    if isinstance(names, str):
        s = names.strip()
        if s.startswith("["):
            try:
                names = json.loads(s)
            except Exception:
                names = [n.strip() for n in s.split(",") if n.strip()]
        else:
            names = [n.strip() for n in s.split(",") if n.strip()]
    if not isinstance(names, list):
        names = []
    names = [str(n) for n in names if n][:200]
    if not names:
        return {"items": []}

    filters = {"name": ["in", names], "submitter_user": user}
    if project:
        filters["project"] = project

    rows = frappe.db.get_all(
        "Feedback Comment",
        filters=filters,
        fields=["name", "status", "status_note", "status_changed_at", "ts"],
        limit_page_length=len(names),
    )
    items = []
    for r in rows:
        sca = r.get("status_changed_at")
        items.append({
            "name": r["name"],
            "status": r.get("status") or "New",
            "status_note": r.get("status_note") or "",
            "status_changed_at": sca.isoformat() if hasattr(sca, "isoformat") else (sca or None),
        })
    return {"items": items}


@frappe.whitelist(allow_guest=False, methods=["GET"])
def jsonl_path(project: str = None):
    """Return absolute path to the JSONL inbox for a project. Useful for AI
    agents that need to know where to grep. System Manager only — anyone else
    gets 403."""
    if "System Manager" not in frappe.get_roles():
        frappe.throw(_("System Manager role required"), frappe.PermissionError)
    project = (project or "").strip() or "default"
    return {"path": str(_jsonl_path(project).resolve())}


def _default_settings() -> dict:
    return {
        "enabled": True,
        "enable_on_desk": True,
        "enable_on_portal": True,
        "allow_all_roles": True,
        "allowed_roles": [],
        "project_name": "",
        "primary_color": "#1f3a5f",
        "fab_color": "#047857",
    }


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_settings() -> dict:
    """Return public settings for feedback widget (cached)."""
    try:
        if not frappe.db or not frappe.db.exists("DocType", "Feedback Settings"):
            return _default_settings()
        # Giá trị HIỆU LỰC hỏi `cai_dat()`, KHÔNG đọc thẳng doc: với Single, `default`
        # khai trong DocType JSON không nằm trong `tabSingles` cho tới khi ai đó lưu một
        # lần, nên `doc.enable_on_desk` trả 0 ở site mới cài ⇒ `is_eligible` False ⇒
        # widget không gắn ⇒ vừa mất nút vừa KHÔNG thu gì, không một dòng lỗi. Đo trên
        # gương HTS 26/08 sau lượt gộp: đúng hai khoá `enable_on_desk`/`allow_all_roles`
        # vắng mặt. `cai_dat()` đã có sẵn tầng mặc định (`MAC_DINH`) nên hỏi nó là hết
        # cả lớp lỗi này, kể cả cho khoá thêm về sau. Bảng con vẫn phải đọc từ doc.
        from feedback_widget.cai_dat import cai_dat

        ct = cai_dat()
        doc = frappe.get_cached_doc("Feedback Settings")
        cho_tat_ca = bool(int(ct.get("allow_all_roles") or 0))
        roles = [r.role for r in (doc.get("allowed_roles") or [])] if not cho_tat_ca else []
        return {
            "enabled": bool(int(ct.get("enabled") or 0)),
            "enable_on_desk": bool(int(ct.get("enable_on_desk") or 0)),
            "enable_on_portal": bool(int(ct.get("enable_on_portal") or 0)),
            "allow_all_roles": cho_tat_ca,
            "allowed_roles": roles,
            "project_name": (ct.get("project_name") or "").strip(),
            "primary_color": ct.get("primary_color") or "#1f3a5f",
            "fab_color": ct.get("fab_color") or "#047857",
        }
    except Exception:
        return _default_settings()


def extend_bootinfo(bootinfo):
    """Inject feedback widget settings and user eligibility into Desk bootinfo."""
    settings = get_settings()
    user = frappe.session.user
    user_roles = frappe.get_roles(user) if user and user != "Guest" else []

    is_eligible = False
    if settings["enabled"] and settings["enable_on_desk"]:
        if settings["allow_all_roles"]:
            is_eligible = True
        else:
            is_eligible = any(r in user_roles for r in settings["allowed_roles"])

    bootinfo.feedback_widget_settings = {
        **settings,
        "is_eligible": is_eligible,
    }
    # v1.6 — cài đặt THU THẬP đi cùng một cửa boot với cài đặt hiển thị. Hai cửa
    # (`extend_bootinfo` + `boot_session`) cùng nhồi cài đặt là hai bản của một luật, và
    # trình duyệt đọc bản nào là do thứ tự nạp quyết định.
    try:
        from feedback_widget.cai_dat import payload_cho_trinh_duyet

        bootinfo.feedback_widget = payload_cho_trinh_duyet(user)
    except Exception:
        # Boot HỎNG là cả desk trắng màn. Một tính năng ghi sổ không được phép làm điều đó.
        frappe.log_error(frappe.get_traceback(), "feedback_widget boot")

