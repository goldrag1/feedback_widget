"""Vé được xử lý xong thì NGƯỜI GÕ phải biết — tự động, không chờ ai nhớ.

Đo trên một site thật 26/08/2026: 93 vé người gõ trong 60 ngày, 74 vé đã Resolved, **0
lượt báo ngược cho người gửi**. Sửa xong mà không ai được báo thì với người dùng nó chưa
xảy ra: họ đã bỏ đường ấy từ lâu và không quay lại thử. Việc báo tay thì luôn là thứ rơi
ra khỏi danh sách khi cuối ngày bận.

Cơ chế: khi `Feedback Comment.status` rời khỏi "New", controller gọi hàm này; nó dựng một
`Feedback Notice` phạm vi "Một người" gửi đúng người đã gõ vé — thẻ đẩy thẳng lên màn của
họ ở lần tải trang kế.

Bốn thứ CỐ Ý không làm:
  • **Không báo vé máy** (`source != "user"`): chủ nhân là Administrator, không có ai để
    cảm ơn và không ai chờ tin.
  • **Không báo khi thiếu lý do**: một thẻ nói "vé của bạn đã Resolved" không cho người
    đọc biết cái gì đã đổi — đó là tiếng ồn, và tiếng ồn làm người ta tắt cả kênh.
  • **Không báo cho chính người vừa đóng vé** — kỹ thuật đóng vé của chính mình thì đã biết.
  • **Không bao giờ để lỗi ở đây làm hỏng lượt đóng vé**: bọc try/except + log.
"""

import frappe
from frappe.utils import add_days, now_datetime

HAN_NGAY = 14
TRANG_THAI_BAO = ("Resolved", "Wontfix")


def _ly_do(ve) -> str:
	"""Lý do đóng vé: `status_note` trước, không có thì lấy Comment MỚI NHẤT.

	Script đóng vé (`feedback-ducan.sh dong/bo-qua`) ghi lý do bằng `add_comment`, còn
	người đóng trong Desk thì gõ vào `status_note`. Đọc một nguồn là mất nửa số ca.
	"""
	note = (ve.get("status_note") or "").strip()
	if note:
		return note
	cmt = frappe.db.sql("""
		SELECT content FROM `tabComment`
		WHERE comment_type = 'Comment' AND reference_doctype = 'Feedback Comment'
		  AND reference_name = %s
		ORDER BY creation DESC LIMIT 1""", (ve.name,))
	if not cmt:
		return ""
	import re
	return re.sub(r"<[^>]+>", " ", cmt[0][0] or "").replace("&nbsp;", " ").strip()


def _duong_dan(ve) -> str:
	"""Link mở ĐÚNG chỗ vừa đổi. Không có link thì thẻ chỉ là tiếng ồn — nhưng vẫn báo,
	vì người gõ vé vẫn cần biết việc của họ đã xong."""
	man = (ve.get("screen_id") or "").strip()
	return man if man.startswith("#/") else ""


def _tieu_de(ve, ly_do: str) -> str:
	viec = (ve.get("message") or "").strip().splitlines()[0] if ve.get("message") else ""
	viec = viec[:70] + ("…" if len(viec) > 70 else "")
	if ve.status == "Wontfix":
		return f"Về góp ý của anh/chị: {viec}" if viec else "Về góp ý của anh/chị"
	return f"Đã xử lý xong: {viec}" if viec else "Góp ý của anh/chị đã được xử lý"


def can_bao(ve) -> tuple:
	"""(có báo không, lý do KHÔNG báo). Tách khỏi hàm ghi để test được từng nhánh."""
	if ve.status not in TRANG_THAI_BAO:
		return False, "trạng thái không phải đã xử lý"
	if (ve.get("source") or "") != "user":
		return False, "vé máy — không có người gõ để báo"
	nguoi = ve.get("owner") or ""
	if nguoi in ("Administrator", "Guest", ""):
		return False, "không có người nhận thật"
	if nguoi == frappe.session.user:
		return False, "người đóng vé chính là người gõ vé"
	if not frappe.db.get_value("User", nguoi, "enabled"):
		return False, "tài khoản đã tắt"
	if frappe.db.exists("Feedback Notice", {"nguon_ve": ve.name}):
		return False, "đã báo cho vé này rồi"
	if not _ly_do(ve):
		return False, "chưa có lý do xử lý — thẻ rỗng là tiếng ồn"
	return True, ""


def bao_ve_da_xu_ly(ve) -> str | None:
	"""Dựng thẻ thông báo cho người gõ vé. Trả tên thẻ, hoặc None nếu không báo."""
	nen, _vi_sao = can_bao(ve)
	if not nen:
		return None
	ly_do = _ly_do(ve)
	tb = frappe.get_doc({
		"doctype": "Feedback Notice",
		"tieu_de": _tieu_de(ve, ly_do),
		"noi_dung": ly_do,
		"duong_dan": _duong_dan(ve),
		"pham_vi": "Một người",
		"nguon_ve": ve.name,
		"cam_on_ai": ve.owner,
		"project": ve.get("project"),
		"bat_dau": now_datetime(),
		"het_han": add_days(now_datetime(), HAN_NGAY),
		"dang_bat": 1,
	})
	tb.append("cac_nguoi", {"user": ve.owner})
	tb.insert(ignore_permissions=True)
	return tb.name


def dang_bat() -> bool:
	"""Công tắc `Feedback Settings.tu_dong_bao_ve`. Thiếu dòng = BẬT (mặc định của field).

	`get_single_value` trả **0** cho CẢ HAI trường hợp "chưa ai lưu Single lần nào" và "đã
	tắt", nên dùng nó ở đây làm tính năng câm ngay từ đầu trên mọi site đang chạy: field
	vừa thêm thì `tabSingles` chưa có dòng nào cả. Đo trên bench dev 27/08 — đóng vé xong
	0 thẻ, không lỗi, không dấu vết. Hỏi thẳng `tabSingles` mới phân biệt được hai ca.
	"""
	dong = frappe.db.sql("""SELECT value FROM `tabSingles`
	                        WHERE doctype = 'Feedback Settings' AND field = 'tu_dong_bao_ve'
	                        LIMIT 1""")
	if not dong:
		return True                       # chưa ai chạm tới công tắc ⇒ theo mặc định của field
	return bool(frappe.utils.cint(dong[0][0]))


def thu_bao(ve) -> None:
	"""Điểm gọi từ controller. KHÔNG bao giờ được làm hỏng lượt đóng vé."""
	try:
		if not dang_bat():
			return
		bao_ve_da_xu_ly(ve)
	except Exception:
		frappe.log_error(title=f"bao_ve_da_xu_ly {ve.name}", message=frappe.get_traceback())
