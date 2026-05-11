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
from frappe.utils import get_datetime, now_datetime

# Make the shared validator importable. The skill lives outside the bench so
# both standalone HTML demos and this app share the same rules.
SHARED_PATH = pathlib.Path.home() / ".claude" / "skills" / "feedback-widget"
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

try:
    from feedback_handler import validate_payload, append_jsonl, FeedbackError  # type: ignore
except Exception as e:  # pragma: no cover — dev-time guard
    raise ImportError(
        f"feedback_widget requires shared validator at {SHARED_PATH}/feedback_handler.py "
        f"(install or symlink the feedback-widget skill from ~/.claude/skills/). Original: {e}"
    )


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

    # 1) Insert DocType row — flatten the rich blobs into Code (JSON) cells
    pe = entry.get("pointed_element") or {}
    ctx = entry.get("context") or {}
    tags = entry.get("tags") or {}

    # ─── Server-authoritative identity ─────────────────────────────────────
    # Never trust client-supplied user/role data — re-derive from session.
    # The widget DOES collect these in ctx.app for HTML-mockup parity, but
    # for Frappe we overwrite them so a malicious client cannot impersonate.
    session_user = frappe.session.user
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

    # Widget sends `ts` as ISO 8601 with trailing Z (UTC). MySQL `datetime`
    # rejects timezone suffix and tz-aware Python datetimes — strip tzinfo so
    # the value lands as naive local time.
    ts_iso = entry.get("ts") or ""
    try:
        ts_dt = get_datetime(ts_iso) if ts_iso else now_datetime()
        if ts_dt and getattr(ts_dt, "tzinfo", None) is not None:
            ts_dt = ts_dt.replace(tzinfo=None)
    except Exception:
        ts_dt = now_datetime()

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
        "pointed_element": json.dumps(pe, ensure_ascii=False) if pe else None,
        "url": (ctx.get("url") or "")[:500] or None,
        "user_agent": entry.get("user_agent") or None,
        "context": json.dumps(ctx, ensure_ascii=False) if ctx else None,
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

    return {
        "ok": True,
        "name": doc.name,
        "saved_as": os.path.basename(saved_path) if saved_path else "",
    }


@frappe.whitelist(allow_guest=False, methods=["GET"])
def jsonl_path(project: str = None):
    """Return absolute path to the JSONL inbox for a project. Useful for AI
    agents that need to know where to grep. System Manager only — anyone else
    gets 403."""
    if "System Manager" not in frappe.get_roles():
        frappe.throw(_("System Manager role required"), frappe.PermissionError)
    project = (project or "").strip() or "default"
    return {"path": str(_jsonl_path(project).resolve())}
