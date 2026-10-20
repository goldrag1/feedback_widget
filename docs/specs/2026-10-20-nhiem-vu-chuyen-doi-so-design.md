# Nhiệm vụ chuyển đổi số — giao việc dùng thử, chấm tự động, huân chương danh dự

Ngày: 20/10/2026 · App: `feedback_widget` · Site bật đầu tiên: `erp.htsfood.com`
Chủ đầu tư: anh Long · Trạng thái: CHỜ DUYỆT

## 1. Vì sao

Mỗi tuần HTS ra 5–10 chức năng mới. Phía người dùng, số đo trên prod cho thấy (20/10/2026):

- 35 người dùng ERP trong 30 ngày, 376.838 lượt thao tác, nhưng **góp ý gõ tay chỉ 16 cái
  trong tháng 6, rồi 1–3 cái mỗi tháng** từ tháng 8. Trong 90 ngày chỉ 3 người ngoài chủ đầu tư
  từng gửi góp ý.
- `Feedback Notice` đã gửi 7 thông báo, tất cả gửi cho một người, **0 lượt bấm "Xem thử"**.
- «Chốt tồn hằng ngày» và «Hủy hàng tồn» ra ngày 19/10: **chỉ chủ đầu tư mở**, không nhân viên
  kho nào. «So giá hệ thống» có 2 người mở. «Đề nghị thanh toán» là ngoại lệ: 4 người Hà Lê dùng
  thật trong 5 ngày.

Vấn đề là không ai được **giao** việc thử chức năng mới, và người góp ý không nhận lại được gì.
Ở đây ta không thiếu hạ tầng: sổ `Feedback Event` đã ghi từng màn, từng nút và từng lệnh gọi máy
chủ kèm kết quả, nên ta chấm được "đã dùng thật chưa" mà không cần ai tự khai.

## 2. Mục tiêu, không làm, phản mục tiêu

**Mục tiêu**
1. Mỗi chức năng ra bản đều có **nhiệm vụ** giao cho đúng key user, gồm vài bước cụ thể. Hệ thống
   tự chấm từ dữ liệu.
2. Key user nhận **điểm, cấp bậc, huân chương** khi dùng thật và khi góp ý có ích. Đây là thưởng
   ẢO, mang tính danh dự (chủ đầu tư chốt 20/10).
3. **Bảng vàng ai cũng xem được** (chủ đầu tư chốt 20/10).
4. Chủ đầu tư thấy ngay chức năng nào đã có người dùng, chức năng nào chưa ai đụng.

**Không làm (lượt này)**
- Thưởng tiền, đổi điểm lấy quà, tích hợp lương.
- Đẩy Telegram/Zalo. Có thể thêm sau, khi trong app đã chạy được.
- Cho nhân viên tự tạo nhiệm vụ. Chỉ quản trị (System Manager) tạo.
- Giao nhiệm vụ theo VAI. Lượt này chỉ giao theo NGƯỜI, vì chủ đầu tư giao theo tên.

**Phản mục tiêu** (chạy đúng kỹ thuật mà vẫn là thất bại)
- **Thưởng cho số lượt bấm.** Chị Điệp có 109.703 lượt/30 ngày, nhưng con số đó không nói gì về
  việc chị có dùng chức năng mới hay không. Điểm chỉ đến từ việc thỏa một BƯỚC đã khai, hoặc từ
  góp ý được duyệt.
- **Góp ý rác để lấy điểm.** Gõ góp ý không được điểm. Điểm chỉ có khi góp ý được đánh dấu "có
  ích" hoặc "thành cải tiến".
- **Nhiệm vụ không ai nhìn thấy.** Nếu người được giao không thấy nhiệm vụ trong 1 ngày thì coi như
  hỏng. Vì vậy nhiệm vụ mới phải đi qua kênh phao realtime đã có (chấm đỏ trên nút 💬 + thẻ).
- **Bảng vàng làm xấu mặt người ít dùng.** Chỉ hiện người CÓ điểm, không xếp hạng ai 0 điểm, không
  có cột "bị phạt".

## 3. Khái niệm (đúng chữ hiện trên giao diện)

