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
~/long/frappe-bench-<bench>/sites/<site>/private/feedback/<project>.jsonl
```

Default `<project>` slug = `<bench>-<site>` (sitename-derived).

### Common queries

```bash
# Show last 5 comments
tail -5 sites/<site>/private/feedback/<bench>-<site>.jsonl | jq

# All blocker bugs from accountants
jq -c 'select(.tags.severity=="blocker" and (.context.app.roles // [] | any(. == "Accounts User")))' \
   sites/<site>/private/feedback/*.jsonl

# Group comments by screen, count
jq -r '.screen_name' sites/<site>/private/feedback/*.jsonl | sort | uniq -c | sort -rn

# Export to markdown audit report (uses shared skill exporter)
python3 ~/.claude/skills/feedback-widget/feedback_export.py \
   sites/<site>/private/feedback/<bench>-<site>.jsonl --by screen
```

### Comment shape

```jsonc
{
  "project": "<bench>-<site>",
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
    "url": "http://<site>:<port>/app/sales-invoice/SI-001",
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
      "user": "long@nextstar.vn",
      "user_full_name": "Nguyễn Hoàng Long",
      "roles": ["Accounts User", "Sales User", "All"],
      "versions": { "frappe": "16.17.0", "erpnext": "16.17.2" }
    }
  },
  "_doc_name": "FB-2026-00042",
  "_site": "<site>"
}
```

`_doc_name` lets you cross-reference to the DocType row:

```bash
bench --site <site> execute frappe.client.get_value \
  --kwargs '{"doctype":"Feedback Comment","filters":"FB-2026-00042","fieldname":"status"}'
```

### Identity is server-trusted

`submitter_user`, `user_full_name`, `user_roles` (DocType columns) and `context.app.user`, `context.app.roles` (JSONL) are **always** re-derived from `frappe.session` and `frappe.get_roles()` at insert time. The widget JS supplies its own `getContext()` view, but the server overwrites the identity fields. A malicious client cannot impersonate another user or grant themselves roles in the stored record.

## Install

```bash
cd ~/long/frappe-bench-<bench>
env/bin/pip install -e apps/feedback_widget
echo feedback_widget >> sites/apps.txt
bench --site <site> install-app feedback_widget
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


---

# v1.6 — Sổ chặn tự động (auto telemetry)

**Vấn đề nó giải:** người dùng không báo lỗi. Họ bị chặn, thử lại vài lần, rồi đi làm
việc khác — dự án tưởng là êm. Đo trên một xưởng thép đang bàn giao (25/08/2026):
538 chỗ `frappe.throw` trong app, **0 dấu vết** ở đường đồng bộ; 59 lần bị chặn trong
9 ngày chỉ ghi được vì chúng đi qua việc nền, và không ai từng đọc.

## Ba tầng

| Tầng | Bảng | Trả lời |
|---|---|---|
| Sổ THÔ | `Feedback Event` | tần suất · mẫu số · chuỗi thao tác · thời gian |
| VÉ | `Feedback Comment` với `source=auto`, gom theo `signature` | "có bao nhiêu LOẠI sự cố, ai đang xử" |
| DANH MỤC | `Feedback Manifest Item` | "cái gì KHÔNG ai dùng" |

Vé máy **gom theo chữ ký** (`chu_ky.py`, tính ở máy chủ): cùng một loại sự cố dù khác mã
lô / khác số luôn về một vé, `occurrences` đếm lần, `affected_users` liệt kê ai. Vé đã
`Resolved` mà chữ ký quay lại thì mở vé MỚI — hồi quy phải nhìn thấy được.

## Thu từ đâu

- **Lỗi trình duyệt** (`window.onerror`, promise treo, `console.error`) — widget đã bắt
  sẵn từ v1.0, nay tự gửi thay vì đợi người bấm.
- **Máy chủ từ chối** — móc ở CẢ `fetch` VÀ `XMLHttpRequest` (desk của Frappe gọi bằng
  XHR; bản chỉ móc `fetch` bắt được 0 lần).
- **App chủ báo trực tiếp** — `window.FeedbackWidget.report({message, endpoint, args})`,
  nơi biết TÊN endpoint và THAM SỐ thật. Trùng với tầng mạng thì widget tự khử.
- **Việc nền** — `tac_vu.bac_cau_error_log()` mỗi 15 phút đưa NGOẠI LỆ trong `Error Log`
  vào cùng hộp thư (nhật ký thông tin thì bỏ qua). Lần đầu KHÔNG đọc ngược lịch sử;
  muốn khai thác quá khứ thì gọi `tac_vu.khai_thac_lich_su(so_ngay=30)` — mặc định chạy thử.
- **Hành vi** — mở màn, bấm nút, kết quả mỗi lần gọi API, gửi theo lô 15 giây và bằng
  `sendBeacon` lúc rời trang; mất mạng thì xếp hàng ở `localStorage` rồi gửi bù.
- **Danh mục nút** — widget KIỂM KÊ nút đang hiện trên màn người dùng vừa mở (không đọc
  mã nguồn: bộ đọc mã phải đoán nút nào thuộc màn nào và sai lệch âm thầm).

## Cài đặt (`Feedback Settings`)

`show_widget` tắt = **GIẤU nút 💬 nhưng VẪN thu** — dùng khi không muốn làm phiền công
nhân mà vẫn cần biết họ tắc ở đâu. Ngoài ra: bật/tắt tự báo, bật/tắt sổ hành vi, tỉ lệ lấy
mẫu, bóp ga theo chữ ký, trần sự kiện/phút, số ngày giữ sổ, danh sách khoá cần che, giờ
gửi tổng kết.

## Đọc kết quả

Workspace **Feedback** → 3 báo cáo: `Blockers` (chỗ tắc, xếp theo SỐ NGƯỜI), `Screen
Behaviour` (lượt vào · thao tác · % chặn/lỗi), `Unused UI` (màn/nút chưa ai dùng).
Cho coding agent: `bench --site <site> execute feedback_widget.phan_tich.bao_cao
--kwargs "{'so_ngay': 7}"` in ra Markdown xếp hạng sẵn (skill `feedback-telemetry`).

## App chủ nối vào (tuỳ chọn, 2 việc)

1. Nhánh lỗi của lớp gọi API gọi `window.FeedbackWidget.report({message, endpoint, args})`.
2. Lúc `after_migrate` gọi `feedback_widget.api.su_kien.khai_danh_muc(items=[{kind:"screen",
   item_id, item_name}])` để "màn không ai vào" đo được.

## Riêng tư

Tham số được che theo danh sách khoá ở mọi độ sâu trước khi ghi. Sổ thô tự xoá sau
`retention_days` (mặc định 90). Đây là công cụ đo VIỆC, không phải đo NGƯỜI — nên nói
trước với người dùng rằng hệ ghi lại chỗ bị chặn để sửa phần mềm.
