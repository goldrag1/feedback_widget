# Kịch bản màn — dẫn dắt, mục tiêu, nhắc nhở và huân chương danh dự

Ngày: 20/10/2026 · App: `feedback_widget` · Site bật đầu tiên: `erp.htsfood.com`
Chủ đầu tư: anh Long · Trạng thái: CHỜ DUYỆT (bản 2: chuyển trọng tâm từ "lần ra bản" sang "kịch bản màn", thêm nhắc nhở)

## 1. Vì sao

HTS ra 5–10 chức năng mỗi tuần. Phía người dùng, đo trên prod 20/10/2026:

- **Nhiều người dùng, rất ít góp ý.** 35 người dùng ERP trong 30 ngày (376.838 lượt thao tác).
  Góp ý gõ tay có 16 cái trong tháng 6, rồi chỉ còn 1–3 cái mỗi tháng từ tháng 8. Trong 90 ngày,
  ngoài chủ đầu tư chỉ có 3 người từng góp ý.
- **Thông báo "đã sửa" không ai bấm.** `Feedback Notice` đã gửi 7 thông báo, tất cả cho từng người
  một, và chưa có lượt "Xem thử" nào.
- **Chức năng mới chưa có người dùng thật.** «Chốt tồn hằng ngày» và «Hủy hàng tồn» ra ngày 19/10,
  nhưng chỉ chủ đầu tư từng mở; không nhân viên kho nào vào. «So giá hệ thống» có 2 người mở.
  «Đề nghị thanh toán» là ngoại lệ: 4 người Hà Lê dùng thật trong 5 ngày.

Nguyên nhân là ba khoảng trống:

1. Không ai dẫn người dùng qua lần đầu.
2. Không ai giao việc dùng thử.
3. Người góp ý không nhận lại được gì.

Hạ tầng thì không thiếu. Sổ `Feedback Event` đã ghi từng màn, từng nút, từng lệnh gọi máy chủ
kèm kết quả, nên chấm được "đã dùng thật chưa" mà không cần ai tự khai.

## 2. Mục tiêu, không làm, phản mục tiêu

**Mục tiêu**
1. **Kịch bản màn.** Mỗi màn quan trọng có một kịch bản sống lâu dài, gồm ba phần: hướng dẫn lần đầu,
   các chặng mục tiêu, và lời nhắc theo ngữ cảnh. Mọi người mở màn đều đi qua kịch bản, kể cả nhân
   viên vào làm sau này. Tất cả giao tiếp đi qua widget. *(Chủ đầu tư chốt 20/10.)*
2. **Giao kịch bản.** Có thể giao một kịch bản cho người cụ thể, kèm chặng cần đạt và hạn. Ai chậm
   mục tiêu hoặc chậm tiến độ thì widget nhắc. *(Chủ đầu tư chốt 20/10.)*
3. **Thưởng ảo danh dự.** Điểm, cấp bậc, huân chương; không có thưởng tiền. *(Chủ đầu tư chốt 20/10.)*
4. **Bảng vàng ai cũng xem được.** *(Chủ đầu tư chốt 20/10.)*
5. Chủ đầu tư thấy ngay màn nào đã có người dùng, ai đang kẹt, và lời nhắc nào có tác dụng.

**Không làm (lượt này)**
- Đổi điểm lấy quà, thưởng tiền, nối với lương.
- Nhắc qua Telegram hoặc Zalo: chỉ dùng widget.
- Soạn kịch bản bằng cách chỉ chuột vào màn. Lượt này soạn trên form desk, hoặc Claude soạn bằng
  kịch bản lệnh.
- Giao kịch bản theo VAI. Lượt này chỉ giao theo NGƯỜI. Phần hướng dẫn và chặng thì đã tự áp dụng
  cho mọi người mở màn.

**Phản mục tiêu** (chạy đúng kỹ thuật nhưng vẫn là thất bại)
- **Thưởng theo số lượt bấm.** Chị Điệp có 109.703 lượt trong 30 ngày, nhưng con số đó không cho
  biết chị có dùng chức năng mới hay không. Điểm chỉ đến từ BƯỚC đã khai sẵn, hoặc từ góp ý được duyệt.
- **Góp ý rác để lấy điểm.** Gõ góp ý không được điểm. Chỉ góp ý được đánh dấu có ích mới được.
- **Nhắc thành tiếng ồn.** Người nhận ba lời nhắc vô ích sẽ đóng lời nhắc thứ tư mà không đọc,
  và kéo theo cả thông báo thật. Vì vậy có trần số lần nhắc, giờ yên lặng, nút tạm hoãn, và tự dừng
  khi người dùng bỏ qua liên tục (§7).
- **Làm xấu mặt người chậm.** Không trừ điểm. Bảng vàng không xếp người 0 điểm. Lời nhắc chỉ gửi cho
  chính người đó; người giao chỉ nhận một thẻ tổng hợp khi quá hạn.
- **Hướng dẫn đè lên người đã quen màn.** Người đã dùng màn nhiều lần không bị bật hướng dẫn tự động
  (§5.1).

## 3. Khái niệm (dùng đúng chữ này trên giao diện)

| Chữ | Nghĩa |
|---|---|
| **Kịch bản** | Gắn với một màn: hướng dẫn lần đầu, các chặng, các mẹo |
| **Hướng dẫn lần đầu** | 3–6 thẻ ngắn, mỗi thẻ có thể chỉ vào một chỗ trên màn |
| **Chặng** | Một mức dùng màn: *Làm quen* → *Thành thạo* → *Chuyên gia*. Loại **Một lần** (đạt rồi là xong) hoặc **Duy trì** (mỗi ngày hoặc mỗi tuần phải đạt lại, ví dụ chốt tồn hằng ngày) |
| **Bước** | Một điều kiện máy chấm được, thuộc một chặng |
| **Mẹo** | Câu gợi ý hiện đúng lúc: khi bị chặn, khi xong một bước |
| **Giao kịch bản** | Giao cho người X đạt chặng Y trước ngày Z. Có nhắc |
| **Lời nhắc** | Thẻ widget gửi khi người dùng chậm mục tiêu hoặc chậm tiến độ |
| **Điểm · Cấp · Huân chương · Bảng vàng** | Như §8 |

## 4. Mô hình dữ liệu (đều thuộc `feedback_widget`, module Feedback Widget)