| Chữ | Nghĩa |
|---|---|
| **Nhiệm vụ** | Một chức năng cần dùng thử. Có tiêu đề, lý do, đường dẫn mở thẳng, hạn, người nhận, và 2–5 bước |
| **Bước** | Một điều kiện máy chấm được: mở màn X / bấm nút Y / ghi trên máy chủ Z / tạo chứng từ / gửi góp ý trên màn X; kèm số lần và số NGÀY khác nhau tối thiểu |
| **Điểm** | Ghi vào sổ điểm, chỉ thêm, không sửa |
| **Cấp** | Tập sự → Thành thạo → Key user → Đại sứ chuyển đổi số, tính theo tổng điểm |
| **Huân chương** | Danh hiệu trao theo luật, nhận được nhiều lần (×N) |
| **Bảng vàng** | Xếp hạng điểm theo tháng và từ trước tới nay |

## 4. Mô hình dữ liệu (tất cả trong `feedback_widget`, module Feedback Widget)

### 4.1 `Feedback Mission` (Nhiệm vụ), đặt tên `NV-.YY.MM.-.####`
| Trường | Kiểu | Ghi chú |
|---|---|---|
| `tieu_de` | Data, bắt buộc | "Chốt tồn kho hằng ngày trên điện thoại" |
| `ly_do` | Small Text | Một câu: vì sao nên dùng. Hiện cho người nhận |
| `duong_dan` | Data | `/app/chot-ton`. Bắt buộc, vì không có đường dẫn là mời vào ngõ cụt |
| `project` | Data | Như các DocType khác của app |
| `dang_bat` | Check | Mặc định 1 |
| `bat_dau` | Datetime | Mặc định lúc tạo. Sự kiện trước mốc này KHÔNG tính |
| `het_han` | Datetime | Mặc định +7 ngày. Validate: `het_han − bat_dau ≤ retention_days − 7` (xem §8) |
| `diem_hoan_thanh` | Int | Mặc định lấy từ Cài đặt (30) |
| `nguon` | Data | Commit/tính năng sinh ra nhiệm vụ, ví dụ `my_custom_app 96cc715` |
| `nguoi_nhan` | Table → `Feedback Notice User` (dùng lại) | Ít nhất 1 người |
| `buoc` | Table → `Feedback Mission Step` | 1–6 bước |

### 4.2 `Feedback Mission Step` (bảng con)
| Trường | Kiểu | Ghi chú |
|---|---|---|
| `mo_ta` | Data, bắt buộc | Chữ hiện cho người dùng: "Ghi một phiếu chốt tồn" |
| `loai` | Select | `Mở màn` · `Bấm nút` · `Gọi máy chủ` · `Tạo chứng từ` · `Góp ý trên màn` |
| `man` | Data | Mẫu `screen_id`, cho phép `*` (ví dụ `Form/Doi Soat Cong No NCC/*`) |
| `nut` | Data | Mẫu `action_id`, cho phép `*` (ví dụ `hop-thu::+ Tạo đơn mua`) |
| `endpoint` | Data | Khớp chính xác `Feedback Event.endpoint` |
| `doctype_ct` | Link → DocType | Dùng cho `Tạo chứng từ` |
| `docstatus_toi_thieu` | Select 0/1 | Dùng cho `Tạo chứng từ`: 0 = nháp cũng tính, 1 = phải ghi sổ |
| `chap_nhan_chan` | Data | Chỉ dùng cho `Gọi máy chủ`: một đoạn chữ. Lần gọi bị CHẶN mà thông điệp chứa đoạn này vẫn tính là xong (xem §8.2) |
| `so_lan` | Int, mặc định 1 | Số lần khớp tối thiểu |
| `so_ngay` | Int, mặc định 1 | Số NGÀY khác nhau tối thiểu (chốt tồn hằng ngày → 3) |
| `diem` | Int | Mặc định từ Cài đặt (10) |

Luật khớp (một định nghĩa duy nhất, trong `feedback_widget/nhiem_vu.py`):

