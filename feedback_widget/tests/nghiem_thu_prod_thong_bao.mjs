/**
 * Nghiệm thu TRÊN PROD ba việc, bằng trình duyệt thật và KHÔNG tự cắm thêm tai nghe nào:
 * widget có tự cắm tai nghe realtime không · thẻ hiện sau bao nhiêu giây · bấm "Xem thử →"
 * trên thẻ trỏ TRANG DESK có đi đúng chỗ không (FB-2026-01430).
 *
 * Vì sao cần: bản 27/08 xanh mọi test mà trên prod `listeners("fbw_thong_bao_moi")` = 0
 * (widget gọi `frappe.realtime.on()` ở giây 2,6 trong khi socket mãi giây 3,1 mới dựng,
 * và `on()` của Frappe im lặng bỏ qua khi chưa có socket). Chỉ số đo trên máy chủ thật
 * mới phân biệt được "đã sửa" với "vẫn câm".
 *
 * Chạy SAU KHI deploy, từ gốc bench:
 *   DISPLAY=:1 ~/.claude/skills/frappe-headed-qa/with-session.sh \
 *     frappeuser@72.61.119.96 '~/frappe-bench-nextstar' ducan.nextstar-erp.com \
 *     ~/.ssh/vps_das node apps/feedback_widget/feedback_widget/tests/nghiem_thu_prod_thong_bao.mjs
 *
 * Nó tự dọn: thông báo thử được xoá ở cuối (kể cả khi đo hỏng), phiên do with-session.sh xoá.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const SID = process.env.FRAPPE_SID || process.argv.at(-1);
const HOST = process.env.FBW_HOST || "ducan.nextstar-erp.com";
const MAY = process.env.FBW_MAY || "frappeuser@72.61.119.96";
const BENCH = process.env.FBW_BENCH || "~/frappe-bench-nextstar";
const KEY = process.env.FBW_KEY || `${process.env.HOME}/.ssh/vps_das`;
const PROBE = `${process.env.HOME}/.claude/skills/frappe-headed-qa/prod-probe.sh`;
const TIEU_DE = "THU-NGHIEM-THU — thông báo tới ngay (xoá sau)";

const tmp = mkdtempSync(join(tmpdir(), "fbw-nt-"));
function chayTrenProd(py) {
  const f = join(tmp, `p${Date.now()}${Math.random().toString(36).slice(2, 6)}.py`);
  writeFileSync(f, py);
  return execFileSync("bash", [PROBE, MAY, BENCH, HOST, f, "-i", KEY], { encoding: "utf8" });
}

const pw = (await import(pathToFileURL(`${process.env.HOME}/.claude/skills/gstack/node_modules/playwright/index.js`))).default;
const browser = await pw.chromium.launch({ headless: false, executablePath: "/usr/bin/google-chrome-stable" });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 950 } });
await ctx.addCookies([{ name: "sid", value: SID, domain: HOST, path: "/" }]);
const page = await ctx.newPage();
const loi = [];
page.on("pageerror", (e) => loi.push("PAGEERROR: " + e));
page.on("console", (m) => { if (m.type() === "error") loi.push("CONSOLE: " + m.text()); });

let tenTB = null;
const kq = {};
try {
  const t0 = Date.now();
  await page.goto(`https://${HOST}/app/steel-app`, { waitUntil: "commit", timeout: 90000 });
  await page.waitForFunction(() => document.title && document.title !== "Frappe", null, { timeout: 90000 });

  // 1) Tai nghe phải do CHÍNH WIDGET cắm — script này không đăng ký gì cả.
  await page.waitForFunction(() => {
    try {
      const s = window.frappe && window.frappe.realtime && window.frappe.realtime.socket;
      return !!(s && s.listeners("fbw_thong_bao_moi").length >= 1);
    } catch (e) { return false; }
  }, null, { timeout: 90000 }).catch(() => {});
  kq.giay_den_khi_co_tai_nghe = ((Date.now() - t0) / 1000).toFixed(1);
  kq.so_tai_nghe = await page.evaluate(() => {
    try {
      const s = window.frappe.realtime.socket;
      return s ? s.listeners("fbw_thong_bao_moi").length : -1;
    } catch (e) { return -2; }
  });
  kq.socket_noi = await page.evaluate(() => {
    try { return !!(window.frappe.realtime.socket && window.frappe.realtime.socket.connected); }
    catch (e) { return false; }
  });

  // 2) Tạo thông báo "Một người" cho chính phiên đang mở, rồi đếm giây tới lúc thẻ hiện.
  const ra = chayTrenProd(`
import frappe
d = frappe.get_doc({"doctype": "Feedback Notice",
    "tieu_de": ${JSON.stringify(TIEU_DE)},
    "noi_dung": "Phép đo tự động — không phải thông báo thật.",
    "duong_dan": "/app/feedback-notice",
    "pham_vi": "Một người", "dang_bat": 1,
    "cac_nguoi": [{"user": "Administrator"}]}).insert(ignore_permissions=True)
frappe.db.commit()
print("TB:" + d.name)
`);
  tenTB = (ra.match(/TB:(\S+)/) || [])[1];
  if (!tenTB) throw new Error("không tạo được thông báo thử trên prod:\n" + ra);
  const tTao = Date.now();
  let hienRa = true;
  await page.waitForSelector(`#fbw-thong-bao-lop [data-tb="${tenTB}"]`, { timeout: 120000 })
    .catch(() => { hienRa = false; });
  kq.the_hien_ra = hienRa;
  kq.giay_tu_luc_tao_den_luc_the_hien = hienRa ? ((Date.now() - tTao) / 1000).toFixed(1) : "KHÔNG HIỆN";

  // 3) FB-2026-01430: thẻ trỏ TRANG DESK bấm vào phải đi thật. Trước bản 28/08 nó gán
  // `location.hash` nên URL thành `…#/app/…`, jQuery ném `Syntax error, unrecognized
  // expression` và người bấm đứng nguyên chỗ cũ — đo trên prod: 1/1 lượt bấm hỏng.
  if (hienRa) {
    try {
      await page.click(`#fbw-thong-bao-lop [data-tb="${tenTB}"] button:has-text("Xem thử")`);
      await page.waitForURL(/\/(app|desk)\/feedback-notice/, { timeout: 30000 }).catch(() => {});
      kq.url_sau_khi_bam = page.url();
      kq.bam_di_dung_cho = /\/(app|desk)\/feedback-notice/.test(page.url())
        && !/#\/app\//.test(page.url());
    } catch (e) {
      kq.url_sau_khi_bam = "lỗi khi bấm: " + e.message;
      kq.bam_di_dung_cho = false;
    }
  }
  kq.loi_console = loi.length;
} finally {
  if (tenTB) {
    try {
      chayTrenProd(`
import frappe
frappe.db.delete("Feedback Notice Seen", {"thong_bao": ${JSON.stringify(tenTB)}})
frappe.delete_doc("Feedback Notice", ${JSON.stringify(tenTB)}, force=True, ignore_permissions=True)
frappe.db.commit()
print("CON_LAI:", frappe.db.count("Feedback Notice", {"tieu_de": ${JSON.stringify(TIEU_DE)}}))
`).trim().split("\n").slice(-1).forEach((l) => console.log("dọn:", l));
    } catch (e) { console.log("!! chưa xoá được thông báo thử " + tenTB + ": " + e.message); }
  }
  rmSync(tmp, { recursive: true, force: true });
  await browser.close();
}

console.log(JSON.stringify(kq, null, 2));
if (loi.length) console.log("lỗi trình duyệt:", loi.slice(0, 5));
const dat = kq.so_tai_nghe >= 1 && kq.the_hien_ra === true && kq.bam_di_dung_cho === true;
console.log(dat ? "ĐẠT — widget tự cắm tai nghe, thẻ tới ngay, bấm đi đúng trang" : "KHÔNG ĐẠT — xem số ở trên");
process.exit(dat ? 0 : 1);
