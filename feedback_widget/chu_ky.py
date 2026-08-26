"""Chữ ký sự kiện — MỘT định nghĩa duy nhất, tính ở MÁY CHỦ.

Vì sao chuẩn hoá: mỗi lần bị chặn, câu lỗi mang số và mã riêng của lần ấy
("lô 66M22507260591 chỉ còn 812 kg") nên gom theo nguyên văn thì mỗi lần một nhóm và
không bao giờ đếm được "lỗi này xảy ra bao nhiêu lần". Bỏ hết phần biến thiên rồi băm
→ cùng một LOẠI sự cố luôn ra cùng chữ ký.

Vì sao KHÔNG tính ở trình duyệt: hai bản cài đặt của một luật thì sớm muộn lệch nhau,
và lúc ấy hộp thư có hai nhóm cho cùng một lỗi mà không ai hiểu tại sao. Trình duyệt
chỉ gửi câu nguyên văn; chữ ký do đây quyết định.
"""

import hashlib
import re

# Dấu hiệu máy-đọc dạng [KHACCUON] — nếu câu lỗi có, nó CHÍNH LÀ danh tính của luật,
# ổn định hơn mọi phép chuẩn hoá văn bản.
_MARKER = re.compile(r"\[([A-Z][A-Z0-9ĐÂÊÔƠƯÁÀẢÃẠ]{3,24})\]")

_THAY = (
    (re.compile(r"<[^>]{0,200}>"), " "),                      # thẻ HTML của frappe.throw
    (re.compile(r"https?://\S+"), " <url> "),
    (re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"), " <ngay> "),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), " <ngay> "),
    (re.compile(r"\b[A-Z]{2,6}-\d{4}-\d{3,6}\b"), " <ma> "),  # XB-2026-0050, FB-2026-00123
    (re.compile(r"\b[A-Z0-9]{6,}[-_][A-Z0-9-_]{1,}\b"), " <lo> "),  # mã lô/băng có gạch nối
    # Mã TRỘN chữ và số, không gạch nối: `66M22507260591`, `39M1120`, `TTCN3.90`. Tiếng
    # Việt không có từ nào chứa chữ số, nên luật "vừa có chữ vừa có số" không ăn nhầm từ
    # thường. Thiếu luật này thì hai lần cùng một sự cố khác mã lô ra hai chữ ký khác nhau
    # — đo 25/08: câu "kho không đủ nguyên liệu" của hai lô không gom được.
    # Ngưỡng là 2 KÝ TỰ chứ không phải 4: mã ngắn ("A1", "B2") vẫn là mã, và sau khi bóc
    # thẻ HTML của `frappe.throw` thì đúng những mã ngắn ấy là phần còn lại khác nhau.
    (re.compile(r"\b(?=[A-Za-z0-9.]*[A-Za-z])(?=[A-Za-z0-9.]*\d)[A-Za-z0-9.]{2,}\b"), " <ma> "),
    (re.compile(r"\b\d[\d.,]*\b"), " <so> "),
    (re.compile(r"\s+"), " "),
)


def dau_hieu(message: str) -> str:
    """Dấu hiệu máy-đọc trong câu lỗi ('' nếu không có)."""
    m = _MARKER.search(message or "")
    return m.group(1) if m else ""


def chuan_hoa(message: str) -> str:
    """Câu lỗi sau khi bỏ mọi thứ biến thiên theo từng lần."""
    s = str(message or "")
    for rx, rep in _THAY:
        s = rx.sub(rep, s)
    return s.strip().lower()[:400]


def chu_ky(message: str, endpoint: str = "", kind: str = None) -> str:
    """Chữ ký 12 ký tự cho một LOẠI sự cố.

    Có dấu hiệu máy-đọc thì lấy nó làm gốc (kèm endpoint để phân biệt hai chỗ dùng
    chung một dấu hiệu); không có thì băm câu đã chuẩn hoá.

    `kind` CỐ Ý không vào băm — giữ trong chữ ký hàm chỉ để nơi gọi không phải sửa.
    VÌ SAO: hai nơi gọi khai `kind` khác nhau cho CÙNG một sự cố — vé băm kèm
    `source="auto"`, sổ băm kèm `kind="chan"/"loi"` — nên vé và sổ không bao giờ ra
    cùng khoá. Đo prod 26/08: 33 vé, 16 dòng sổ, **0 chữ ký dùng chung**, tức mục
    "Hồi quy" (vé đã đóng mà lỗi quay lại) nối `Comment.signature = Event.signature`
    về cấu trúc là LUÔN RỖNG, và vòng "đóng vé rồi đo lại chữ ký" so hai thứ khác nhau.
    Đánh đổi đã cân: `chan` và `loi` cùng câu + cùng endpoint nay gom một khoá — vẫn
    tách được khi cần vì cột `kind` còn nguyên; bảng xếp hạng đọc cột ấy, không đọc khoá.
    """
    mk = dau_hieu(message)
    goc = f"{endpoint}|{mk}" if mk else f"{endpoint}|{chuan_hoa(message)}"
    return hashlib.sha1(goc.encode("utf-8")).hexdigest()[:12]