| `loai` | Nguồn | Điều kiện |
|---|---|---|
| Mở màn | `Feedback Event` | `user`, `ts ≥ bat_dau`, `screen_id LIKE man` |
| Bấm nút | `Feedback Event` | như trên + `action_id LIKE nut`, `outcome='ok'` |
| Gọi máy chủ | `Feedback Event` | `endpoint = endpoint`, và `outcome='ok'` HOẶC (`outcome='chan'` và `message LIKE %chap_nhan_chan%`); cộng `man` nếu có khai. `ok` = máy chủ trả 2xx; mọi `frappe.throw` ra 417 nên không lọt thành `ok` |
| Tạo chứng từ | bảng `tab<doctype_ct>` | `owner = user`, `creation ≥ bat_dau`, `docstatus ≥ docstatus_toi_thieu`, `docstatus != 2` |
| Góp ý trên màn | `Feedback Comment` | `source='user'`, `submitter_user = user`, `ts ≥ bat_dau`, `screen_id LIKE man` |

`*` chuyển thành `%`. Các ký tự `%` và `_` có sẵn trong mẫu phải được escape. Số ngày đếm bằng
`COUNT(DISTINCT DATE(ts))`.

> **Why `Tạo chứng từ` đọc thẳng CSDL:** `Feedback Event` do TRÌNH DUYỆT gửi lên, nên ai biết mở
> devtools là giả được. Thưởng ở đây chỉ là danh dự nên rủi ro thấp, nhưng bước "đã ghi thật" thì
> có nguồn sự thật không giả được (chứng từ trong sổ), và ta dùng nguồn đó. Các bước "mở / bấm"
> vẫn đọc sổ sự kiện, vì không có nguồn nào khác.

### 4.3 `Feedback Mission Progress` (tiến độ từng người), mỗi cặp (nhiệm vụ, người) một dòng
`nhiem_vu` (Link), `user` (Link User), `trang_thai` (`Đang làm` / `Hoàn thành` / `Hết hạn`),
`buoc_xong` (Code JSON: `{step_row_name: ts_hoàn_thành}`), `hoan_thanh_luc` (Datetime).
Có unique index `(nhiem_vu, user)`. Dòng được tạo cùng lúc với nhiệm vụ.
**Bước đã xong thì giữ nguyên, kể cả khi sau này sổ sự kiện bị dọn** (§8).

### 4.4 `Feedback Point` (sổ điểm), chỉ thêm
`user`, `diem` (Int, có thể âm), `ly_do` (Select: `Bước` · `Nhiệm vụ` · `Người mở đường` ·
`Góp ý có ích` · `Góp ý thành cải tiến` · `Thu hồi`), `nguon_doctype`, `nguon_name`, `khoa`
(Data, unique). `khoa` có dạng `"<ly_do>|<nguon_name>|<step?>|<user>"`, nhờ đó chấm lại bao nhiêu
lần cũng không cộng đôi.

### 4.5 `Feedback Badge Award` (huân chương đã trao)
`user`, `huan_chuong` (Select, danh mục ở §6), `luc`, `nguon_doctype`, `nguon_name`, `khoa` (unique), `da_bao` (Check).

### 4.6 Thêm vào `Feedback Comment`
`co_ich` (Check, "Góp ý có ích") và `thanh_cai_tien` (Check, "Dẫn tới cải tiến đã ra bản").
Bật `thanh_cai_tien` thì tự bật `co_ich`.

### 4.7 Thêm vào `Feedback Settings`
`nv_bat` (Check, công tắc tổng, **mặc định 0**) · `diem_buoc` 10 · `diem_nhiem_vu` 30 ·
`diem_mo_duong` 20 · `gio_mo_duong` 48 · `diem_co_ich` 20 · `diem_cai_tien` 50 ·
`nguong_thanh_thao` 100 · `nguong_key_user` 300 · `nguong_dai_su` 700 ·
`tuan_chuyen_can` 4 · `khong_xep_hang` (Table → User; mặc định Administrator + tài khoản chủ đầu tư).

> **Why ngưỡng nằm ở Cài đặt mà luật huân chương nằm trong mã:** mỗi huân chương là một luật có
> logic riêng (rules-configurability: luật có logic là mã, con số là dữ liệu). Chỉnh điểm hay ngưỡng
> không cần deploy.

## 5. Chấm điểm

