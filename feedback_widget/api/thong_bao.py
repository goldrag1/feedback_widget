"""Thông báo đẩy: lấy cái CHƯA XEM của chính mình, và đánh dấu đã xem.

Hai endpoint, không hơn. Widget hỏi lúc mở app (qua boot, khi phần nối dây lên) hoặc gọi
thẳng; người dùng chỉ thấy thông báo gửi cho MÌNH.
"""

import frappe
from frappe.utils import now_datetime

HAN_MAC_DINH = 14


def _cua_toi(user: str) -> list:
	"""Thông báo còn hiệu lực mà `user` nằm trong phạm vi. Đọc bằng SQL một lượt.

	KHÔNG dùng `frappe.get_all` với quyền mặc định: DocType này chỉ System Manager đọc
	được (cố ý), còn người dùng thường vẫn phải nhận được thông báo gửi cho họ. Bù lại,
	phạm vi ở đây là cổng THẬT — mọi nhánh đều lọc theo chính `user` truyền vào.
	"""
	vai = frappe.get_roles(user) or []
	ph = ", ".join(["%s"] * len(vai)) or "''"
	# `NOW()` của MySQL CẮT phần giây lẻ, còn `bat_dau` do Python ghi có micro-giây: một
	# thông báo vừa tạo lúc 17:08:41.738 sẽ bị coi là "chưa tới giờ" cho tới 17:08:42.
	# Vô hại trên sản phẩm nhưng làm test đỏ mọi lần — và nó là loại lệch âm thầm đúng
	# kiểu ta hay đi tìm nhầm chỗ. Truyền mốc từ Python để hai bên cùng độ chính xác.
	bay_gio = frappe.utils.now_datetime()
	return frappe.db.sql(f"""
		SELECT n.name, n.tieu_de, n.noi_dung, n.duong_dan, n.cam_on_ai, n.nguon_ve, n.creation, n.pham_vi
		  FROM `tabFeedback Notice` n
		 WHERE n.dang_bat = 1
		   AND (n.bat_dau IS NULL OR n.bat_dau <= %s)
		   AND (n.het_han IS NULL OR n.het_han >= %s)
		   AND (
			 n.pham_vi = 'Tất cả'
			 OR (n.pham_vi = 'Một người' AND EXISTS (
				 SELECT 1 FROM `tabFeedback Notice User` u
				  WHERE u.parent = n.name AND u.user = %s))
			 OR (n.pham_vi = 'Nhóm vai' AND EXISTS (
				 SELECT 1 FROM `tabFeedback Role Item` r
				  WHERE r.parent = n.name AND r.parenttype = 'Feedback Notice'
				    AND r.role IN ({ph})))
		   )
		   AND NOT EXISTS (
			 SELECT 1 FROM `tabFeedback Notice Seen` s
			  WHERE s.thong_bao = n.name AND s.user = %s)
		 ORDER BY n.creation DESC
		 LIMIT 5
	""", [bay_gio, bay_gio, user] + vai + [user], as_dict=True)


@frappe.whitelist()
def cua_toi() -> list:
	"""Thông báo chưa xem của NGƯỜI ĐANG ĐĂNG NHẬP. Khách vãng lai: không có gì."""
	user = frappe.session.user
	if not user or user == "Guest":
		return []
	return _cua_toi(user)


@frappe.whitelist()
def da_xem(thong_bao: str, da_bam: int = 0) -> dict:
	"""Đánh dấu ĐÃ XEM — chỉ gọi khi người dùng BẤM (xem thử / đóng), không phải khi nó
	vừa hiện ra: thông báo biến mất vĩnh viễn vì người ta lướt qua thì bằng không có."""
	user = frappe.session.user
	if not user or user == "Guest":
		return {"ok": False}
	if not frappe.db.exists("Feedback Notice", thong_bao):
		return {"ok": False, "loi": "không có thông báo này"}
	# Chỉ ghi cho CHÍNH mình; không cho ghi hộ người khác dù có gửi tham số.
	da_co = frappe.db.get_value("Feedback Notice Seen",
	                            {"thong_bao": thong_bao, "user": user}, "name")
	if da_co:
		if int(da_bam or 0):
			frappe.db.set_value("Feedback Notice Seen", da_co, "da_bam", 1)
	else:
		frappe.get_doc({"doctype": "Feedback Notice Seen", "thong_bao": thong_bao,
		                "user": user, "xem_luc": now_datetime(),
		                "da_bam": 1 if int(da_bam or 0) else 0}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


def dem_da_xem(thong_bao: str) -> dict:
	"""Số đo của một thông báo — người sửa đọc để biết có ai bấm không (không whitelist)."""
	return {
		"da_xem": frappe.db.count("Feedback Notice Seen", {"thong_bao": thong_bao}),
		"da_bam": frappe.db.count("Feedback Notice Seen", {"thong_bao": thong_bao, "da_bam": 1}),
	}
