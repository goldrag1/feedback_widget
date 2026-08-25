"""Gieo cài đặt mặc định MỘT LẦN, để màn Cài đặt nói đúng thứ hệ đang làm.

`cai_dat()` đã tự lùi về mặc định khi chưa có dòng nào, nên hệ chạy đúng kể cả không có
patch này. Nhưng màn Cài đặt lúc ấy hiện các ô Check TRỐNG trong khi tính năng đang BẬT —
giao diện nói ngược với hành vi, và người vận hành sẽ tin vào giao diện.
"""

import frappe

from feedback_widget.cai_dat import MAC_DINH


def execute():
    doc = frappe.get_single("Feedback Widget Settings")
    da_khai = {r[0] for r in frappe.db.sql(
        """SELECT field FROM `tabSingles` WHERE doctype='Feedback Widget Settings'""")}
    for k, v in MAC_DINH.items():
        if k not in da_khai:
            doc.set(k, v)
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