### 4.1 `Feedback Playbook` — Kịch bản màn, đặt tên `KB-.####`
| Trường | Kiểu | Ghi chú |
|---|---|---|
| `ten` | Data, bắt buộc | "Chốt tồn hằng ngày" |
| `man` | Data, bắt buộc, unique | Mẫu `screen_id`, cho phép `*` (`Form/Doi Soat Cong No NCC/*`) |
| `duong_dan` | Data, bắt buộc | `/app/chot-ton`. Không có đường dẫn là mời người dùng vào ngõ cụt |
| `ly_do` | Small Text | Một câu: dùng màn này để được gì |
| `project` | Data | Như các DocType khác của app |
| `dang_bat` | Check | Mặc định 1 |
| `nguon` | Data | Commit hoặc tính năng đã sinh ra màn |
| `huong_dan` | Table → `Feedback Playbook Guide` | |
| `chang` | Table → `Feedback Playbook Stage` | 1–4 chặng |
| `buoc` | Table → `Feedback Mission Step` | Mỗi bước gắn vào một chặng |
| `meo` | Table → `Feedback Playbook Tip` | |

### 4.2 `Feedback Playbook Guide` (bảng con) — thẻ hướng dẫn lần đầu
`thu_tu` (Int) · `tieu_de` (Data) · `noi_dung` (Small Text, tối đa 2 câu) · `chi_vao` (Data:
danh sách selector CSS ngăn bằng dấu `;`, thử lần lượt, vì desk, màn điện thoại và desk React có
DOM khác nhau) · `vi_tri` (Select: tự động / trên / dưới).

### 4.3 `Feedback Playbook Stage` (bảng con) — chặng
| Trường | Kiểu | Ghi chú |
|---|---|---|
| `ma` | Data | `lam-quen`, `thanh-thao`, `chuyen-gia`. Bước tham chiếu chặng qua mã này |
| `ten` | Data | "Làm quen" |
| `thu_tu` | Int | Phải xong chặng trước mới tính sang chặng sau |
| `loai` | Select | `Một lần` · `Duy trì` |
| `chu_ky` | Select | `Ngày` · `Tuần` (chỉ dùng cho Duy trì) |
| `gio_han` | Time | Duy trì theo ngày: phải đạt trước giờ này, ví dụ 17:00 |
| `ngay_lam_viec` | Data | Ví dụ `1,2,3,4,5,6` (Thứ Hai = 1). Mặc định lấy từ Cài đặt |
| `diem` | Int | Thưởng khi xong chặng. Với Duy trì: thưởng mỗi kỳ đạt |
| `hoi_cam_nhan` | Check, mặc định 1 | Xong chặng thì hỏi "Màn này dùng thấy sao?" (§6.4) |

### 4.4 `Feedback Mission Step` (bảng con) — bước
| Trường | Kiểu | Ghi chú |
|---|---|---|
| `chang` | Data | `ma` của chặng |
| `mo_ta` | Data, bắt buộc | Chữ hiện cho người dùng: "Ghi một phiếu chốt tồn" |
| `loai` | Select | `Mở màn` · `Bấm nút` · `Gọi máy chủ` · `Tạo chứng từ` · `Góp ý trên màn` |
| `nut` | Data | Mẫu `action_id`, cho phép `*` |
| `endpoint` | Data | So khớp chính xác với `Feedback Event.endpoint` |
| `chap_nhan_chan` | Data | Chỉ cho `Gọi máy chủ`: lần gọi bị chặn mà thông điệp chứa đoạn chữ này vẫn tính là xong (§10.2) |
| `doctype_ct` | Link → DocType | Cho `Tạo chứng từ` |
| `docstatus_toi_thieu` | Select 0/1 | Cho `Tạo chứng từ` |
| `so_lan` | Int, mặc định 1 | Số lần khớp tối thiểu (trong một kỳ, nếu chặng là Duy trì) |
| `so_ngay` | Int, mặc định 1 | Số NGÀY khác nhau tối thiểu (chỉ cho chặng Một lần) |
| `diem` | Int | Mặc định lấy từ Cài đặt (10). Chặng Duy trì: bước không có điểm riêng |

Luật khớp có MỘT định nghĩa duy nhất, trong `feedback_widget/kich_ban.py`. Mẫu màn lấy từ
`Feedback Playbook.man`.

| `loai` | Nguồn | Điều kiện |
|---|---|---|
| Mở màn | `Feedback Event` | `user`, `ts ≥ mốc`, `screen_id LIKE man` |
| Bấm nút | `Feedback Event` | như trên, thêm `action_id LIKE nut`, `outcome='ok'` |
| Gọi máy chủ | `Feedback Event` | `endpoint = endpoint` và (`outcome='ok'` HOẶC (`outcome='chan'` và `message LIKE %chap_nhan_chan%`)). `ok` nghĩa là máy chủ trả 2xx; `frappe.throw` trả 417 nên không bao giờ thành `ok` |
| Tạo chứng từ | `tab<doctype_ct>` | `owner = user`, `creation ≥ mốc`, `docstatus ≥ docstatus_toi_thieu`, `docstatus != 2` |
| Góp ý trên màn | `Feedback Comment` | `source='user'`, `submitter_user = user`, `ts ≥ mốc`, `screen_id LIKE man` |

Quy ước chung:
- Dấu `*` được đổi thành `%`; ký tự `%` và `_` có sẵn trong mẫu phải escape.
- Số ngày khác nhau tính bằng `COUNT(DISTINCT DATE(ts))`.
- **Mốc** của chặng Một lần là lúc người đó có dòng tiến độ (§4.6), hoặc lúc được giao nếu sớm hơn.
  Mốc của chặng Duy trì là đầu kỳ hiện tại.

> **Why chọn `Tạo chứng từ` cho bước "đã ghi thật":** sự kiện do TRÌNH DUYỆT gửi lên nên giả được,
> còn chứng từ trong sổ thì không. Chỉ dùng loại này khi doctype đó CHỈ màn này sinh ra (ví dụ
> `Doi Soat Cong No NCC`). `huy_hang.create` sinh `Stock Entry` thường, mà Stock Entry tạo ở chỗ
> khác cũng sẽ khớp, nên với Hủy hàng thì dùng `Gọi máy chủ`.

### 4.5 `Feedback Playbook Tip` (bảng con) — mẹo
`khi` (Select: `Bị chặn` · `Xong bước` · `Mở lần thứ`) · `dieu_kien` (Data: một đoạn chữ ký hoặc
thông điệp chặn; hoặc mã bước; hoặc một số) · `noi_dung` (Small Text) · `chi_vao` (Data, không bắt buộc).

