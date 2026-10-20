# Kịch bản màn — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mỗi màn có kịch bản (hướng dẫn lần đầu, chặng, mẹo), giao được cho người kèm hạn, tự chấm từ sổ sự kiện, nhắc khi chậm, cộng điểm/cấp/huân chương danh dự, bảng vàng.

**Architecture:** Toàn bộ trong app `feedback_widget`. Máy chủ: `kich_ban.py` (luật khớp + chấm, MỘT định nghĩa), `diem.py` (sổ điểm, cấp, huân chương), `nhac.py` (luật nhắc + chống ồn), `api/kich_ban.py` (endpoint cho widget). Trình duyệt: tệp riêng `public/js/kich_ban_the.js` khai `window.FeedbackPlaybook`, đăng ký lối vào qua `FeedbackWidget.registerAction` trong bundle. Lời nhắc là `Feedback Notice` (sổ nhắc = Notice).

**Tech Stack:** Frappe v16, Python 3.14, MariaDB, JS thuần (không framework) trong bundle esbuild của Frappe.

**Spec:** `docs/specs/2026-10-20-kich-ban-man-design.md` (đọc kèm; các § bên dưới trỏ vào đó).

## Global Constraints

- Mọi tính năng sau công tắc `Feedback Settings.kb_bat` (mặc định **0**); `kb_bat=0` ⇒ cron no-op, API trả rỗng, menu không hiện.
- Mỗi khoá cài đặt mới phải có trong `cai_dat.MAC_DINH`; `khong_xep_hang` (bảng con) đọc riêng.
- Giá trị mặc định đúng bảng §4.10 của spec (điểm 10·30·5·30·20·20·50·5; ngưỡng 100·300·700; `gio_mo_duong` 48; `phien_da_quen` 3; giờ làm 08:00–18:00; ngày làm `1,2,3,4,5,6`; nhắc 3/ngày, 1/kịch bản/ngày, dừng sau 3 bỏ qua; N1 24h, N2 biên 25, N3 24h; `tuan_chuyen_can` 4).
- Chữ giao diện tiếng Việt có dấu; ô bấm ≥ 44px; chạy ở 390px.
- Điểm chỉ ghi qua `diem.ghi_diem` (khoá unique); luật khớp chỉ ở `kich_ban.py`.
- Không gửi gì ra ngoài trong test (`frappe.flags.in_test` chặn Telegram như các test hiện có).
- Comment/docstring tiếng Việt, theo giọng mã sẵn có của app.
- Nhánh `develop`; commit theo từng task, nêu tên tệp, không `git add -A`.

## Review Focus

1. Màn React desk / Frappe Page mà `screen_id` có hash (`#/...`) — `kich_ban_cua_man` phải khớp theo cùng chuỗi mà bundle gửi (`currentRoute()`): test khớp `chot-ton` và `Form/Doi Soat Cong No NCC/DSNCC-1`.
2. Người dùng đã quen màn không bị bật hướng dẫn — test với 3 `session_id` trước mốc bật.
3. Cron nhắc chạy hai lần liền / song song không gửi đôi thẻ — test gọi `nhac_kich_ban()` 2 lần.
4. Ngày Chủ nhật / ngoài giờ: không kỳ Duy trì, không nhắc — test với `luc` cố định CN 10:00 và T2 19:00.
5. Selector hướng dẫn không tồn tại trên màn — thẻ vẫn hiện, ghi `Feedback Event kind='loi'` chữ ký `kich-ban-chi-vao-mat:<KB>:<thu_tu>` (kiểm ở Task 9 trong Chrome).

---

### Task 1: Mô hình dữ liệu + cài đặt + chỉ mục