### 5.1 Khi nào chấm
1. **Cron 15 phút** (`tac_vu.cham_nhiem_vu`): chấm mọi dòng `Đang làm` của nhiệm vụ đang bật và còn hạn.
2. **Khi người dùng mở tab Nhiệm vụ**: `api.nhiem_vu.cua_toi()` chấm riêng người đó trước khi trả
   kết quả, nên vừa làm xong là thấy ngay.
3. **`Feedback Comment` after_insert / on_update**: chấm bước "Góp ý trên màn" của người gửi, và
   tính điểm góp ý khi `co_ich` / `thanh_cai_tien` / `status` đổi.

Ba đường này gọi chung MỘT hàm `cham(nhiem_vu, user)`. Cron và đường mở tab có thể chạy cùng lúc,
nên ghi điểm dựa vào `khoa` unique (insert gặp trùng thì bỏ qua) và cập nhật tiến độ dưới
`SELECT … FOR UPDATE` trên dòng progress.

### 5.2 Điểm
| Sự kiện | Điểm | `khoa` |
|---|---|---|
| Xong một bước | `diem` của bước | `Bước|NV|step|user` |
| Xong cả nhiệm vụ | `diem_hoan_thanh` | `Nhiệm vụ|NV|user` |
| Xong trong `gio_mo_duong` giờ kể từ `bat_dau` | +`diem_mo_duong` + huân chương 🚀 | `Người mở đường|NV|user` |
| `co_ich` bật (tự bật khi `status → Resolved`, trừ khi người duyệt đã tắt tay) | +`diem_co_ich` | `Góp ý có ích|FB|user` |
| `thanh_cai_tien` bật | +`diem_cai_tien` | `Góp ý thành cải tiến|FB|user` |
| Tắt `co_ich` / `thanh_cai_tien` sau khi đã cộng | dòng âm, `ly_do=Thu hồi` | `Thu hồi|<khoa gốc>` |

`co_ich` chỉ tự bật khi `status` CHUYỂN sang Resolved (so `doc.has_value_changed('status')`), không bật khi lưu lại một vé đã Resolved từ trước.
**Bù một lần lúc bật** *(quyết định của Claude, anh có thể bác)*: một patch chạy một lần, bật `co_ich` và ghi +`diem_co_ich` cho các góp ý `source='user'` đã Resolved trước ngày bật (prod 20/10: 23 góp ý gõ tay, phần lớn của tháng 6). Người góp ý sớm vì vậy có điểm ngay ngày đầu. Patch không bật `thanh_cai_tien`.
Góp ý `source='auto'` (vé máy) không bao giờ được điểm. Góp ý của người nằm trong `khong_xep_hang`
vẫn được ghi điểm, chỉ không hiện trên bảng vàng.

> **Why tự bật `co_ich` khi Resolved:** nếu điểm góp ý đợi người duyệt tick tay thì sẽ không ai
> tick, và đường thưởng chết y như kênh thông báo hiện nay (0 lượt bấm). Người duyệt vẫn tắt được.

### 5.3 Hết hạn
Quá `het_han` mà chưa xong thì `trang_thai = Hết hạn`. Bước đã xong vẫn giữ điểm. Không trừ điểm.

## 6. Cấp bậc và huân chương

**Cấp** tính theo tổng `Feedback Point.diem` của người đó: < `nguong_thanh_thao` là Tập sự,
< `nguong_key_user` là Thành thạo, < `nguong_dai_su` là Key user, còn lại là Đại sứ chuyển đổi số.
Lên cấp thì hiện thẻ chúc mừng một lần (§7.3).

**Huân chương** (danh mục trong mã, mỗi huân chương một hàm kiểm tra):
| | Tên | Luật |
|---|---|---|
| 🚀 | Người mở đường | Xong nhiệm vụ trong `gio_mo_duong` giờ đầu |
| 🦅 | Mắt tinh | Góp ý `tag_type='bug'` được bật `thanh_cai_tien` |
| 💡 | Người gợi ý | Góp ý `tag_type` khác `bug` được bật `thanh_cai_tien` |
| 🔥 | Chuyên cần | `tuan_chuyen_can` tuần ISO liên tiếp, tuần nào cũng có ≥ 1 dòng điểm dương |
| 🏅 | Hoàn thành «tên nhiệm vụ» | Mỗi nhiệm vụ xong được một huy hiệu riêng, hiện trong hồ sơ |