### 4.6 `Feedback Playbook Progress` — tiến độ, mỗi cặp (kịch bản, người) một dòng, unique
| Trường | Ghi chú |
|---|---|
| `kich_ban`, `user` | |
| `bat_dau` | Lần đầu người đó mở màn sau khi kịch bản được bật (hoặc lúc được giao) |
| `huong_dan` | Select: `Chưa xem` · `Đang xem` (kèm thẻ đang đứng) · `Đã xem` · `Bỏ qua` |
| `huong_dan_the` | Int: thẻ đang đứng |
| `buoc_xong` | JSON `{step_row_name: ts}`. **Bước đã xong giữ nguyên**, kể cả sau khi sổ sự kiện bị dọn |
| `chang_xong` | JSON `{ma: ts}` cho các chặng Một lần |
| `chang_hien_tai` | Data |
| `duy_tri` | JSON `{ma: {ky_cuoi_dat, chuoi, chuoi_dai_nhat}}` |
| `lan_nhac_cuoi`, `so_lan_bo_qua_lien` | Phục vụ §7 |
| `nhac_tam_hoan_den` | Datetime |

### 4.7 `Feedback Mission` — giao kịch bản, đặt tên `NV-.YY.MM.-.####`
`kich_ban` (Link, bắt buộc) · `nguoi_nhan` (Table → `Feedback Notice User`, dùng lại) ·
`chang_muc_tieu` (Data: `ma` của chặng cần đạt) · `bat_dau` (mặc định lúc lưu) · `het_han`
(mặc định +7 ngày; với chặng Duy trì đây là hạn giữ được chuỗi) · `chuoi_muc_tieu` (Int, mặc định 3:
số kỳ Duy trì liên tiếp cần đạt) · `nhac` (Check, mặc định 1) · `nguoi_giao` (Link User, mặc định
người tạo) · `trang_thai` cho từng người lưu ở `Feedback Mission Assignee` (bảng con: `user`,
`trang_thai` = Đang làm / Hoàn thành / Quá hạn, `hoan_thanh_luc`).

Validate lúc lưu:
- `het_han − bat_dau ≤ retention_days − 7`.
- Người nhận phải `enabled=1`.
- Người nhận phải mở được màn: với Page thì kiểm `Has Role` của Page, với DocType thì kiểm
  `has_permission(read)`.

Không đạt thì CHẶN và nói rõ ai thiếu quyền gì. Đây là cổng chặn, nên phải ghi sổ khi chặn.

### 4.8 `Feedback Point` — sổ điểm, chỉ thêm, không sửa
`user` · `diem` (có thể âm) · `ly_do` (Select: `Bước` · `Chặng` · `Kỳ duy trì` · `Hoàn thành nhiệm vụ` ·
`Người mở đường` · `Góp ý có ích` · `Góp ý thành cải tiến` · `Cảm nhận` · `Thu hồi`) ·
`nguon_doctype`, `nguon_name` · `khoa` (unique, chấm lại nhiều lần không cộng đôi) · `da_bao` (Check).

### 4.9 `Feedback Badge Award` — huân chương đã trao
`user` · `huan_chuong` (Select, danh mục ở §8.3) · `luc` · `nguon_doctype`, `nguon_name` · `khoa` (unique) · `da_bao`.

