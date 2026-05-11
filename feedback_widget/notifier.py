"""Telegram notifier for feedback_widget.

Reads the same Telegram bot config the rest of the user's stack uses:
  ~/.claude/channels/telegram/.env       → TELEGRAM_BOT_TOKEN
  ~/.claude/channels/telegram/access.json → allowFrom[0] is the chat_id

Soft-fails on every failure path: missing config, network error, Telegram
API error → log + return False. Never raises. Feedback save must NOT depend
on Telegram being healthy.

Three send modes:
  - send_message(text)                        → /sendMessage (text only)
  - send_photo(text, photo_path)              → /sendPhoto with caption
  - send_media_group(text, photo_paths)       → /sendMediaGroup (2-10 photos
                                                 + caption on first item)

Telegram constraints we enforce:
  - Caption max 1024 UTF-8 chars (we truncate)
  - sendMediaGroup wants 2-10 items (we route 1 item → sendPhoto, 11+ →
    sendMediaGroup in batches of 10)
  - Photo file size ≤ 10MB per Telegram (we skip oversized files with a
    warning instead of failing the whole batch)
"""
from __future__ import annotations

import json
import mimetypes
import pathlib
import secrets
import urllib.request
from typing import Iterable, Optional, Tuple

ENV_PATH = pathlib.Path.home() / ".claude" / "channels" / "telegram" / ".env"
ACCESS_PATH = pathlib.Path.home() / ".claude" / "channels" / "telegram" / "access.json"

CAPTION_MAX_BYTES = 1024
PHOTO_MAX_BYTES = 10 * 1024 * 1024  # Telegram bot API limit
TELEGRAM_API = "https://api.telegram.org"


def _log(msg: str) -> None:
    """Single log entry point. Routes through Frappe if available so it lands
    in the bench error log; falls back to stderr otherwise."""
    try:
        import frappe  # type: ignore
        frappe.logger("feedback_widget").info(f"[notifier] {msg}")
    except Exception:
        import sys
        print(f"[feedback_widget notifier] {msg}", file=sys.stderr)


def _load_config() -> Tuple[Optional[str], Optional[str]]:
    """Returns (bot_token, chat_id) or (None, None) if config missing."""
    token: Optional[str] = None
    chat_id: Optional[str] = None
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if ACCESS_PATH.exists():
        try:
            access = json.loads(ACCESS_PATH.read_text(encoding="utf-8"))
            allow = access.get("allowFrom") or []
            if allow:
                chat_id = str(allow[0])
        except json.JSONDecodeError:
            pass
    return token, chat_id


def is_configured() -> bool:
    t, c = _load_config()
    return bool(t and c)


def _truncate_caption(s: str) -> str:
    """Telegram caption is 1024 UTF-8 chars. Trim safely on character boundary."""
    if not s:
        return ""
    encoded = s.encode("utf-8")
    if len(encoded) <= CAPTION_MAX_BYTES:
        return s
    # Trim then re-decode safely
    return encoded[:CAPTION_MAX_BYTES - 3].decode("utf-8", errors="ignore") + "…"


def _build_multipart(
    fields: dict,
    files: Iterable[Tuple[str, str, bytes, str]],
    boundary: str,
) -> Tuple[bytes, str]:
    """fields: {name: value}. files: iterable of (field_name, filename, body_bytes, mime).
    Returns (body, content_type)."""
    parts: list = []
    for k, v in fields.items():
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
        parts.append(str(v).encode("utf-8"))
        parts.append(b"\r\n")
    for field_name, filename, data, mime in files:
        parts.append(f"--{boundary}\r\n".encode())
        # Quote/escape the filename minimally — Telegram accepts UTF-8
        safe_filename = filename.replace('"', '_')
        parts.append(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{safe_filename}"\r\n'.encode("utf-8")
        )
        parts.append(f"Content-Type: {mime}\r\n\r\n".encode())
        parts.append(data)
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    ctype = f"multipart/form-data; boundary={boundary}"
    return body, ctype


def _post(url: str, body: bytes, content_type: str, timeout: int = 30) -> Tuple[bool, dict]:
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": content_type})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read()
            try:
                parsed = json.loads(payload)
            except Exception:
                parsed = {"raw": payload[:200].decode("utf-8", errors="ignore")}
            ok = 200 <= resp.status < 300 and parsed.get("ok") is not False
            return ok, parsed
    except Exception as e:
        return False, {"error": str(e)}


def send_message(text: str, parse_mode: str = "HTML",
                 chat_id: Optional[str] = None) -> bool:
    """Send a plain text message. Returns True on success."""
    token, default_chat = _load_config()
    chat = chat_id or default_chat
    if not (token and chat and text):
        _log(f"sendMessage skipped (token={bool(token)}, chat={bool(chat)}, text={bool(text)})")
        return False
    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    boundary = "fbw" + secrets.token_hex(8)
    body, ctype = _build_multipart(
        {
            "chat_id": chat,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": "true",
        },
        [],
        boundary,
    )
    ok, resp = _post(url, body, ctype, timeout=15)
    if not ok:
        _log(f"sendMessage failed: {resp}")
    return ok


