frappe.ui.form.on("Feedback Mission", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.kich_ban) return;
		frm.add_custom_button(__("Tiến độ kịch bản"), () =>
			frappe.set_route("query-report", "Tien Do Kich Ban", { kich_ban: frm.doc.kich_ban }));
	},
});