### 4.10 Thay đổi trên DocType đã có
- `Feedback Comment`: thêm `tu_cam_nhan` (Check, ẩn: góp ý sinh từ thẻ hỏi cảm nhận) và `co_ich` (Check, "Góp ý có ích") và `thanh_cai_tien` (Check, "Dẫn tới
  cải tiến đã ra bản"; bật ô này thì tự bật `co_ich`).
- `Feedback Notice`: thêm `kich_ban` (Link), `loai_nhac` (Data: mã luật ở §7), `nhiem_vu` (Link).
  Mỗi lời nhắc là một Notice, nên **chính Notice là sổ nhắc**. Có sẵn `Feedback Notice Seen.da_bam`
  để đo hiệu quả.
- `Feedback Settings` (đây là DocType mà `cai_dat.py` đọc): thêm các trường dưới đây. Mỗi khoá mới
  phải thêm vào `MAC_DINH`, vì `cai_dat()` bỏ qua khoá lạ. `khong_xep_hang` là bảng con, không nằm
  trong `tabSingles`, nên phải đọc riêng.

| Trường | Mặc định | |
|---|---|---|
| `kb_bat` | **0** | Công tắc tổng |
| `diem_buoc` · `diem_chang` · `diem_ky_duy_tri` · `diem_nhiem_vu` · `diem_mo_duong` · `diem_co_ich` · `diem_cai_tien` · `diem_cam_nhan` | 10 · 30 · 5 · 30 · 20 · 20 · 50 · 5 | |
| `gio_mo_duong` | 48 | |
| `nguong_thanh_thao` · `nguong_key_user` · `nguong_dai_su` | 100 · 300 · 700 | |
| `tuan_chuyen_can` | 4 | |
| `phien_da_quen` | 3 | Ngưỡng "đã quen màn" (§5.1) |
| `gio_lam_tu` · `gio_lam_den` · `ngay_lam_viec` | 08:00 · 18:00 · `1,2,3,4,5,6` | |
| `nhac_toi_da_ngay` · `nhac_toi_da_kb_ngay` · `nhac_dung_sau_bo_qua` | 3 · 1 · 3 | |
| `nhac_chua_mo_gio` · `nhac_cham_bien` · `nhac_sap_het_gio` | 24 · 25 · 24 | |
| `khong_xep_hang` | Administrator + tài khoản chủ đầu tư | Table → User |

> **Why con số nằm ở Cài đặt còn luật nằm trong mã:** mỗi luật nhắc hay luật huân chương có logic
> riêng, nên thuộc về mã (rules-configurability). Các ngưỡng thì chỉnh được mà không cần deploy.

## 5. Kịch bản chạy thế nào

### 5.1 Lần đầu mở màn
1. Widget nhận diện màn (`_detectScreen`) và hỏi máy chủ `kich_ban.cua_toi(screen_id)`. Máy chủ trả
   kịch bản khớp, tiến độ của người này (tạo dòng nếu chưa có), cùng các thẻ cần hiện.
2. **Có bật hướng dẫn tự động hay không:** chỉ khi `huong_dan = Chưa xem` VÀ người này có ít hơn
   `phien_da_quen` phiên (`session_id` khác nhau) trên màn này trong sổ còn giữ, tính từ TRƯỚC khi
   kịch bản được bật. Người đã quen màn không bị bật; họ vẫn mở lại được từ menu.
   > **Why:** Lâm đã dùng ma trận phiếu giao hàng tháng; bật lại hướng dẫn cho anh ấy là đúng loại
   > tiếng ồn khiến người ta tắt mọi thẻ của widget.
3. Thẻ hướng dẫn: viền sáng quanh chỗ `chi_vao`, có nút Tiếp / Bỏ qua và "1/4". Không tìm thấy
   selector nào thì vẫn hiện thẻ (chỉ có chữ, ở giữa màn) và **ghi một `Feedback Event`
   `kind='loi'` với chữ ký `kich-ban-chi-vao-mat:<KB>:<thu_tu>`**. Nhờ vậy giao diện đổi làm hỏng
   hướng dẫn sẽ thành vé máy, không hỏng im lặng.
4. Đóng giữa chừng thì `Đang xem`. Lần mở sau widget hỏi một lần "Xem tiếp hướng dẫn?" (luật N7).

### 5.2 Trong lúc dùng
- Một nút nhỏ **"🎯 Mục tiêu"** gắn vào nút 💬 (badge là số bước còn lại của chặng hiện tại) mở thẻ
  chặng: tên chặng, các bước ✓/◐/○, điểm, bước kế tiếp, nút "Xem lại hướng dẫn".
- Bước vừa xong: chấm lại ngay khi widget đẩy lô sự kiện lên (máy chủ chấm sau `su_kien` ghi sổ,
  chỉ cho các kịch bản khớp màn đó) và gửi về mẹo `Xong bước` nếu có. Nếu không có mẹo thì gửi thẻ
  "Xong ✓ — tiếp: <bước kế>".
- Bị chặn: nếu kịch bản có mẹo `Bị chặn` khớp thì hiện mẹo ngay tại chỗ.

### 5.3 Xong chặng
Thưởng điểm, chuyển sang chặng sau, và nếu `hoi_cam_nhan` thì hỏi cảm nhận (§6.4).

### 5.4 Chặng Duy trì
Mỗi kỳ (ngày hoặc tuần, chỉ tính ngày làm việc) đạt đủ bước trước `gio_han` thì cộng
`diem_ky_duy_tri` và nối chuỗi. Lỡ một kỳ thì chuỗi về 0, **không trừ điểm**, và thẻ kế tiếp viết
"Bắt đầu lại chuỗi". Chuỗi dài nhất được giữ để hiện trong hồ sơ.

## 6. Giao diện

Phần vẽ nằm ở **tệp riêng** `public/js/kich_ban_the.js`, khai `window.FeedbackPlaybook`, theo đúng
quy ước của `thong_bao_the.js` (core.js do phiên khác giữ). Chữ hiển thị là tiếng Việt, ô bấm
≥ 44px, chạy được trên màn 390px.

### 6.1 Lối vào
- Menu nút 💬: **"🎯 Mục tiêu trên màn này"** (chỉ hiện khi màn có kịch bản), **"🏅 Thành tích của
  tôi"**, **"🏆 Bảng vàng"**.
- Phải chạy ở mọi nơi widget đang chạy: desk, Frappe Page (chot-ton, huy-hang, hop-thu), màn mobile
  www, desk React. Người làm phải đo từng nơi (§12).

### 6.2 Thẻ mục tiêu
```
 🎯 Chốt tồn hằng ngày — chặng Làm quen
 ✓ Mở trang Chốt tồn                              +10
 ◐ Ghi phiếu chốt tồn 3 ngày khác nhau (1/3)      +10
 ○ Gửi một góp ý ngay trên trang                  +10
 Xong chặng: +30 · Hạn giao: còn 5 ngày
 [ Bước tiếp ]  [ Xem lại hướng dẫn ]
```
Ô "Gửi một góp ý" mở thẳng ô góp ý đã gắn sẵn màn hiện tại.

### 6.3 Thành tích của tôi
Cấp + thanh tới cấp kế · tổng điểm · huân chương ×N · danh sách kịch bản (chặng đã đạt, chuỗi duy trì).

### 6.4 Hỏi cảm nhận khi xong chặng
"Màn «Chốt tồn» dùng thấy sao?" với 👍 / 👎 và một ô gõ không bắt buộc.
- Chỉ bấm 👍 (không gõ chữ) thì **không tạo `Feedback Comment`**: lưu vào progress (`cam_nhan`
  JSON `{chặng: "👍"}`) và ghi một `Feedback Event` `action_id='kich-ban::cam-nhan'`. Lý do: mọi
  góp ý gõ tay đều bị đẩy lên Telegram (`api/feedback.py`), và một 👍 không đáng làm phiền ai.
- Bấm 👎, hoặc gõ chữ, thì tạo `Feedback Comment` `source='user'` với cờ mới `tu_cam_nhan=1`. Góp ý
  này đi vào triage và Telegram như mọi vé khác, vì một lời chê là việc thật.
- Cả hai trường hợp đều cộng `diem_cam_nhan` MỘT lần cho mỗi chặng (`khoa` =
  `Cảm nhận|KB|chặng|user`).
- **Góp ý `tu_cam_nhan=1` KHÔNG thỏa bước "Góp ý trên màn"**, để một cú chạm không ăn cả điểm bước
  lẫn điểm cảm nhận (phản mục tiêu "góp ý rác lấy điểm").
- Bỏ qua thì không hỏi lại cho chặng đó.
- *(Quyết định của Claude.)*

> **Why:** đây là chỗ đánh vào con số "1–3 góp ý/tháng". Hỏi ngay lúc người dùng vừa làm xong, bằng
> một cú chạm, thay vì đợi họ tự nghĩ ra để mở widget.

### 6.5 Chúc mừng
Lần chấm sau phát hiện dòng điểm hoặc huân chương `da_bao=0` thì hiện một thẻ gộp, ví dụ: «+30 —
Xong chặng Làm quen "Chốt tồn". 🚀 Người mở đường».

**Lên cấp:** cấp TRƯỚC tính từ tổng điểm các dòng `da_bao=1`, cấp SAU từ tổng mọi dòng. Hai cấp khác
nhau thì thêm dòng "Lên cấp Key user", rồi đánh dấu `da_bao=1`. *(Quyết định của Claude: không cần lưu
cấp riêng.)*

### 6.6 Bảng vàng
- Hai tab: Tháng này / Từ trước tới nay.
- Bộ lọc công ty mặc định là công ty của người xem, có lựa chọn "Tất cả". Công ty của một người lấy
  theo thứ tự: `Employee.company` (theo `user_id`) → User Permission `Company` nếu chỉ có đúng một →
  công ty mặc định toàn cục. Phải chịu được site không có HRMS. *(Quyết định của Claude: Ngân, Huyền
  và Huỳnh không có Employee.)*
- Cột: hạng, tên, cấp, điểm, huân chương. Chỉ hiện người có điểm > 0, không hiện `khong_xep_hang`.
  API không trả email.

### 6.7 Phía quản trị (System Manager)
- Form `Feedback Playbook` và `Feedback Mission` trên desk.
- Script Report **"Tiến độ kịch bản"**, mỗi dòng một cặp (kịch bản, người). Các cột: chặng hiện tại,
  bước xong/tổng, chuỗi duy trì, lần cuối mở màn, số lời nhắc đã gửi, **% lời nhắc có hành động trong
  24 giờ**, giao bởi ai, hạn, trạng thái. Lọc theo kịch bản, theo người, theo "đang kẹt" (có nhắc mà
  không có hành động).
- Script Report **"Màn chưa ai dùng"**: kịch bản đang bật × số người đạt Làm quen. Đây là câu trả lời
  cho câu hỏi "chức năng nào chưa ai đụng".

## 7. Nhắc nhở khi chậm mục tiêu hoặc chậm tiến độ

Một cron 15 phút (`tac_vu.nhac_kich_ban`) chạy các luật dưới đây. Mỗi lời nhắc là một `Feedback
Notice` phạm vi `Một người`, có `kich_ban` và `loai_nhac`, đi qua phao realtime nên hiện ngay,
không cần F5. Mọi lời nhắc theo khuôn **TRẠNG THÁI · VIỆC KẾ TIẾP · NÚT MỞ THẲNG**, giọng mời,
không trách. Mẫu lời ghi trong mã, mỗi luật một mẫu.

| Mã | Khi nào | Gửi ai | Lời mẫu |
|---|---|---|---|
| **N1 Chưa mở** | Được giao đã `nhac_chua_mo_gio` giờ mà chưa có sự kiện nào trên màn | người nhận | "Anh/chị được mời dùng thử «Chốt tồn». Bắt đầu bằng hướng dẫn 1 phút →" |
| **N2 Chậm tiến độ** | Đã qua ≥ 40% thời gian giao, và tỷ lệ bước xong của chặng mục tiêu < tỷ lệ thời gian đã trôi − `nhac_cham_bien` điểm % | người nhận | "«Chốt tồn»: xong 1/3 bước, còn 4 ngày. Bước kế: ghi phiếu chốt hôm nay →" |
| **N3 Sắp hết hạn** | Còn ≤ `nhac_sap_het_gio` giờ mà chưa xong | người nhận, một lần | "Còn 1 ngày để xong «Làm quen» của «Chốt tồn» →" |
| **N4 Quá hạn** | Quá `het_han` mà chưa xong | người nhận (một lần, giọng "vẫn làm tiếp được") + **người giao** (một thẻ tổng hợp mỗi ngày: ai quá hạn, kẹt ở bước nào, đã nhắc mấy lần) | |
| **N5 Duy trì chưa đạt** | Ngày làm việc, đã tới `gio_han` − 2 giờ mà kỳ này chưa đạt | CHỈ người đang được giao chặng đó | "Hôm nay chưa chốt tồn kho Hà Đông — chuỗi 4 ngày đang chờ →" |
| **N6 Kẹt vì bị chặn** | ≥ 3 lần chặn cùng chữ ký trên màn của kịch bản trong 1 giờ | người đó | Có mẹo `Bị chặn` khớp thì hiện mẹo. Không có thì: "Có vẻ đang vướng ở đây. Gửi góp ý (đã kèm sẵn màn) →" |
| **N7 Hướng dẫn bỏ dở** | Mở lại màn khi `huong_dan = Đang xem` | người đó, một lần | "Xem tiếp hướng dẫn (còn 2 thẻ)?" |

**Ai nhận nhắc:** N1–N5 chỉ gửi cho người ĐƯỢC GIAO (họ có công tắc `Feedback Mission.nhac`).
N6 và N7 là thẻ tại chỗ, hiện cho mọi người đang mở màn. Người không được giao vẫn có chuỗi Duy
trì trong hồ sơ, nhưng không bao giờ bị nhắc. Chuỗi tính theo NGƯỜI, không theo kho: hôm Lâm nghỉ
và đồng nghiệp chốt hộ thì chuỗi của Lâm đứt. Đúng ý đồ, vì đây là thước đo việc Lâm có dùng hay
không. *(Quyết định của Claude.)*

**Vòng đời một thẻ nhắc:**
- `het_han` = cuối giờ làm của ngày làm việc kế tiếp, để thẻ không chất đống.
- **"Bỏ qua"** chỉ tính khi người dùng bấm ✕ (`da_xem`, `da_bam=0`). Thẻ tự ẩn sau
  `giay_tu_dong_dong` giây không tính là bỏ qua; thẻ vẫn hiện lại lần mở sau cho tới khi hết hạn.
- **"Để mai"** gọi `da_xem` với cờ `tam_hoan=1` (thêm Check `tam_hoan` vào `Feedback Notice Seen`)
  và đặt `progress.nhac_tam_hoan_den`. Thẻ đó biến mất. Hôm sau, nếu vẫn chậm, cron gửi một thẻ MỚI.
  Không cần truy vấn ẩn-theo-người riêng.
- **"Mở"** gọi `da_xem` với `da_bam=1` và đặt `so_lan_bo_qua_lien = 0`.

*(Quyết định của Claude.)*

**Luật chống ồn** (áp dụng trước khi gửi bất kỳ lời nhắc nào):
1. Chỉ gửi trong khoảng `gio_lam_tu`–`gio_lam_den`, vào `ngay_lam_viec`. Lời nhắc rơi ngoài giờ thì
   chờ tới giờ làm kế tiếp. N6 và N7 là thẻ tại chỗ nên không bị giới hạn này.
2. Mỗi người tối đa `nhac_toi_da_ngay` lời nhắc một ngày, tối đa `nhac_toi_da_kb_ngay` cho mỗi kịch
   bản. Thứ tự ưu tiên khi vượt trần: N4 > N3 > N5 > N2 > N1.
3. Mỗi thẻ nhắc có nút **"Để mai"**, đặt `nhac_tam_hoan_den` = đầu giờ làm ngày làm việc kế tiếp.
4. Đóng thẻ mà không bấm nút mở liên tiếp `nhac_dung_sau_bo_qua` lần thì **dừng nhắc kịch bản đó cho
   người đó**, và báo người giao qua thẻ tổng hợp N4: "Ngân đã bỏ qua 3 lời nhắc «Hộp thư» — có thể
   cần nói chuyện trực tiếp". Bấm mở lại bất kỳ lúc nào thì đếm lại từ 0.
5. Không nhắc người có tài khoản bị tắt, và không nhắc khi `kb_bat=0` hoặc `Feedback Mission.nhac=0`.

**Đo hiệu quả:** một lời nhắc được tính là "có tác dụng" nếu trong 24 giờ sau khi gửi người đó có
sự kiện trên màn của kịch bản. Số này hiện trong báo cáo §6.7. Luật nào dưới 20% sau 2 tuần là
viết sai, cần sửa lại câu chữ hoặc ngưỡng; không được kết luận là người dùng thờ ơ.

> **Why người giao nhận thẻ TỔNG HỢP chứ không nhận từng lời nhắc:** người giao cần biết ai kẹt để
> nói chuyện trực tiếp. Nhận từng lời nhắc thì họ thành người nhận tiếng ồn thứ hai.

## 8. Điểm, cấp, huân chương

### 8.1 Chấm khi nào
Có bốn đường:
1. Cron 15 phút.
2. `kich_ban.cua_toi()` lúc mở màn hoặc mở thẻ.
3. Sau mỗi lô `su_kien` (chỉ cho kịch bản khớp màn đó).
4. `Feedback Comment` after_insert / on_update.

Cả bốn đường gọi chung MỘT hàm `cham(kich_ban, user)`. Ghi điểm dựa vào `khoa` unique (bị trùng
thì bỏ qua). Cập nhật tiến độ dưới `SELECT … FOR UPDATE` trên dòng progress.

### 8.2 Bảng điểm
| Sự kiện | Điểm |
|---|---|
| Xong một bước (chặng Một lần) | `diem` của bước |
| Xong một chặng Một lần | `diem` của chặng |
| Đạt một kỳ Duy trì | `diem_ky_duy_tri` |
| Hoàn thành nhiệm vụ được giao | `diem_nhiem_vu` |
| Hoàn thành trong `gio_mo_duong` giờ kể từ lúc giao | +`diem_mo_duong` + 🚀 |
| Trả lời "dùng thấy sao" | `diem_cam_nhan` |
| `co_ich` bật | `diem_co_ich` |
| `thanh_cai_tien` bật | `diem_cai_tien` |
| Tắt `co_ich` / `thanh_cai_tien` sau khi đã cộng | dòng âm `Thu hồi` |

Chi tiết:
- `co_ich` tự bật khi `status` **CHUYỂN** sang Resolved (`has_value_changed`), trừ khi người duyệt
  đã tắt tay. Lưu lại một vé đã Resolved từ trước thì không bật.
  > **Why:** nếu phải đợi người tick tay thì không ai tick, và đường thưởng chết y như kênh thông
  > báo hiện nay.
- **Bù một lần lúc bật** *(quyết định của Claude, anh có thể bác)*: một patch bật `co_ich` và cộng
  điểm cho các góp ý gõ tay đã Resolved trước đó (prod hiện có 23 góp ý gõ tay). Patch không bật
  `thanh_cai_tien`.
- Vé máy (`source='auto'`) không bao giờ được điểm.
- Người nằm trong `khong_xep_hang` vẫn được ghi điểm, chỉ bị ẩn trên bảng vàng.

### 8.3 Cấp và huân chương
- **Cấp:** Tập sự (< `nguong_thanh_thao`) → Thành thạo → Key user → Đại sứ chuyển đổi số (≥ `nguong_dai_su`).
- **Huân chương** (danh mục trong mã, mỗi huân chương một hàm kiểm tra, nhận được nhiều lần):

| | Tên | Luật |
|---|---|---|
| 🚀 | Người mở đường | Xong nhiệm vụ được giao trong `gio_mo_duong` giờ đầu |
| 🦅 | Mắt tinh | Góp ý `tag_type='bug'` được bật `thanh_cai_tien` |
| 💡 | Người gợi ý | Góp ý `tag_type='idea'` được bật `thanh_cai_tien` |
| 🔥 | Chuyên cần | `tuan_chuyen_can` tuần ISO liên tiếp, tuần nào cũng có ≥ 1 dòng điểm dương |
| 🎯 | Thạo «màn» | Đạt chặng cuối của một kịch bản |
| 📅 | Chuỗi 10 / 30 | Chuỗi Duy trì đạt 10, rồi 30 kỳ |

`tag_type` gần như luôn trống (prod: 20/23, vì `hien_tag=0`). Vì vậy **người đóng vé phân loại**:
khi đóng bằng `feedback-announce` / `dong`, người đóng (thường là Claude) đặt `tag_type` cùng lúc
với `thanh_cai_tien`. Vé thành cải tiến mà `tag_type` trống thì chỉ có điểm, không có 🦅/💡.
*(Quyết định của Claude.)*

## 9. Hiệu năng

`Feedback Event` có **611.658 dòng**, nhưng **chỉ có chỉ mục trên `name` và `creation`** (đo 20/10).

- Patch tạo hai chỉ mục ghép: `(user, ts)` và `(screen_id, ts)`.
- Ngưỡng: `cham()` một người, một kịch bản 3 chặng 8 bước phải < 50 ms trên prod. Lượt cron nhắc
  cho toàn site phải < 5 giây. Đo cả trước và sau khi thêm chỉ mục.
- `ALTER` chạy online trên InnoDB, mất vài giây. Chạy trong giờ làm thì báo trước.
- Chấm sau lô `su_kien` chạy `enqueue` hàng `short`, không chặn request ghi sự kiện.

## 10. Khi nào khác? (trường hợp biên)

1. **Sổ sự kiện bị dọn sau 90 ngày.** Bước đã xong nằm ở progress nên không mất. Hạn giao bị giới hạn
   ≤ `retention_days − 7`.
2. **Chốt tồn khi mọi dòng khớp sổ.** `chot_ton.create` khi đó gọi `frappe.throw("Tại thời điểm chốt,
   mọi mặt hàng đã đếm đều khớp sổ — không cần ghi phiếu.")`. Người dùng đã làm đúng việc, nên bước
   này dùng `chap_nhan_chan = "đều khớp sổ"`. Người làm phải xác nhận trên mirror rằng lần chặn ấy vào
   sổ với `kind='chan'` và `message` chứa đúng câu đó, rồi viết test cho trường hợp này.
3. **Màn có selector khác nhau giữa desk, mobile và desk React.** `chi_vao` cho phép nhiều selector.
   Không selector nào khớp thì hiện thẻ chữ và ghi vé máy (§5.1).
4. **`action_id` mang số động** (ví dụ `hop-thu::Chưa xong 3`). Với những nút này dùng `*` hoặc
   chuyển sang `Gọi máy chủ`.
5. **Một màn khớp hai kịch bản** (mẫu `*` chồng nhau). `man` là unique, và validate từ chối mẫu chồng
   lên kịch bản đang bật.
6. **Đổi kịch bản khi đã có người đang làm.**
   - Bước đã xong giữ nguyên điểm.
   - Bước mới chấm từ mốc cũ.
   - Bước bị xoá thì không thu điểm đã cộng.
   - Thẻ hướng dẫn đổi thì không bật lại cho người đã xem. Muốn bật lại cho mọi người thì có nút
     "Phát lại hướng dẫn" trên form, đặt mọi progress về `Chưa xem`.
7. **Người dùng ở hai công ty, hoặc dùng chung tài khoản** (ví dụ `kt.hamona@gmail.com` "Kế toán
   HTS"). Chấm theo tài khoản. Báo cáo ghi chú các tài khoản không gắn Employee.
8. **Chủ đầu tư tự thử.** Vẫn chấm, nhưng ẩn khỏi bảng vàng.
9. **Lần chặn chỉ vào sổ khi `auto_report=1`** (prod = 1, đo 20/10), và cùng một thông điệp lặp
   trong 3 giây chỉ ghi một lần. `chap_nhan_chan` và N6 phụ thuộc vào điều này. Khi bật `kb_bat` mà
   `auto_report=0` thì Cài đặt CẢNH BÁO; hai tính năng đó tự tắt chứ không chấm sai.
10. **Mất sự kiện.** `usage_sample_pct` = 100 trên prod, nhưng mỗi trình duyệt có trần
   `max_events_per_minute` = 120. Có thể mất vài sự kiện "mở/bấm". Chấp nhận, vì bước "đã ghi thật"
   dùng nguồn máy chủ. Không vượt trần cho kịch bản.
11. **`Feedback Event.ts` là lúc máy chủ NHẬN lô**, không phải lúc người dùng bấm. Lô gửi trễ qua nửa
    đêm có thể lệch `so_ngay` hoặc kỳ Duy trì một ngày. Chấp nhận.
12. **Ngày nghỉ.** Kỳ Duy trì và lời nhắc chỉ tính `ngay_lam_viec`. Ngày lễ lượt này chưa tính.
    *(Hoãn có lý do: chưa site nào khai Holiday List cho nhân viên kho; khi cần thì đọc Holiday List
    của Employee.)*
13. **Site không có `tabEmployee` / HRMS.** Phần dự phòng công ty (§6.6) và người nhận thẻ N4 (người
    giao) không phụ thuộc HRMS.
14. **`kb_bat = 0`.** Cron không chạy, menu không hiện, API trả rỗng, dữ liệu giữ nguyên.

## 11. Lập kịch bản khi ra bản (đổi quy trình, không chỉ đổi mã)

Bước cuối của lượt ship hiện nay là `feedback-announce`. Thêm vào skill đó, viết lại `SKILL.md`:

- Màn MỚI thì lập kịch bản (2–4 thẻ hướng dẫn, chặng Làm quen 2–3 bước, mẹo cho các cổng chặn của
  màn).
- Màn CŨ được cải tiến thì thêm bước hoặc mẹo vào kịch bản đã có.
- Giao cho người đang làm đúng việc ấy (theo số đo) hoặc người chủ đầu tư chỉ định.

Có script `scripts/lap_kich_ban.py`, chạy qua `prod-probe.sh`. Khi đóng vé phải đặt `tag_type` và
`thanh_cai_tien`. Không sửa skill thì kịch bản dừng lại ở đợt đầu tiên.

## 12. Bốn kịch bản đầu tiên và việc giao (chủ đầu tư chỉ định 20/10)

Đã đo quyền trên prod ngày 20/10: cả ba người đều mở được màn của mình.

| Kịch bản | Giao cho | Chặng (người làm đối chiếu lại endpoint thật) |
|---|---|---|
| Chốt tồn hằng ngày `chot-ton` | Lâm `hanoi.hamona@gmail.com` (Kho HTS, Stock Manager). Mục tiêu: Duy trì, chuỗi 3, hạn 7 ngày | **Làm quen:** mở màn · gọi `my_custom_app.my_custom_app.chot_ton.create` (`chap_nhan_chan="đều khớp sổ"`) · góp ý trên màn. **Duy trì (Ngày, trước 17:00):** gọi `chot_ton.create` ≥ 1 |
| Hủy hàng tồn `huy-hang` | Huyền KT `thanhhuyen.iclould2001@gmail.com` (Stock Manager; tài khoản `thanhhuyen.icloud2001` đã bị tắt). Mục tiêu: Làm quen | **Làm quen:** mở màn · gọi `my_custom_app.my_custom_app.huy_hang.create` · góp ý trên màn |
| Đối soát công nợ NCC `Form/Doi Soat Cong No NCC/*` (+ List) | Ngân `sale11.hamona@gmail.com`. Mục tiêu: Làm quen | **Làm quen:** mở màn · tạo chứng từ `Doi Soat Cong No NCC` · góp ý trên màn |
| Hộp thư `hop-thu` | Ngân. Mục tiêu: Thành thạo | **Làm quen:** mở màn · gọi `tro_ly_ke_toan.hop_thu.api.gui`. **Thành thạo:** bấm `hop-thu::+ Tạo đơn mua` hoặc gắn đối tác · góp ý trên màn |

Ghi chú:
- `Doi Soat Cong No NCC` nằm trong app `tro_ly_ke_toan` và đã có trên prod (`9a29a43`). **Bản local
  đi SAU prod** (`b716a21`), nên phải kéo về trước khi viết test.
- Huyền dùng hệ thống lần cuối ngày 13/10, nên luật N1 sẽ là phép thử đầu tiên của phần nhắc nhở.
- Ngân đã dùng `hop-thu` (245 sự kiện trong 30 ngày), nên luật §5.1 sẽ KHÔNG bật hướng dẫn tự động
  cho Ngân. Đây là hành vi đúng.

## 13. Công tắc, nơi chạy, deploy

- `feedback_widget` cài trên **erp.htsfood.com và hkd688.vn** (chung mã trên một bench). `kb_bat`
  mặc định 0; chỉ bật cho erp.htsfood.com.
- Nhánh sống là **`develop`**, không phải `main`. Prod đang ở `f0fbe40`; local ở `dd1fe95` (+1 commit
  chỉ có test) cộng thêm các commit spec. `tro_ly_ke_toan` local (`b716a21`) đi SAU prod (`9a29a43`);
  phải kéo về trước khi làm kịch bản Đối soát / Hộp thư.
- Deploy cần: migrate (DocType mới, trường mới, patch chỉ mục, patch bù điểm), build bundle (thêm
  tệp JS), restart web (thêm module Python và hook mới). Restart gây 502 khoảng 1 giây cho cả 3 site
  trên bench, nên chọn giờ vắng.
- Xoá thư mục mồ côi `doctype/feedback_widget_settings/` (chỉ còn `__pycache__`).

## 14. Kiểm thử và nghiệm thu

**Test Python** (`tests/test_kich_ban_*.py`) cần phủ:
- Mỗi loại bước, cả khớp lẫn không khớp; `so_ngay`; mốc thời gian.
- Chặng Duy trì: đạt kỳ, lỡ kỳ, ngày không làm việc, chuỗi.
- Chấm hai lần (kể cả song song) không cộng đôi. `Thu hồi`. Resolved tự bật `co_ich`. Vé máy không
  được điểm.
- Hướng dẫn tự bật hay không theo `phien_da_quen`.
- Từng luật nhắc N1–N7 và từng luật chống ồn: trần, giờ yên lặng, "Để mai", dừng sau 3 lần bỏ qua,
  ưu tiên khi vượt trần.
- Validate quyền và người bị tắt. Bước đã xong còn nguyên sau `don_so_cu`. Trường hợp "khớp hết" của
  chốt tồn.
- Không gửi tin ra ngoài (theo `test_kiem_thu_khong_gui_telegram`).

**Chrome thật** (`tests/nghiem_thu_prod_kich_ban.mjs`, chạy được trên prod bằng phiên ngắn hạn của
`frappe-headed-qa`):
- Hướng dẫn lần đầu có viền sáng đúng chỗ, và có trường hợp selector mất.
- Thẻ mục tiêu, thẻ nhắc với nút "Để mai", hỏi cảm nhận, chúc mừng, bảng vàng.
- Chạy ở 390px và desktop, trên desk, trang `chot-ton` và desk React.
- Console phải 0 lỗi.

**Nghiệm thu thật:** 48 giờ sau khi bật, đọc báo cáo "Tiến độ kịch bản". Nếu 0/3 người mở thẻ thì
lối vào sai, không phải người dùng thờ ơ. Sau 2 tuần, đọc tỷ lệ lời nhắc có tác dụng theo từng luật.

## 15. Rà nợ trước khi ship (BẮT BUỘC, ngay trước bước deploy)

- Thông báo "Đã xử lý xong" (`Feedback Notice` một người) và thẻ chúc mừng "+50 Góp ý thành cải tiến"
  có báo trùng cùng một việc không? Gộp lại, hoặc ghi lý do giữ cả hai.
- `feedback-announce` / `feedback-ducan.sh dong` đã đặt `thanh_cai_tien` + `tag_type` chưa? Chưa thì
  +50 và 🦅/💡 không bao giờ được trao.
- Mỗi cột mới (`co_ich`, `thanh_cai_tien`, `da_bao`, `kich_ban`/`loai_nhac` trên Notice) có đúng một
  nơi ghi và một nơi đọc.
- Đếm điểm và luật khớp chỉ có MỘT định nghĩa (`kich_ban.py`). Bảng vàng, hồ sơ và báo cáo đều gọi
  vào đó, không viết SQL riêng.
- Mỗi luật nhắc có ghi sổ (chính là Notice) và người nhận làm được việc lời nhắc mời.
- Đo lại mọi lối vào (§6.1) trên prod bằng dữ liệu thật.
- Không có test đỏ, không có test để lại dữ liệu trên site.

### Kết quả rà nợ 20/10/2026 (trước deploy — đo trên mirror, 116 + 52 test xanh, Chrome thật ĐẠT)

**Sửa ngay:**
- *Hai thẻ cho một việc* — đúng như lo: vé Resolved sinh thẻ "Đã xử lý xong" VÀ điểm +20/+50 chưa
  báo ⇒ widget hiện thêm thẻ chúc mừng cùng lúc. Nay `bao_ve_da_xu_ly._gop_thuong` ghép điểm +
  huân chương của CHÍNH vé đó vào thẻ báo và đánh dấu `da_bao`; thẻ chúc mừng chỉ còn gánh điểm
  khác (test `TestThuongDiChungTheBao`).
- *Bảng vàng có SQL cộng điểm riêng* ⇒ `diem.bang_diem`, API gọi vào đó.
- *Test để lại dữ liệu*: hai tài khoản `thu-kb-*` sót trên mirror ⇒ `tearDownModule` → `xoa_nguoi()`.
- *Thanh bên mồ côi*: mục "Home" trỏ Workspace "Feedback" đã gỡ làm TRẮNG trang mọi báo cáo không
  có mục riêng (TypeError `.public`) ⇒ `thanh_ben.don_va_bo_sung` ở after_migrate + 4 lối vào mới.
- *Hai chồng thẻ đè nhau* (nút "Để mai" bấm không tới) ⇒ dùng chung `#fbw-thong-bao-lop`.
- *Đóng vé bằng `db.set_value` bỏ qua điểm* ⇒ ghi vào `feedback-announce` + `feedback-analyse-latest`:
  đóng bằng `doc.save()`, đặt `tag_type` + `thanh_cai_tien`.
- *Thẻ hướng dẫn trỏ phần chỉ hiện sau khi chọn dữ liệu* (7/10 thẻ ở 3 màn) ⇒ mỗi thẻ thêm chỗ dự
  phòng có sẵn lúc mới mở, khỏi đẻ vé máy `kich-ban-chi-vao-mat` cho mọi người mới.

**Hoãn, có lý do:**
- Bốn câu SQL "khớp màn" (`kich_ban.dem_buoc`, `api._so_phien_truoc`, `nhac.meo_tai_cho`, báo cáo
  `tac_dung_cua_nhac`) dùng CHUNG `kich_ban.mau_like`; câu truy vấn khác nhau vì câu hỏi khác nhau
  (đếm phiên trước mốc · đếm chặn trong 1 giờ · có sự kiện trong 24 giờ). Không gộp.
- `da_bao` có hai nơi ghi (`diem.danh_dau_da_bao`, `_gop_thuong`) — cùng một nghĩa "đã báo cho người".
- Màn điện thoại `www` không nạp bundle desk nên chưa có kịch bản; bốn màn đợt 1 đều là desk/Page.
- Hộp thư Thành thạo "tạo đơn mua HOẶC gắn đối tác": bước là AND nên chỉ còn "+ Tạo đơn mua"; cần
  loại bước "một trong" nếu chủ đầu tư muốn giữ chữ "hoặc".
- Selector form Đối soát NCC chưa đo được trên mirror (form mới không dựng — `tro_ly_ke_toan` local
  đi sau prod 26 commit); mẫu `.frappe-control[data-fieldname=…]` đã đo đúng trên form desk khác.
  Đo trên prod ở bước nghiệm thu, cùng việc đo lại mọi lối vào §6.1.
- Có sẵn từ trước, ngoài phạm vi: hash tab của form (`#details`) bị ghi thành `screen_id`
  (`currentRoute` trả mọi hash) — lần mở đầu không có hash nên bước "Mở màn" vẫn khớp.

## 16. Để cho người làm quyết

Màu và icon, câu chữ cụ thể (giữ ngắn, đúng khuôn ở §7), hiệu ứng viền sáng, cách vẽ thanh tiến độ,
phân trang bảng vàng, tên hàm và tệp ngoài các tên đã định ở trên.