def _read_file(path: pathlib.Path) -> Optional[Tuple[bytes, str, str]]:
    """Read a file. Returns (bytes, filename, mime) or None on error / oversize."""
    try:
        data = path.read_bytes()
    except Exception as e:
        _log(f"read failed for {path}: {e}")
        return None
    if len(data) > PHOTO_MAX_BYTES:
        _log(f"skipping oversize file {path} ({len(data)} bytes > {PHOTO_MAX_BYTES})")
        return None
    mime, _ = mimetypes.guess_type(str(path))
    return data, path.name, mime or "application/octet-stream"


def send_photo(caption: str, photo_path: pathlib.Path,
               parse_mode: str = "HTML",
               chat_id: Optional[str] = None) -> bool:
    """Send a single photo with caption."""
    token, default_chat = _load_config()
    chat = chat_id or default_chat
    if not (token and chat):
        _log("sendPhoto skipped (no token / chat)")
        return False
    f = _read_file(pathlib.Path(photo_path))
    if not f:
        return False
    data, filename, mime = f
    url = f"{TELEGRAM_API}/bot{token}/sendPhoto"
    boundary = "fbw" + secrets.token_hex(8)
    body, ctype = _build_multipart(
        {
            "chat_id": chat,
            "caption": _truncate_caption(caption or ""),
            "parse_mode": parse_mode,
        },
        [("photo", filename, data, mime)],
        boundary,
    )
    ok, resp = _post(url, body, ctype, timeout=60)
    if not ok:
        _log(f"sendPhoto failed: {resp}")
    return ok


def send_media_group(caption: str, photo_paths: Iterable[pathlib.Path],
                     parse_mode: str = "HTML",
                     chat_id: Optional[str] = None) -> bool:
    """Send 2-10 photos as an album with caption on the first item.

    For 1 photo, routes to send_photo. For 11+ photos, sends in batches of 10
    with caption only on the first batch's first item.
    """
    token, default_chat = _load_config()
    chat = chat_id or default_chat
    if not (token and chat):
        _log("sendMediaGroup skipped (no token / chat)")
        return False

    paths = [pathlib.Path(p) for p in photo_paths]
    if not paths:
        return False
    if len(paths) == 1:
        return send_photo(caption, paths[0], parse_mode=parse_mode, chat_id=chat_id)

    # Read all files; skip ones that fail or are oversize
    loaded: list[Tuple[bytes, str, str]] = []
    for p in paths:
        f = _read_file(p)
        if f:
            loaded.append(f)
    if not loaded:
        return False
    if len(loaded) == 1:
        d, fn, mt = loaded[0]
        # Fall back to sendPhoto for the single survivor
        return send_photo(caption, paths[0], parse_mode=parse_mode, chat_id=chat_id)

    # Batch in groups of 10. Caption only on the very first item of the first batch.
    overall_ok = True
    first_batch = True
    for i in range(0, len(loaded), 10):
        batch = loaded[i:i + 10]
        media: list = []
        files: list = []
        for j, (data, filename, mime) in enumerate(batch):
            field_name = f"file{i + j}"
            files.append((field_name, filename, data, mime))
            item = {"type": "photo", "media": f"attach://{field_name}"}
            if first_batch and j == 0 and caption:
                item["caption"] = _truncate_caption(caption)
                item["parse_mode"] = parse_mode
            media.append(item)
        first_batch = False

        url = f"{TELEGRAM_API}/bot{token}/sendMediaGroup"
        boundary = "fbw" + secrets.token_hex(8)
        body, ctype = _build_multipart(
            {"chat_id": chat, "media": json.dumps(media)},
            files,
            boundary,
        )
        ok, resp = _post(url, body, ctype, timeout=120)
        if not ok:
            _log(f"sendMediaGroup batch failed: {resp}")
            overall_ok = False
    return overall_ok


# ---------- Convenience entry point used by api/feedback.py ----------

def push_feedback(summary_text: str, attachment_paths: Optional[list] = None) -> bool:
    """Send a feedback notification — text only or text+photos depending on
    whether attachments were supplied. Returns True on success.

    summary_text is the formatted Telegram message (HTML-safe). Caller is
    responsible for formatting (use feedback_handler.default_telegram_summary).

    attachment_paths: list of absolute filesystem paths to image files.
    """
    if not is_configured():
        _log("push_feedback skipped (telegram not configured)")
        return False
    paths = [pathlib.Path(p) for p in (attachment_paths or []) if p]
    paths = [p for p in paths if p.exists()]
    if not paths:
        return send_message(summary_text)
    if len(paths) == 1:
        return send_photo(summary_text, paths[0])
    return send_media_group(summary_text, paths)
