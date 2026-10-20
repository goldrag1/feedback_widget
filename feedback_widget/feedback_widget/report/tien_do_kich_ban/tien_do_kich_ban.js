frappe.query_reports["Tien Do Kich Ban"] = {
	filters: [
		{ fieldname: "kich_ban", label: __("Kịch bản"), fieldtype: "Link", options: "Feedback Playbook" },
		{ fieldname: "user", label: __("Người"), fieldtype: "Link", options: "User" },
		{ fieldname: "dang_ket", label: __("Chỉ người đang kẹt"), fieldtype: "Check" },
	],
};