`tag_type` gần như luôn trống (prod: 20/23 góp ý, vì `hien_tag=0`). Vì vậy **người đóng vé phân loại**: lúc đóng vé bằng `feedback-announce` / `dong`, người đóng (thường là Claude) đặt `tag_type` (`bug` / `idea`) cùng lúc với `thanh_cai_tien`. Vé thành cải tiến mà `tag_type` trống thì không trao 🦅/💡 (chỉ có điểm). *(Quyết định của Claude.)*

Chuyên cần được kiểm ở cron hằng ngày và trao một lần cho mỗi chuỗi. `khoa` là tuần kết thúc chuỗi.

## 7. Giao diện

Theo quy ước của app: phần vẽ nằm ở **tệp riêng** `public/js/nhiem_vu_the.js`, khai
`window.FeedbackMissions`, giống `thong_bao_the.js` (vì core.js do phiên khác giữ). Chữ trên giao
diện bằng tiếng Việt, ô bấm ≥ 44px. Phải dùng được trên điện thoại, vì Lâm và kho chủ yếu dùng điện thoại.

### 7.1 Lối vào
- Menu của nút 💬 thêm mục **"🏅 Nhiệm vụ của tôi"**, có badge là số nhiệm vụ đang làm.
- Nhiệm vụ mới: tạo kèm một `Feedback Notice` phạm vi `Một người` cho từng người nhận, đường dẫn
  mở thẳng tab Nhiệm vụ. Dùng lại phao realtime `SU_KIEN` để chấm đỏ hiện ngay, không cần F5.
- Phải chạy được ở mọi nơi widget đang chạy: desk, trang Frappe Page (chot-ton, huy-hang,
  hop-thu), màn mobile www, và desk React (`react_desk`). Builder phải đo từng chỗ (§11).

### 7.2 Tab "Nhiệm vụ" (bảng trượt của widget)
```
 Lâm · Thành thạo · 140 điểm   ▓▓▓▓▓▓░░░░ 160 điểm nữa lên Key user
 🚀×1 🔥×0 🦅×0 💡×0

 ĐANG LÀM
 ┌ Chốt tồn kho hằng ngày trên điện thoại        còn 5 ngày
 │ Vì sao: đếm xong là sổ khớp, khỏi gửi số qua Zalo.
 │ ✓ Mở trang Chốt tồn                              +10
 │ ◐ Ghi phiếu chốt tồn 3 ngày khác nhau (1/3)      +10
 │ ○ Gửi một góp ý ngay trên trang                  +10
 │ Xong cả nhiệm vụ: +30 · trong 48 giờ: +20 🚀
 └ [ Mở trang ]
 ĐÃ XONG (thu gọn) …
 [ Bảng vàng ]
```
"Gửi một góp ý" phải có nút mở thẳng ô góp ý đã gắn đúng màn đó.

### 7.3 Chúc mừng
Khi lần chấm sau phát hiện bước, nhiệm vụ, huân chương hoặc cấp mới chưa báo thì hiện một thẻ
(cùng kiểu `thong_bao_the`), ví dụ: «+30 điểm — Hoàn thành "Chốt tồn". Huân chương 🚀 Người mở đường».
Cờ "đã báo" lưu ở `Feedback Point.da_bao` và `Feedback Badge Award.da_bao` để không báo lặp trên máy khác. **Lên cấp không cần lưu riêng:** cấp TRƯỚC = cấp của tổng điểm các dòng `da_bao=1`, cấp SAU = cấp của tổng mọi dòng; khác nhau thì thẻ chúc mừng thêm dòng lên cấp, rồi đánh dấu các dòng đó `da_bao=1`. *(Quyết định của Claude.)*

### 7.4 Bảng vàng
- Hai tab: **Tháng này** (điểm phát sinh trong tháng) và **Từ trước tới nay**.
- Bộ lọc công ty: mặc định là công ty của người xem, có lựa chọn "Tất cả". Công ty của một người
  lấy lần lượt từ `Employee.company` theo `user_id`, rồi User Permission `Company` nếu chỉ có đúng
  một, rồi công ty mặc định toàn cục. *(Quyết định của Claude: Ngân, Huyền và Huỳnh không có
  Employee, nên phải có đường dự phòng.)*
