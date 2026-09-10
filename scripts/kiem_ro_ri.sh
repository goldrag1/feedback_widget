#!/usr/bin/env bash
# Bộ kiểm của app này chạy trên SITE THẬT, nên một teardown sót là vé rác trong hộp thư
# của chủ dự án — trông y hệt vé thật, không có gì báo động. Phép đo duy nhất bắt được:
# đếm trước, chạy, đếm sau.
#
#     bash apps/feedback_widget/scripts/kiem_ro_ri.sh [site]
set -euo pipefail
BENCH=/home/long/long/frappe-bench-asxh
SITE=${1:-asxh.localhost}
BENCH_BIN=/home/long/.local/bin/bench

dem() {
  cd "$BENCH/sites" && ../env/bin/python -c "
import frappe, sys
frappe.init(site='$SITE', sites_path='$BENCH/sites'); frappe.connect()
print(' '.join(str(frappe.db.count(d)) for d in ('Feedback Comment','Feedback Event','Feedback Notice')))
" 2>/dev/null | tail -1
}

truoc=$(dem)
echo "── trước ── vé/sự kiện/thẻ báo: $truoc"
# `run-tests` chạy HAI bộ (một bộ chạm CSDL, một bộ thuần) và in "Ran N" hai lần —
# `tail -3` chỉ thấy bộ sau, nên một bộ đỏ vẫn trôi qua im lặng.
cd "$BENCH"
ket=$("$BENCH_BIN" --site "$SITE" run-tests --app feedback_widget 2>&1 | sed 's/\x1b\[[0-9;]*m//g')
echo "$ket" | grep -E "^(Ran |OK|FAILED)" || true
if echo "$ket" | grep -qE "^(FAILED|ERROR)"; then
  echo "✘ bộ kiểm ĐỎ — đọc kỹ trước khi tin con số dưới đây" >&2
  exit 1
fi
sau=$(dem)
echo "── sau   ── vé/sự kiện/thẻ báo: $sau"

if [ "$truoc" = "$sau" ]; then
  echo "✔ không rò dòng nào"
else
  echo "✘ RÒ: bộ kiểm để lại dữ liệu trên site thật ($truoc → $sau)" >&2
  exit 1
fi