**Files:**
- Create: `feedback_widget/feedback_widget/doctype/{feedback_playbook, feedback_playbook_guide, feedback_playbook_stage, feedback_playbook_tip, feedback_mission_step, feedback_playbook_progress, feedback_mission, feedback_mission_assignee, feedback_point, feedback_badge_award}/` (json + `.py` + `__init__.py`)
- Modify: `feedback_comment.json` (+`tu_cam_nhan` hidden, `co_ich`, `thanh_cai_tien`), `feedback_notice.json` (+`kich_ban` Link, `loai_nhac` Data, `nhiem_vu` Link), `feedback_notice_seen.json` (+`tam_hoan` Check), `feedback_settings.json` (section "Kịch bản màn" với mọi trường §4.10), `cai_dat.py` (MAC_DINH + `khong_xep_hang()`)
- Create: `feedback_widget/patches/v1_8/chi_muc_su_kien.py`; Modify `patches.txt`
- Delete: `doctype/feedback_widget_settings/` (chỉ còn `__pycache__`)
- Test: `tests/test_kich_ban_mo_hinh.py`

**Interfaces — Produces:**
- DocType tên đúng spec §4.1–4.9, field đúng tên spec. `Feedback Playbook.man` unique. `Feedback Playbook Progress` unique `(kich_ban, user)` (qua `on_doctype_update` add_unique). `Feedback Point.khoa`, `Feedback Badge Award.khoa` unique.
- Quyền: mọi DocType mới chỉ System Manager đọc/ghi (người dùng đi qua API).
- `cai_dat.khong_xep_hang() -> set[str]`.
- Patch tạo chỉ mục `fbw_user_ts (user, ts)` và `fbw_screen_ts (screen_id, ts)` trên `tabFeedback Event`, idempotent.

- [ ] Step 1: Viết test `test_mo_hinh`: mọi DocType tồn tại; `cai_dat()` có đủ khoá §4.10 với đúng mặc định; `khong_xep_hang()` trả set; `show index` có `fbw_user_ts`, `fbw_screen_ts`; insert hai `Feedback Point` cùng `khoa` ⇒ `frappe.UniqueValidationError`/`DuplicateEntryError`.
- [ ] Step 2: Chạy `bench --site erp.htsfood.com run-tests --module feedback_widget.tests.test_kich_ban_mo_hinh` → FAIL.
- [ ] Step 3: Tạo DocType JSON (module "Feedback Widget", `custom: 0`), sửa JSON cũ, MAC_DINH, patch; `bench --site erp.htsfood.com migrate`.
- [ ] Step 4: Chạy lại test → PASS; chạy cả suite cũ `--app feedback_widget` → không đỏ mới.
- [ ] Step 5: Commit.

### Task 2: Luật khớp bước (`kich_ban.py`)

**Files:** Create `feedback_widget/kich_ban.py`; Test `tests/test_kich_ban_khop.py`