- Cột: hạng, tên (`full_name`), cấp, điểm, huân chương. Chỉ hiện người có điểm > 0.
  Không hiện người trong `khong_xep_hang`.
- Ai đăng nhập cũng xem được (chủ đầu tư chốt). API `bang_vang(ky, cong_ty)` không lộ email,
  chỉ trả tên hiển thị.

### 7.5 Phía quản trị (System Manager)
- Form `Feedback Mission` trên desk. Lưu xong thì tự tạo dòng tiến độ và thông báo.
- Script Report **"Tiến độ nhiệm vụ"**: mỗi dòng một cặp (nhiệm vụ, người), gồm bước xong/tổng,
  trạng thái, ngày xong, lần cuối mở màn. Lọc theo nhiệm vụ hoặc người. Đây là câu trả lời cho
  câu hỏi "chức năng nào chưa ai dùng".
- Form `Feedback Comment` hiện hai ô `co_ich` và `thanh_cai_tien`.

## 8. Khi nào khác? (trường hợp biên)

1. **Sổ sự kiện bị dọn** (`don_so_cu`, `retention_days` mặc định 90). Bước đã xong được lưu trong
   progress nên không mất. Validate hạn nhiệm vụ ≤ `retention_days − 7` để một bước đang đếm dở
   không bị dọn mất nửa.
2. **Chốt tồn không tạo phiếu khi mọi dòng khớp sổ.** `chot_ton.create` khi đó `frappe.throw("Tại
   thời điểm chốt, mọi mặt hàng đã đếm đều khớp sổ — không cần ghi phiếu.")`. Hôm đó Lâm đã làm
   đúng việc, nên bước này là `Gọi máy chủ` `…chot_ton.create` với `chap_nhan_chan = "đều khớp sổ"`.
   Builder phải xác nhận trên mirror rằng lần chặn ấy vào sổ với `kind='chan'` và `message` chứa đúng
   câu đó. Thêm test.
   **Không dùng `Tạo chứng từ` khi doctype quá chung**: `huy_hang.create` sinh `Stock Entry` thường,
   và Huyền (Stock Manager) tạo Stock Entry ở chỗ khác cũng sẽ khớp. Chỉ dùng `Tạo chứng từ` cho
   doctype mà CHỈ màn đó sinh ra (như `Doi Soat Cong No NCC`).
3. **Người nhận bị tắt tài khoản** (đã có: `thanhhuyen.icloud2001` bị tắt, tài khoản thật là
   `thanhhuyen.iclould2001`). Validate `nguoi_nhan` phải `enabled=1`. Bỏ qua người bị tắt khi chấm
   và khi xếp hạng.
4. **Người nhận không có quyền mở màn.** Validate khi lưu nhiệm vụ: đường dẫn là Page thì kiểm
   `Has Role` của Page; là DocType thì kiểm `has_permission(read)` của người nhận. Không đạt thì
   CHẶN và nói rõ "Huyền không mở được trang huy-hang (cần vai Stock User)". Đây là cổng chặn nên
   phải ghi sổ khi chặn (rules-code-guards).
5. **`action_id` có số động** (`hop-thu::Chưa xong 3`, `hop-thu::38 Đơn mua chờ hàng 327.463.000`).
   Với nút có nhãn đổi theo dữ liệu thì dùng `*` hoặc dùng `Gọi máy chủ`. Hướng dẫn ở §10.
6. **Cùng một người được giao hai nhiệm vụ trên cùng một màn** (Ngân: hop-thu và Đối soát NCC là
   hai màn khác nhau nên không sao, nhưng có thể xảy ra). Mỗi nhiệm vụ chấm độc lập. Một góp ý được
   tính cho mọi nhiệm vụ có mẫu `man` khớp. Chấp nhận.
7. **Chủ đầu tư tự làm thử nhiệm vụ.** Vẫn chấm và vẫn ghi điểm, chỉ ẩn khỏi bảng vàng.
8. **Sửa bước sau khi đã có người làm.** Bước đã xong giữ nguyên điểm. Bước mới thêm thì chấm từ
   `bat_dau`. Bước bị xoá thì điểm đã cộng không thu lại.
