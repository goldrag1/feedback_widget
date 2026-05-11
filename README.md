# feedback_widget

Drop-in floating feedback widget for Frappe sites.

## What it does

A small `💬` button on every desk page. Tap → bottom sheet → user picks a tag (🐛 Lỗi · 💡 Ý tưởng · …), optionally taps `📍` and clicks the element they're talking about, types a message, hits send.

Each comment lands in **two places**:

1. **`Feedback Comment` DocType** — canonical, queryable, permissioned. ListView at `/app/feedback-comment`.
2. **JSONL inbox at `sites/<site>/private/feedback/<project>.jsonl`** — append-only raw payload for AI coding agents to grep / jq / cat. One submission per line.

## Why dual-write

| Use | Read from |
|---|---|
| Triage UI, search, status workflow | DocType (Frappe ListView) |
| AI coding agent in a Claude Code session | JSONL (no DB, no SQL, just `jq`) |
| Rebuild after DB reset | JSONL (DocType is derived) |
| Telegram push, alerting | DocType `on_insert` hook (TODO) |

The JSONL is **append-only**. If a triager later edits the DocType (status, paraphrase), the JSONL still holds the original wording — useful for "what did the user actually say?" audits.

## For AI coding agents

The JSONL inbox lives at:

```
~/long/frappe-bench-dcnet/sites/<site>/private/feedback/<project>.jsonl
```

Default `<project>` slug for this app on dcnet = `dcnet-dcnet.localhost` (sitename-derived).

### Common queries

```bash
# Show last 5 comments
tail -5 sites/dcnet.localhost/private/feedback/dcnet-dcnet.localhost.jsonl | jq

# All blocker bugs from accountants
jq -c 'select(.tags.severity=="blocker" and (.context.app.roles // [] | any(. == "Accounts User")))' \
   sites/dcnet.localhost/private/feedback/*.jsonl

# Group comments by screen, count
jq -r '.screen_name' sites/dcnet.localhost/private/feedback/*.jsonl | sort | uniq -c | sort -rn

# Export to markdown audit report (uses shared skill exporter)
python3 ~/.claude/skills/feedback-widget/feedback_export.py \
   sites/dcnet.localhost/private/feedback/dcnet-dcnet.localhost.jsonl --by screen
```

### Comment shape

```jsonc
{
  "project": "dcnet-dcnet.localhost",
  "screen_id": "Form/Sales Invoice/SI-001",
  "screen_name": "Sales Invoice · SI-001",
  "message": "Nút Submit không hoạt động khi điền VAT 0%",
  "submitter": "Nguyễn Hoàng Long",
  "ts": "2026-05-11T06:35:00Z",
  "received_at": "2026-05-11T06:35:00.142Z",
  "user_agent": "Mozilla/5.0 ...",
  "tags": { "type": "bug", "severity": "blocker" },
  "pointed_element": {
    "selector": ".btn-primary[data-fieldname=submit]",
    "tag": "button",
    "text": "Submit",
    "html": "<button class=\"btn btn-primary\">Submit</button>",
    "bbox": { "x": 100, "y": 200, "w": 80, "h": 32 },
    "viewport": { "w": 1440, "h": 900 }
  },
  "context": {
    "url": "http://dcnet.localhost:8001/app/sales-invoice/SI-001",
    "viewport": { "w": 1440, "h": 900, "dpr": 2 },
    "recent_actions": [
      { "type": "click", "target": "input.fbw-name", "ts": 1730000000000 },
      { "type": "route", "target": "Form/Sales Invoice/SI-001", "ts": 1730000001000 }
    ],
    "console_errors": [
      { "type": "error", "message": "Cannot read properties of undefined", "ts": 1730000002000 }
    ],
    "app": {
      "route": "Form/Sales Invoice/SI-001",
      "doctype": "Sales Invoice",
      "docname": "SI-001",
      "docstatus": 0,
      "user": "long@dcnet.vn",
      "user_full_name": "Nguyễn Hoàng Long",
      "roles": ["Accounts User", "Sales User", "All"],
      "versions": { "frappe": "16.17.0", "erpnext": "16.17.2" }
    }
  },
  "_doc_name": "FB-2026-00042",
  "_site": "dcnet.localhost"
}
```

`_doc_name` lets you cross-reference to the DocType row:

```bash
bench --site dcnet.localhost execute frappe.client.get_value \
  --kwargs '{"doctype":"Feedback Comment","filters":"FB-2026-00042","fieldname":"status"}'
```

### Identity is server-trusted

`submitter_user`, `user_full_name`, `user_roles` (DocType columns) and `context.app.user`, `context.app.roles` (JSONL) are **always** re-derived from `frappe.session` and `frappe.get_roles()` at insert time. The widget JS supplies its own `getContext()` view, but the server overwrites the identity fields. A malicious client cannot impersonate another user or grant themselves roles in the stored record.

## Install

```bash
cd ~/long/frappe-bench-dcnet
env/bin/pip install -e apps/feedback_widget
echo feedback_widget >> sites/apps.txt
bench --site dcnet.localhost install-app feedback_widget
bench build --app feedback_widget
bench restart  # required: app_include_js needs server reload
```

## Permissions

- **System Manager** — full read/write/delete on all comments
- **All authenticated users** — can create + read (each user sees their own; Owner-based visibility via standard Frappe permission model)
- **Guest** — denied (the `collect()` endpoint is `allow_guest=False`)

For public mockups, deploy the standalone collector instead — see `~/.claude/skills/feedback-widget/SKILL.md` Recipe A.

## Endpoints

| Path | Method | Auth | Purpose |
|---|---|---|---|
| `/api/method/feedback_widget.api.feedback.collect` | POST | session | Submit a comment |
| `/api/method/feedback_widget.api.feedback.jsonl_path` | GET | System Manager | Get absolute path to JSONL inbox for a project |

CSRF: the widget passes `X-Frappe-CSRF-Token` from `frappe.csrf_token` automatically.