**Interfaces — Produces:**
- `mau_like(mau: str) -> str` — escape `\`, `%`, `_` rồi `*`→`%`.
- `dem_buoc(buoc, man: str, user: str, tu: datetime, den: datetime | None = None) -> tuple[int, int]` — `(so_lan, so_ngay)` theo bảng §4.4; `Góp ý trên màn` loại `tu_cam_nhan=1`; `Tạo chứng từ` đọc `tab<doctype_ct>` (`owner`, `creation`, `docstatus`).
- `buoc_dat(buoc, man, user, tu, den=None) -> bool` — `so_lan ≥ buoc.so_lan` và `so_ngay ≥ buoc.so_ngay`.
- `kich_ban_cua_man(screen_id: str) -> str | None` — kịch bản đang bật có `screen_id LIKE mau_like(man)`; cache theo request.

- [ ] Step 1: Test (tạo `Feedback Event` giả bằng insert trực tiếp, user test, xoá trong tearDown): mở màn khớp `chot-ton` và `Form/X/*`; trước `tu` không tính; `Bấm nút` cần `outcome='ok'`; `Gọi máy chủ` với `outcome='chan'` + message chứa "đều khớp sổ" tính khi `chap_nhan_chan="đều khớp sổ"`, không tính khi trống; `Tạo chứng từ` với `ToDo` (owner = user) nháp tính khi `docstatus_toi_thieu=0`; góp ý `tu_cam_nhan=1` không tính; `so_ngay=3` với sự kiện ở 2 ngày ⇒ False, 3 ngày ⇒ True; mẫu chứa `_` không khớp ký tự bất kỳ.
- [ ] Step 2: Chạy → FAIL. Step 3: Cài. Step 4: Chạy → PASS. Step 5: Commit.

### Task 3: Sổ điểm, cấp, huân chương (`diem.py`)

**Files:** Create `feedback_widget/diem.py`; Test `tests/test_kich_ban_diem.py`

**Interfaces — Produces:**
- `ghi_diem(user, diem: int, ly_do: str, khoa: str, nguon_doctype=None, nguon_name=None) -> bool` — insert; trùng khoá ⇒ False, không ném.
- `thu_hoi(khoa_goc: str) -> bool` — ghi dòng âm `Thu hồi`, khoá `Thu hồi|<khoa_goc>`, chỉ khi dòng gốc tồn tại.
- `tong_diem(user, chi_da_bao=False, tu=None) -> int`
- `cap(tong: int) -> str` — "Tập sự"/"Thành thạo"/"Key user"/"Đại sứ chuyển đổi số" theo ngưỡng cài đặt.
- `trao(user, huan_chuong: str, khoa: str, nguon_doctype=None, nguon_name=None) -> bool`
- `DANH_MUC_HUAN_CHUONG: dict[str, str]` (mã → "🚀 Người mở đường"…, đúng §8.3).
- `chua_bao(user) -> dict` — `{diem:[...], huan_chuong:[...], cap_truoc, cap_sau}` và `danh_dau_da_bao(user)`.
- `kiem_huan_chuong_ngay(luc=None)` — Chuyên cần (tuần ISO liên tiếp có điểm dương, khoá = tuần cuối chuỗi).

- [ ] Step 1: Test: ghi hai lần cùng khoá ⇒ một dòng; `thu_hoi` ⇒ tổng giảm, gọi lại không giảm nữa; `cap(99)`="Tập sự", `cap(100)`="Thành thạo", `cap(700)`="Đại sứ chuyển đổi số"; `chua_bao` báo lên cấp khi dòng mới vượt ngưỡng rồi rỗng sau `danh_dau_da_bao`; Chuyên cần trao khi 4 tuần liền, không trao khi 3.
- [ ] Step 2–5: FAIL → cài → PASS → commit.

### Task 4: Chấm tiến độ (`kich_ban.cham`)

**Files:** Modify `feedback_widget/kich_ban.py`; Test `tests/test_kich_ban_cham.py`

**Interfaces — Produces:**
- `tien_do(kich_ban: str, user: str, tao: bool = True, luc=None)` → Doc progress (tạo với `bat_dau=luc`).
- `ky_hien_tai(chang, luc) -> tuple[datetime, datetime] | None` — Ngày: [00:00, `gio_han`] nếu là ngày làm việc; Tuần: thứ Hai 00:00 → CN 23:59; None nếu không phải ngày làm việc.
- `cham(kich_ban: str, user: str, luc=None) -> list[dict]` — khoá dòng progress `FOR UPDATE`; với chặng Một lần theo `thu_tu` (chặng sau chỉ chấm khi chặng trước xong): ghi `buoc_xong`, `chang_xong`, điểm `Bước`/`Chặng` (khoá `Bước|KB|row|user`, `Chặng|KB|ma|user`); chặng Duy trì: kỳ đạt ⇒ `Kỳ duy trì` (khoá `Kỳ duy trì|KB|ma|<ngày đầu kỳ>|user`), cập nhật `chuoi`/`chuoi_dai_nhat`, lỡ kỳ trước ⇒ chuoi=1; huân chương 🎯 khi xong chặng cuối, 📅 khi chuỗi 10/30; rồi `_cap_nhat_nhiem_vu(kich_ban, user, luc)` (Assignee → Hoàn thành khi đạt `chang_muc_tieu` [Duy trì: chuoi ≥ `chuoi_muc_tieu`] + `Hoàn thành nhiệm vụ` + 🚀/`Người mở đường` nếu trong `gio_mo_duong`). Trả danh sách việc mới đạt.
- `cham_theo_man(user: str, screen_ids: list[str])` — enqueue-able, chấm các kịch bản khớp.
- `cham_tat_ca(luc=None)` — cron: mọi progress của kịch bản đang bật (Duy trì cần chấm cả người chưa giao).

- [ ] Step 1: Test: đủ bước chặng Làm quen ⇒ điểm bước + chặng, `chang_hien_tai` sang chặng kế; chấm 2 lần ⇒ không cộng đôi; bước xong vẫn giữ khi xoá Feedback Event; Duy trì: đạt T2, T3 ⇒ chuỗi 2; bỏ T4, đạt T5 ⇒ chuỗi 1, `chuoi_dai_nhat`=2; Chủ nhật ⇒ không kỳ; nhiệm vụ hoàn thành trong 48h ⇒ có `Người mở đường` + 🚀, sau 48h ⇒ không.
- [ ] Step 2–5.

### Task 5: Góp ý có ích / thành cải tiến + bù điểm

**Files:** Modify `hooks.py` (`doc_events["Feedback Comment"]` on_update/after_insert → `feedback_widget.diem.theo_gop_y`), `diem.py`; Create `patches/v1_8/bu_diem_gop_y.py`; Test `tests/test_kich_ban_gop_y.py`

**Interfaces — Produces:** `theo_gop_y(doc, method=None)` — `source='auto'` bỏ; `status` chuyển sang Resolved và `co_ich` chưa đặt tay ⇒ đặt `co_ich=1` (db_set); `thanh_cai_tien=1` ⇒ `co_ich=1`; ghi/thu hồi điểm theo §8.2; trao 🦅 (`tag_type='bug'`) / 💡 (`'idea'`) khi `thanh_cai_tien`; gọi `cham_theo_man(submitter_user, [screen_id])` nếu `kb_bat`. Patch bù: góp ý `source='user'` đã Resolved ⇒ `co_ich=1` + điểm, idempotent.

- [ ] Step 1: Test: Resolved lần đầu ⇒ +20; lưu lại ⇒ không thêm; bỏ `co_ich` ⇒ dòng `Thu hồi`; `thanh_cai_tien` + bug ⇒ +50 + 🦅; vé auto ⇒ 0; patch chạy 2 lần ⇒ điểm một lần.
- [ ] Step 2–5.

### Task 6: Giao kịch bản (`Feedback Mission`) + validate

**Files:** `doctype/feedback_mission/feedback_mission.py`, `doctype/feedback_playbook/feedback_playbook.py`; Test `tests/test_kich_ban_giao.py`

**Interfaces — Produces:**
- `FeedbackPlaybook.validate`: `man` không chồng kịch bản đang bật khác (khớp LIKE hai chiều); mỗi bước trỏ `chang` có thật; `duong_dan` bắt buộc. Nút "Phát lại hướng dẫn" = whitelisted `phat_lai_huong_dan(kich_ban)`.
- `FeedbackMission.validate`: hạn ≤ `retention_days − 7`; người nhận `enabled=1`; quyền mở màn (`duong_dan` dạng `/app/<page>` ⇒ Page `Has Role` ∩ roles người nhận, hoặc Page không khai vai; dạng DocType ⇒ `frappe.has_permission(dt, "read", user=u)`); không đạt ⇒ ghi `Feedback Event kind='chan'` chữ ký `kich-ban-giao-thieu-quyen` rồi `frappe.throw("<Tên> không mở được <màn> (cần vai …)")`.
- `FeedbackMission.on_update` (lần đầu): tạo progress cho mỗi người (mốc = `bat_dau`), Assignee `Đang làm`, gửi Notice "Được mời" qua `nhac.gui_nhac(..., loai="N0", bo_qua_tran=True)`.

- [ ] Step 1: Test: giao cho user tắt ⇒ throw; user không có vai Page ⇒ throw + có Event `chan`; hạn quá 83 ngày ⇒ throw; giao hợp lệ ⇒ progress + 1 Notice phạm vi Một người có `kich_ban`.
- [ ] Step 2–5.

### Task 7: Nhắc nhở (`nhac.py`)

**Files:** Create `feedback_widget/nhac.py`; Modify `hooks.py` (cron `*/15`: `feedback_widget.kich_ban.cham_tat_ca`, `feedback_widget.nhac.nhac_kich_ban`; daily: `feedback_widget.diem.kiem_huan_chuong_ngay`), `api/thong_bao.py` (`da_xem(thong_bao, da_bam=0, tam_hoan=0)`: ghi `tam_hoan`; nếu Notice có `kich_ban` ⇒ cập nhật progress: `da_bam=1` ⇒ `so_lan_bo_qua_lien=0`; ✕ ⇒ +1; `tam_hoan` ⇒ `nhac_tam_hoan_den` = đầu giờ làm ngày làm việc kế); Test `tests/test_kich_ban_nhac.py`

**Interfaces — Produces:**
- `trong_gio_lam(luc) -> bool`, `gio_lam_ke_tiep(luc) -> datetime`
- `gui_nhac(user, kich_ban, loai, tieu_de, noi_dung, duong_dan, nhiem_vu=None, luc=None, bo_qua_tran=False) -> str | None` — kiểm `kb_bat`, user enabled, giờ làm, tạm hoãn, dừng-sau-bỏ-qua, trần ngày/kịch bản (đếm Notice có `loai_nhac` của user hôm nay), một loại nhắc một lần/ngày/kịch bản; tạo Notice (`pham_vi='Một người'`, `het_han` = cuối giờ làm ngày làm việc kế, `kich_ban`, `loai_nhac`, `nhiem_vu`) + `day_ngay`.
- `nhac_kich_ban(luc=None) -> dict` — tính ứng viên N1–N5 cho mọi Assignee `Đang làm` của Mission `nhac=1`, sắp theo ưu tiên N4>N3>N5>N2>N1 rồi gửi; N4 quá hạn: Assignee→`Quá hạn`, một thẻ cho người nhận + gom thẻ tổng hợp cho `nguoi_giao` (một/ngày, gồm ai, bước kẹt, số lần nhắc, ai đã bỏ qua ≥3). Lời mẫu theo bảng §7.
- `meo_tai_cho(kich_ban, user, screen_id, luc=None) -> list[dict]` — N6 (≥3 `chan` cùng chữ ký trong 1h trên màn ⇒ mẹo khớp hoặc mời góp ý) và N7 (`huong_dan='Đang xem'`), không qua trần.

- [ ] Step 1: Test (luc cố định): N1 sau 24h chưa mở; N2 khi 50% thời gian, 0/3 bước; N3 còn 20h; N4 quá hạn ⇒ 2 thẻ (người nhận + người giao); ngoài giờ ⇒ không gửi; trần 3/ngày giữ ưu tiên; chạy 2 lần ⇒ không đôi; `da_xem(tam_hoan=1)` ⇒ không nhắc tới giờ làm kế; 3 lần ✕ ⇒ dừng + người giao được báo; N5 chỉ cho người được giao.
- [ ] Step 2–5.

### Task 8: API cho widget (`api/kich_ban.py`) + chấm sau lô sự kiện

**Files:** Create `feedback_widget/api/kich_ban.py`; Modify `api/su_kien.py` (sau commit: nếu `kb_bat` ⇒ `frappe.enqueue("feedback_widget.kich_ban.cham_theo_man", queue="short", user=..., screen_ids=[...], deduplicate không dùng)`), `api/feedback.py` `extend_bootinfo` (+`kb_bat`); Test `tests/test_kich_ban_api.py`

**Interfaces — Produces (whitelisted, user = session user):**
- `cua_toi(screen_id: str) -> dict | None` — `{kich_ban, ten, ly_do, duong_dan, huong_dan:{tu_bat: bool, trang_thai, the, cac_the:[{tieu_de,noi_dung,chi_vao,vi_tri}]}, chang:[{ma,ten,loai,xong,hien_tai,buoc:[{mo_ta,loai,xong,dem,can,diem}]}], duy_tri:{...}, nhiem_vu:{het_han,chang_muc_tieu}|None, meo:[...] (meo_tai_cho), chua_bao: chua_bao(user)}`; chấm trước khi trả. `tu_bat` theo §5.1 (đếm `session_id` khác nhau trước `Playbook.creation`… hoặc trước lúc tạo progress < `phien_da_quen`).
- `huong_dan(kich_ban: str, trang_thai: str, the: int = 0) -> dict`
- `cam_nhan(kich_ban: str, chang: str, y: str, chu: str = "") -> dict` — §6.4.
- `da_bao() -> dict` — `danh_dau_da_bao`.
- `thanh_tich() -> dict` — `{ten, cap, tong, nguong_ke, huan_chuong:{ma: so_lan}, kich_ban:[...]}`.
- `bang_vang(ky: str = "thang", cong_ty: str | None = None) -> dict` — `{cong_ty_cua_toi, cac_cong_ty, hang:[{ten, cap, diem, huan_chuong}]}`; không email; bỏ `khong_xep_hang`, điểm ≤ 0; công ty theo §6.6.
- `kb_bat=0` ⇒ mọi hàm trả None/rỗng.

- [ ] Step 1: Test: `cua_toi` trả `tu_bat=True` cho người mới, False cho người có 3 phiên trước; `cam_nhan("👍")` không tạo Comment, có điểm 1 lần; `"👎"` tạo Comment `tu_cam_nhan=1`; `bang_vang` không có email/người 0 điểm/khong_xep_hang, lọc công ty; `kb_bat=0` ⇒ None.
- [ ] Step 2–5.

### Task 9: Giao diện `kich_ban_the.js` + nút "Để mai"

**Files:** Create `public/js/kich_ban_the.js`; Modify `feedback_widget.bundle.js` (import + `dangKyKichBan()`: khi đổi route gọi `cua_toi(currentRoute())` (≤1 lần/route/30s), đăng ký 3 lối vào order 20/40/50 chỉ khi `boot.feedback_widget.kb_bat`), `thong_bao_the.js` (Notice có `loai_nhac` ⇒ thêm nút "Để mai" gọi `da_xem(..., tam_hoan=1)`), test `tests/test_boot_payload.py` vẫn xanh.

**Interfaces — Produces:** `window.FeedbackPlaybook = { nap(duLieu), moMucTieu(), moHuongDan(tuDau), moThanhTich(), moBangVang() }`. Thẻ hướng dẫn: thử từng selector trong `chi_vao` (tách `;`), lấy phần tử hiển thị đầu tiên; không có ⇒ thẻ giữa màn + `FeedbackWidget` đẩy event `{kind:'loi', screen_id, message:'kich-ban-chi-vao-mat:<KB>:<thu_tu>'}`. Ô "Gửi một góp ý" ⇒ `FeedbackWidget.toggle(true)`. Chúc mừng gộp từ `chua_bao`, rồi `da_bao()`. Hỏi cảm nhận khi `chang` vừa xong có `hoi_cam_nhan` (cờ trong `chua_bao` mục `Chặng`).

- [ ] Step 1: `bench build --app feedback_widget`; `systemctl --user restart hts-mirror`.
- [ ] Step 2: Script Chrome thật `tests/nghiem_thu_kich_ban.mjs` (theo mẫu `nghiem_thu_prod_thong_bao.mjs`, chạy trên mirror rồi prod): user thử mới mở `/app/chot-ton` ⇒ thẻ hướng dẫn 1/N hiện, viền đúng phần tử; selector hỏng ⇒ thẻ chữ + event `loi`; menu có 🎯/🏅/🏆; thẻ mục tiêu liệt kê bước; Notice nhắc có nút "Để mai" và bấm thì biến mất; 390px và 1366px; console 0 lỗi.
- [ ] Step 3: Commit.

### Task 10: Báo cáo quản trị

**Files:** Create `feedback_widget/feedback_widget/report/tien_do_kich_ban/` và `report/man_chua_ai_dung/` (Script Report, System Manager); Test `tests/test_kich_ban_bao_cao.py`

**Interfaces — Produces:** cột §6.7; "% nhắc có tác dụng" = Notice `loai_nhac` của cặp có ≥1 `Feedback Event` của user khớp màn trong 24h sau `creation` / tổng Notice; bộ lọc `kich_ban`, `user`, `dang_ket` (có nhắc 24h không hành động). Đếm điểm/khớp đi qua `kich_ban.py`/`diem.py`, không SQL riêng cho luật.

- [ ] Step 1–5: test số liệu trên dữ liệu giả → cài → PASS → commit.

### Task 11: Lập 4 kịch bản đầu + quy trình ra bản

**Files:** Create `scripts/lap_kich_ban.py` (đọc JSON khai kịch bản + giao; idempotent theo `man`; `--apply`), `scripts/kich_ban/hts_dot1.json` (4 kịch bản §12 với endpoint đã đối chiếu, hướng dẫn 3–4 thẻ mỗi màn viết từ chính màn, mẹo cho các câu chặn của `chot_ton`/`huy_hang`); Modify `~/.claude/skills/feedback-announce/SKILL.md` (bước "lập/cập nhật kịch bản" + đóng vé phải đặt `tag_type` và `thanh_cai_tien`), và `feedback-ducan.sh dong`/công cụ đóng vé nếu có tham số.

- [ ] Step 1: Đọc DOM thật của 4 màn (mirror; `Doi Soat Cong No NCC`/`hop-thu` đọc trên prod qua phiên ngắn hạn vì `tro_ly_ke_toan` local đi sau 26 commit) để lấy selector.
- [ ] Step 2: Chạy `lap_kich_ban.py` khô trên mirror ⇒ in kế hoạch; `--apply` trên mirror ⇒ 4 kịch bản + 3 người được giao; validate quyền qua.
- [ ] Step 3: Commit.

### Task 12: Rà nợ, deploy, bật, nghiệm thu prod

- [ ] Step 1: Rà nợ §15 của spec, ghi kết quả vào `docs/specs/2026-10-20-kich-ban-man-design.md` §15 (fix/defer/delete) và báo chủ đầu tư.
- [ ] Step 2: Cả suite `--app feedback_widget` xanh trên mirror.
- [ ] Step 3: Push `develop`; trên VPS: `git -C apps/feedback_widget pull`, migrate `erp.htsfood.com` VÀ `hkd688.vn` (chung app), `bench build --app feedback_widget`, restart web+workers (giờ vắng), `bench clear-cache`, `touch sites/assets/assets.json`. Đo thời gian ALTER chỉ mục.
- [ ] Step 4: Bật `kb_bat=1` CHỈ erp.htsfood.com; chạy `lap_kich_ban.py --apply` qua `prod-probe.sh`.
- [ ] Step 5: Chạy `nghiem_thu_kich_ban.mjs` trên prod bằng phiên ngắn hạn; đo `cham()` < 50 ms, cron nhắc < 5 s.
- [ ] Step 6: Cập nhật CLAUDE.md của bench (Current Priorities), memory, session-last.