9. **Công tắc `nv_bat = 0`.** Cron không chạy, menu không hiện, API trả rỗng. Dữ liệu giữ nguyên.
10. **Mất sự kiện.** `usage_sample_pct` trên prod = 100 (đo 20/10), nhưng có trần `max_events_per_minute` = 120 mỗi trình duyệt, nên người bấm rất nhanh có thể mất vài sự kiện `Mở màn`/`Bấm nút`. Chấp nhận, vì mở màn sinh nhiều sự kiện và bước "đã ghi thật" dùng nguồn máy chủ. Không vượt trần cho nhiệm vụ.
11. **`Feedback Event.ts` là lúc máy chủ NHẬN lô**, không phải lúc bấm. Điện thoại gửi lô trễ qua nửa đêm có thể lệch `so_ngay` một ngày. Chấp nhận.
12. **Site không có `tabEmployee`** (feedback_widget có thể cài trên site không có HRMS). Phần dự
    phòng công ty phải chịu được việc thiếu bảng đó.

## 9. Hiệu năng

`Feedback Event` có **611.658 dòng** và **chỉ có chỉ mục trên `name` và `creation`** (đo 20/10).
Truy vấn theo `user` + `ts` hiện đang quét toàn bảng, nên phải thêm patch tạo chỉ mục ghép
`(user, ts)`. Ngưỡng chấp nhận: một lượt `cham()` của một người với một nhiệm vụ 4 bước chạy
< 50 ms trên prod. Đo trước và sau khi thêm chỉ mục. `ALTER` trên 600k dòng InnoDB chạy online,
mất vài giây. Nếu chạy trong giờ làm việc thì báo trước.

## 10. Lập nhiệm vụ lúc ra bản (đổi quy trình, không chỉ đổi mã)

Bước cuối của mỗi lượt ship hiện nay là `feedback-announce`. Thêm bước **"lập nhiệm vụ"** vào skill
đó, viết lại cả `SKILL.md`: chọn người nhận từ số đo (người đang làm đúng việc ấy, hoặc chủ đầu tư
chỉ định), khai 2–4 bước dùng endpoint hoặc chứng từ, tránh nhãn nút có số. Có kịch bản
`scripts/lap_nhiem_vu.py` chạy qua `prod-probe.sh`. Nếu không sửa skill thì gamify sẽ chết sau đợt
nhiệm vụ đầu tiên, vì không ai lập nhiệm vụ mới.

## 11. Bốn nhiệm vụ đầu tiên (chủ đầu tư chỉ định 20/10)

Quyền đã đo trên prod 20/10: cả ba người đều mở được màn của mình.

| Nhiệm vụ | Người nhận | Bước (đề xuất, builder đối chiếu lại tên endpoint thật) |
|---|---|---|
| Chốt tồn kho hằng ngày | Lâm `hanoi.hamona@gmail.com` (Kho HTS, Stock Manager) | Mở màn `chot-ton` · Gọi `my_custom_app.my_custom_app.chot_ton.create`, `so_ngay=3` (xem §8.2) · Góp ý trên `chot-ton` |
| Hủy hàng tồn có lý do | Huyền KT `thanhhuyen.iclould2001@gmail.com` (Stock Manager) | Mở màn `huy-hang` · Gọi `my_custom_app.my_custom_app.huy_hang.create` · Góp ý trên `huy-hang` |
| Đối soát công nợ nhà cung cấp | Ngân `sale11.hamona@gmail.com` (Purchase/Accounts User) | Mở `List/Doi Soat Cong No NCC/*` · Tạo chứng từ `Doi Soat Cong No NCC` · Góp ý trên `Form/Doi Soat Cong No NCC/*` |
| Hộp thư Zalo/Messenger | Ngân | Mở `hop-thu` · Gọi `tro_ly_ke_toan.hop_thu.api.gui` · Bấm `hop-thu::+ Tạo đơn mua` hoặc gắn đối tác · Góp ý trên `hop-thu` |

