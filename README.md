# feedback_widget

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Frappe](https://img.shields.io/badge/Frappe-v15%2B-0089FF.svg)](https://frappeframework.com/)
[![Commercial license $20/site/year](https://img.shields.io/badge/Commercial-%2420%2Fsite%2Fyear-success.svg)](COMMERCIAL.md)
[![Questions](https://img.shields.io/badge/Questions-Discussions-blueviolet.svg)](https://github.com/goldrag1/feedback_widget/discussions)

A floating per-screen feedback widget for **Frappe / ERPNext**. Click the 💬 bubble on any desk page, leave a comment, attach screenshots, pin specific elements. Submissions land in the `Feedback Comment` DocType for triage AND in a JSONL inbox at `sites/<site>/private/feedback/<project>.jsonl` for AI-agent consumption.

Companion Odoo widget at [`goldrag1/odoo-feedback-widget`](https://github.com/goldrag1/odoo-feedback-widget) — same UX, same JSONL schema, same license + pricing.

---

## Highlights

- **One file, no deps** — `feedback_widget.bundle.js` is ~25KB embedding its own CSS, no React/jQuery/lodash imports
- **Drop-in on every desk page** — loaded via `app_include_js` in hooks
- **Multi-pin element picker** — click N elements in a row, ESC to finish; touch-friendly highlight
- **Per-screen history panel** — your own past comments + status badge for each
- **Offline-first** — failed POSTs go to localStorage and retry on reconnect
- **Browser context capture** — last 50 console errors + last 30 user actions sent with every submission
- **Clipboard paste attachments** — paste screenshots directly into the modal
- **Dual-write storage** — `Feedback Comment` DocType (Frappe ListView triage) + JSONL inbox (AI-pipeline consumption)
- **Telegram push** — optional, configurable via `~/.claude/channels/telegram/.env` or settings
- **Vietnamese + English** widget strings, auto-detect from browser
- **Status workflow** — manager moves the entry through New → Triaged → In Progress → Resolved → Wontfix, widget polls and shows the badge to the user next time they open it

---

## Why dual-write (DocType + JSONL)

| Use case | Read from |
|---|---|
| Triage UI, search, status workflow, role-based permissions | `Feedback Comment` DocType (ListView at `/app/feedback-comment`) |
| AI coding agent in a Claude Code session | JSONL (no DB, no SQL — just `jq`/`grep`) |
| Rebuild after DB reset | JSONL (the DocType is derived) |
| Long-term audit ("what did the user actually say?") | JSONL (append-only, unedited) |

The JSONL is **append-only**. If a triager paraphrases or edits the DocType later, the JSONL still holds the original wording.

---

## Install

```bash
cd ~/frappe-bench
bench get-app https://github.com/goldrag1/feedback_widget.git
bench --site <site> install-app feedback_widget
bench restart
```

The widget appears as a green 💬 button on every page of `/app`.

### Requirements

- Frappe v15+ (tested on v15, should work on v14 with minor `frappe.ui` adjustments)
- No Frappe app dependencies beyond `frappe` itself

---

## Configuration

Most settings live in a single document — **Feedback Widget Settings** (Single DocType, accessible to System Manager). Notable knobs:

| Setting | Default | Notes |
|---|---|---|
| Project slug | `<sitename>` | Namespace for JSONL mirror + Telegram message |
| Anonymous allowed | true (configurable) | If your site uses `allow_guest=True` |
| Attachment max size | 8 MB | Per file |
| Attachment max count | 10 | Per submission (mirrors Telegram media-group cap) |
| Language | auto | English / Vietnamese, browser auto-detect by default |

For Telegram, the addon reads creds from `~/.claude/channels/telegram/.env` (`TELEGRAM_BOT_TOKEN=...`) + `~/.claude/channels/telegram/access.json` (chat ID in `allowFrom[0]`). Falls back to settings doc if not present.

---

## For AI coding agents

The JSONL inbox lives at:

```
sites/<site>/private/feedback/<project>.jsonl
```

Default `<project>` slug = sitename-derived (e.g. `dcnet-dcnet.localhost`).

### Common queries

```bash
# Last 5 comments
tail -5 sites/<site>/private/feedback/<project>.jsonl | jq

# All blocker bugs from accountants
jq -c 'select(.tags.severity=="blocker" and (.context.app.roles // [] | any(. == "Accounts User")))' \
   sites/<site>/private/feedback/*.jsonl

# Group by screen, count
jq -r '.screen_name' sites/<site>/private/feedback/*.jsonl | sort | uniq -c | sort -rn

# Export to markdown audit report (uses the shared exporter)
python3 ~/.claude/skills/feedback-widget/feedback_export.py \
   sites/<site>/private/feedback/<project>.jsonl --by screen
```

### Comment shape

```jsonc
{
  "project": "dcnet-dcnet.localhost",
  "screen_id": "Form/Sales Invoice/SI-001",
  "screen_name": "Sales Invoice · SI-001",
  "message": "Submit không hoạt động khi điền VAT 0%",
  "submitter": "Hieu",
  "ts": "2026-05-20T10:23:00Z",
  "tags": { "type": "bug", "severity": "blocker" },
  "pointed_elements": [
    { "selector": "button.primary-action", "text": "Submit", "rect": {...} }
  ],
  "attachments": [
    { "file_url": "/private/files/screenshot.png", "file_name": "screenshot.png" }
  ],
  "context": {
    "url": "https://dcnet.localhost/app/sales-invoice/SI-001",
    "viewport": { "w": 1920, "h": 1080, "dpr": 1, "form_factor": "desktop" },
    "console_errors": [...last 50...],
    "recent_actions": [...last 30 clicks + routes...],
    "app": { "doctype": "Sales Invoice", "docname": "SI-001", "user": "...", "roles": [...] }
  }
}
```

---

## Privacy stance

- User-agent truncated to 160 chars on capture
- No cookies, geolocation, or device IDs are read
- Submitter name is asked once on the first comment and persisted to localStorage — never auto-collected
- Per-deployment opt-out for context capture (console errors + recent actions)
- JSONL is `chmod 600` per-site `private/` folder — only the Frappe bench user can read it
- DocType respects standard Frappe permission roles

---

## Documentation

The widget is intentionally simple — most of what you need is in this README + the `Feedback Widget Settings` doc. For the broader design rationale (multi-pin UX choices, the dual-write architecture, the AI-pipeline JSONL schema), see the companion Odoo addon's docs at [`goldrag1/odoo-feedback-widget/docs`](https://github.com/goldrag1/odoo-feedback-widget/tree/main/docs) — same underlying design.

---

## License

[**GNU AGPL-3.0**](LICENSE) for community use — free for personal, internal, and contributor use. The full license text is in `LICENSE`.

**Commercial license: $20 USD per production site per year** — if you're integrating into a proprietary SaaS, bundling with closed-source modules, or your compliance team has flagged AGPL, see [COMMERCIAL.md](COMMERCIAL.md) for terms and how to request one.

Questions? Open a [GitHub Discussion](https://github.com/goldrag1/feedback_widget/discussions).
