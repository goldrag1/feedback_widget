// Lối vào hai báo cáo quản trị (spec §6.7) — app không còn workspace riêng, nên đây là chỗ
// người lập kịch bản chắc chắn đi qua.
frappe.ui.form.on("Feedback Playbook", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Tiến độ kịch bản"), () =>
			frappe.set_route("query-report", "Tien Do Kich Ban", { kich_ban: frm.doc.name }), __("Báo cáo"));
		frm.add_custom_button(__("Màn chưa ai dùng"), () =>
			frappe.set_route("query-report", "Man Chua Ai Dung"), __("Báo cáo"));
	},
});