`Doi Soat Cong No NCC` nằm trong app `tro_ly_ke_toan`, ĐÃ có trên prod (prod ở `9a29a43`). **Bản local đi SAU prod** (`b716a21`), nên phải kéo về trước khi viết test. Huyền: tài khoản dùng lần cuối ngày 13/10. Nếu sau 3 ngày chị chưa mở thẻ nhiệm vụ, báo chủ đầu tư.

## 12. Công tắc, nơi chạy, deploy

- `feedback_widget` cài trên **erp.htsfood.com và hkd688.vn** (chung mã trong bench). Mọi tính
  năng nằm sau `nv_bat`, mặc định 0. Chỉ bật trên erp.htsfood.com.
- Nhánh sống là **`develop`** (không phải `main`). Prod đang ở `f0fbe40`, local ở `dd1fe95`
  (đi trước 1 commit chỉ có test).
- Cài đặt nằm ở **`Feedback Settings`** (`cai_dat.py`). Thư mục `feedback_widget_settings/` chỉ còn
  `__pycache__`, xoá nó trong lượt rà nợ. `cai_dat()` bỏ qua mọi khoá không có trong `MAC_DINH`, nên
  mỗi trường mới phải được thêm vào đó. `khong_xep_hang` là bảng con, không nằm trong `tabSingles`,
  nên phải đọc riêng.
- Deploy cần migrate (DocType mới + patch chỉ mục), build bundle (tệp JS mới), và restart web (module
  Python mới đã có người gọi qua hooks). Restart gây 502 khoảng 1 giây cho cả 3 site trên bench,
  nên chọn giờ vắng.

## 13. Kiểm thử và nghiệm thu

- **Test Python** (`tests/test_nhiem_vu_*.py`): mỗi loại bước khớp hoặc không khớp; `so_ngay`;
  `bat_dau` loại sự kiện cũ; chấm hai lần không cộng đôi (cả khi cron chạy song song); `Thu hồi`;
  Resolved tự bật `co_ich`; vé máy không có điểm; người bị tắt; validate quyền; nhiệm vụ hết hạn;
  bước đã xong vẫn còn sau `don_so_cu`; trường hợp "khớp hết" của chốt tồn. Không gửi tin ra ngoài
  (theo test `test_kiem_thu_khong_gui_telegram`).
- **Chrome thật** (`tests/nghiem_thu_prod_nhiem_vu.mjs`, chạy được trên prod bằng phiên ngắn hạn
  của `frappe-headed-qa`): lối vào menu, thẻ nhiệm vụ, chúc mừng, bảng vàng ở cỡ điện thoại 390px
  và desktop, trên desk, trang `chot-ton` và desk React. Lỗi console phải bằng 0.
- **Nghiệm thu thật**: 48 giờ sau khi bật, đọc báo cáo "Tiến độ nhiệm vụ" xem bao nhiêu người đã
  mở thẻ, bao nhiêu bước đã xong. Nếu 0/3 người mở thẻ thì lối vào sai, không phải người dùng thờ ơ.

## 14. Rà nợ trước khi ship (BẮT BUỘC, ngay trước bước deploy)

- Kênh `Feedback Notice` "Đã xử lý xong" (một người) vẫn chạy. Nó và thẻ chúc mừng "+50 Góp ý thành
  cải tiến" có báo trùng cùng một việc không? Hoặc gộp, hoặc ghi rõ lý do để cả hai.
- `feedback-announce` và `feedback-ducan.sh dong` có đặt `thanh_cai_tien` khi đóng vé không? Nếu
  không, đường +50 không bao giờ được kích hoạt.
- Cột mới (`co_ich`, `thanh_cai_tien`, `da_bao`): mỗi cột có đúng một nơi ghi và một nơi đọc.
- Đếm điểm chỉ có MỘT định nghĩa (`nhiem_vu.py`). Bảng vàng, hồ sơ và báo cáo đều gọi nó, không
  viết SQL riêng.
- Đo lại mọi lối vào trên prod (§7.1) bằng dữ liệu thật.
- Test đỏ, test để lại dữ liệu trên site.

## 15. Để cho người làm quyết

Màu và icon của thẻ, câu chữ chúc mừng (giữ ngắn, theo khuôn XONG · MỜI LÀM · LINK), cách vẽ thanh
tiến độ, phân trang bảng vàng, tên hàm và tệp Python ngoài các tên đã định ở trên.
