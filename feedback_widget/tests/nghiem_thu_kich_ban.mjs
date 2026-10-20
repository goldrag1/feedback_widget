/**
 * Nghiệm thu KỊCH BẢN MÀN bằng Chrome thật (plan Task 9 Step 2, spec §14).
 *
 * Dựng một kịch bản thử trên danh sách ToDo cho một người thử MỚI, rồi đo đúng những gì người
 * đó thấy: thẻ hướng dẫn tự bật, viền sáng ôm đúng phần tử; thẻ trỏ selector hỏng vẫn hiện
 * (chỉ chữ) và ghi `Feedback Event kind='loi'`; menu nút 💬 có 🎯/🏅/🏆; thẻ mục tiêu liệt kê
 * bước; thẻ nhắc có nút "Để mai", bấm thì biến mất và máy chủ ghi tạm hoãn; khay không tràn ngang
 * ở 390px; console không có lỗi của widget.
 *
 * Mirror (mặc định — tự bật `kb_bat` rồi trả lại giá trị cũ):
 *   DISPLAY=:1 node apps/feedback_widget/feedback_widget/tests/nghiem_thu_kich_ban.mjs
 * Prod (sau deploy, `kb_bat` đã bật; người thử tạo rồi xoá):
 *   DISPLAY=:1 FBW_MAY=frappeuser@72.61.119.96 FBW_BENCH='~/frappe-bench' FBW_HOST=erp.htsfood.com \
 *     node apps/feedback_widget/feedback_widget/tests/nghiem_thu_kich_ban.mjs
 *
 * Tự dọn ở `finally` (kịch bản, tiến độ, điểm, sự kiện, thẻ nhắc, phiên, người thử), kể cả khi đo hỏng.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const MAY = process.env.FBW_MAY || "local";
const BENCH = process.env.FBW_BENCH || "/home/long/long/frappe-bench-hts";
const HOST = process.env.FBW_HOST || "erp.htsfood.com";
const KEY = process.env.FBW_KEY || `${process.env.HOME}/.ssh/vps_das`;
const GOC = process.env.FBW_URL || (MAY === "local" ? "http://localhost:8003" : `https://${HOST}`);
const PROBE = `${process.env.HOME}/.claude/skills/frappe-headed-qa/prod-probe.sh`;
const NGUOI = "thu-kb-nghiem-thu@kiemthu.local";
const TEN_KB = "THU-KB-NGHIEM-THU todo";
// Màn THỬ là danh sách ToDo — mọi người dùng desk đều mở được, và không kịch bản thật nào
// chiếm nó. Dùng `chot-ton` thì đụng kịch bản thật đợt 1 (luật chống chồng lấn chặn ngay).
const MAN = "List/ToDo*", DUONG = "/app/todo";

const tmp = mkdtempSync(join(tmpdir(), "fbw-kb-nt-"));
function py(code) {
  const f = join(tmp, `p${Date.now()}${Math.random().toString(36).slice(2, 6)}.py`);
  writeFileSync(f, code);
  const args = [PROBE, MAY, BENCH, HOST, f];
  if (MAY !== "local") args.push("-i", KEY);
  return execFileSync("bash", args, { encoding: "utf8" });
}
function lay(ra, nhan) { return (ra.match(new RegExp(nhan + ":(\\S*)")) || [])[1]; }

const DUNG = `
import frappe, secrets
from frappe.utils import now_datetime
U, TEN = ${JSON.stringify(NGUOI)}, ${JSON.stringify(TEN_KB)}
r = frappe.db.sql("SELECT value FROM tabSingles WHERE doctype='Feedback Settings' AND field='kb_bat'")
print("KB_CU:" + (r[0][0] if r and r[0][0] is not None else "NONE"))
frappe.db.sql("DELETE FROM tabSingles WHERE doctype='Feedback Settings' AND field='kb_bat'")
frappe.db.sql("INSERT INTO tabSingles (doctype, field, value) VALUES ('Feedback Settings','kb_bat','1')")
if not frappe.db.exists("User", U):
    frappe.get_doc({"doctype": "User", "email": U, "first_name": "Thử kịch bản", "send_welcome_email": 0,
                    "user_type": "System User"}).insert(ignore_permissions=True)
frappe.get_doc("User", U).add_roles("Stock Manager")
# Site cách ly công ty (hts_multi_company) đòi người dùng có công ty — thiếu thì trang tự 403
# và console đỏ vì lý do không phải của widget.
cty = frappe.db.get_default("company") or frappe.get_all("Company", pluck="name", limit=1)[0]
if not frappe.db.exists("User Permission", {"user": U, "allow": "Company"}):
    frappe.get_doc({"doctype": "User Permission", "user": U, "allow": "Company", "for_value": cty,
                    "apply_to_all_doctypes": 1}).insert(ignore_permissions=True)
k = frappe.get_doc({"doctype": "Feedback Playbook", "ten": TEN, "man": ${JSON.stringify(MAN)}, "duong_dan": ${JSON.stringify(DUONG)},
    "dang_bat": 1, "ly_do": "Phép đo tự động — không phải kịch bản thật.",
    "chang": [{"ma": "lam-quen", "ten": "Làm quen", "thu_tu": 1, "loai": "Một lần", "diem": 30}],
    "buoc": [{"chang": "lam-quen", "mo_ta": "Mở danh sách việc", "loai": "Mở màn", "so_lan": 1},
             {"chang": "lam-quen", "mo_ta": "Gửi một góp ý ngay trên trang", "loai": "Góp ý trên màn", "so_lan": 1}],
    "huong_dan": [{"thu_tu": 1, "tieu_de": "Đây là nút góp ý", "noi_dung": "Thẻ này phải có viền sáng.",
                   "chi_vao": "#khong-co-1; .fbw-fab"},
                  {"thu_tu": 2, "tieu_de": "Chỗ này đã mất", "noi_dung": "Selector hỏng: thẻ chỉ có chữ.",
                   "chi_vao": "#khong-co-cho-nay-dau"}]}).insert(ignore_permissions=True)
frappe.get_doc({"doctype": "Feedback Point", "user": U, "diem": 10, "ly_do": "Bước",
                "khoa": "THU-NT|" + k.name, "nguon_doctype": "Feedback Playbook", "nguon_name": k.name}).insert(ignore_permissions=True)
tb = frappe.get_doc({"doctype": "Feedback Notice", "tieu_de": "THU-NT nhắc: còn 1 bước", "noi_dung": "Phép đo tự động.",
    "duong_dan": ${JSON.stringify(DUONG)}, "pham_vi": "Một người", "cac_nguoi": [{"user": U}], "dang_bat": 1,
    "bat_dau": now_datetime(), "kich_ban": k.name, "loai_nhac": "N1"}).insert(ignore_permissions=True)
sid = secrets.token_hex(20)
frappe.db.sql("""INSERT INTO tabSessions (user,sid,sessiondata,ipaddress,lastupdate,status)
                 VALUES (%s,%s,%s,%s,NOW(),'Active')""", (U, sid, frappe.as_json({"user": U, "ipaddress": "127.0.0.1"}), "127.0.0.1"))
frappe.db.commit()
frappe.clear_cache()
print("KB:" + k.name); print("TB:" + tb.name); print("SID:" + sid)
`;

function donDep(kbCu, ten, tb) {
  return py(`
import frappe
U = ${JSON.stringify(NGUOI)}
for n in frappe.get_all("Feedback Notice", filters={"tieu_de": ["like", "THU-NT%"]}, pluck="name"):
    frappe.db.delete("Feedback Notice Seen", {"thong_bao": n})
    frappe.delete_doc("Feedback Notice", n, force=True, ignore_permissions=True)
for k in frappe.get_all("Feedback Playbook", filters={"ten": ${JSON.stringify(TEN_KB)}}, pluck="name"):
    frappe.db.delete("Feedback Playbook Progress", {"kich_ban": k})
    frappe.delete_doc("Feedback Playbook", k, force=True, ignore_permissions=True)
for dt, f in (("Feedback Point", "user"), ("Feedback Badge Award", "user"), ("Feedback Event", "user"),
              ("Feedback Comment", "submitter_user"), ("Sessions", "user"), ("User Permission", "user")):
    frappe.db.delete(dt, {f: U})
if frappe.db.exists("User", U):
    frappe.delete_doc("User", U, force=True, ignore_permissions=True)
cu = ${JSON.stringify(kbCu)}
if cu is not None:          # null = phần dựng hỏng trước khi đọc được giá trị cũ ⇒ không đụng công tắc
    frappe.db.sql("DELETE FROM tabSingles WHERE doctype='Feedback Settings' AND field='kb_bat'")
    if cu != "NONE":
        frappe.db.sql("INSERT INTO tabSingles (doctype, field, value) VALUES ('Feedback Settings','kb_bat',%s)", cu)
frappe.db.commit(); frappe.clear_cache()
print("CON_LAI:", frappe.db.count("Feedback Playbook", {"ten": ${JSON.stringify(TEN_KB)}}),
      frappe.db.count("Sessions", {"user": U}), frappe.db.exists("User", U) or 0)
`);
}

const pw = (await import(pathToFileURL(`${process.env.HOME}/.claude/skills/gstack/node_modules/playwright/index.js`))).default;
const kq = {};
const loi = [];
let kbCu = null, tenKB = null, tenTB = null;
const browser = await pw.chromium.launch({ headless: false, executablePath: "/usr/bin/google-chrome-stable" });
try {
  const ra = py(DUNG);
  kbCu = lay(ra, "KB_CU"); tenKB = lay(ra, "KB"); tenTB = lay(ra, "TB");
  const SID = lay(ra, "SID");
  if (!SID || !tenKB) throw new Error("dựng dữ liệu thử hỏng:\n" + ra);
  const domain = new URL(GOC).hostname;

  async function moTrang(w, h) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h } });
    await ctx.addCookies([{ name: "sid", value: SID, domain, path: "/" }]);
    const page = await ctx.newPage();
    page.on("pageerror", (e) => loi.push(`[${w}] PAGEERROR: ${e}`));
    page.on("console", (m) => { if (m.type() === "error") loi.push(`[${w}] CONSOLE: ${m.text()}`); });
    await page.goto(`${GOC}${DUONG}`, { waitUntil: "commit", timeout: 90000 });
    await page.waitForFunction(() => window.frappe && frappe.boot && window.FeedbackPlaybook, null, { timeout: 90000 });
    return { ctx, page };
  }

  // ---- 1366px: hướng dẫn, menu, mục tiêu, chúc mừng, nhắc ----
  const { ctx, page } = await moTrang(1366, 850);
  kq.kb_bat_trong_boot = await page.evaluate(() => !!(frappe.boot.feedback_widget || {}).kb_bat);
  await page.waitForSelector('.fbw-kb-hd[data-kb-the="1"]', { timeout: 20000 });
  kq.hd_tu_bat = true;
  await page.waitForTimeout(600);   // thẻ đặt lại vị trí sau khi cuộn mượt xong
  kq.hd_vien_om_phan_tu = await page.evaluate(() => {
    const v = document.querySelector(".fbw-kb-vien");
    // Đích là chính nút 💬: luôn hiện trên mọi màn, nên phép đo không phụ thuộc bố cục của
    // trang chủ (chot-ton giấu `.page-head` — đo 20/10, thẻ trỏ `.page-title` rơi về chữ).
    const t = document.querySelector(".fbw-fab");
    if (!v || !t) return false;
    const a = v.getBoundingClientRect(), b = t.getBoundingClientRect();
    const om = a.left <= b.left + 1 && a.top <= b.top + 1 && a.right >= b.right - 1 && a.bottom >= b.bottom - 1;
    if (!om) window.__kb_do = { vien: [a.left, a.top, a.right, a.bottom], dich: [b.left, b.top, b.right, b.bottom], cls: t.className };
    return om;
  });
  if (!kq.hd_vien_om_phan_tu) kq.hd_vien_do = await page.evaluate(() => window.__kb_do || {
    vien: !!document.querySelector(".fbw-kb-vien"), toi: !!document.querySelector(".fbw-kb-man-toi"),
    fab: !!document.querySelector(".fbw-fab"), route: location.pathname });
  kq.hd_so_the = await page.textContent(".fbw-kb-hd .fbw-kb-so");
  await page.click('.fbw-kb-hd button:has-text("Tiếp")');
  await page.waitForSelector('.fbw-kb-hd[data-kb-the="2"]', { timeout: 5000 });
  kq.the_hong_chi_chu = await page.evaluate(() => !document.querySelector(".fbw-kb-vien") && !!document.querySelector(".fbw-kb-man-toi"));
  await page.click('.fbw-kb-hd button:has-text("Xong")');
  await page.waitForTimeout(800);
  kq.hd_dong_sach = await page.evaluate(() => !document.querySelector(".fbw-kb-hd, .fbw-kb-vien, .fbw-kb-man-toi"));

  kq.chuc_mung_hien = await page.locator('[data-kb="chuc-mung"]').count() > 0;

  // Thẻ nhắc có "Để mai"; bấm thì biến mất.
  await page.waitForSelector(`#fbw-thong-bao-lop [data-tb="${tenTB}"] [data-de-mai]`, { timeout: 30000 })
    .then(() => { kq.nhac_co_de_mai = true; }).catch(() => { kq.nhac_co_de_mai = false; });
  if (kq.nhac_co_de_mai) {
    await page.click(`#fbw-thong-bao-lop [data-tb="${tenTB}"] [data-de-mai]`);
    await page.waitForTimeout(300);
    kq.nhac_bien_mat = (await page.locator(`#fbw-thong-bao-lop [data-tb="${tenTB}"]`).count()) === 0;
  }

  // Lô sự kiện "mở màn" lên máy chủ rồi hỏi lại (mirror không có worker chấm nền; `cua_toi`
  // tự chấm trước khi trả).
  await page.evaluate(() => { try { window.__fbw_instance__._flushEvents(); } catch (e) {} });
  await page.waitForTimeout(1500);
  await page.evaluate(() => window.FeedbackPlaybook.lamMoi());
  await page.waitForTimeout(1500);
  // Menu nút 💬.
  kq.mot_chong_the = await page.evaluate(() => document.querySelectorAll(".fbw-kb-the").length === 0
    || !!document.querySelector("#fbw-thong-bao-lop .fbw-kb-the"));
  await page.click(".fbw-fab");
  await page.waitForSelector(".fbw-menu.fbw-open", { timeout: 5000 });
  kq.menu = await page.$$eval(".fbw-menu .fbw-menu-item", (xs) => xs.map((x) => x.dataset.id));
  kq.menu_du_3_loi = ["kich-ban-muc-tieu", "kich-ban-thanh-tich", "kich-ban-bang-vang"].every((i) => kq.menu.includes(i));
  await page.click('.fbw-menu-item[data-id="kich-ban-muc-tieu"]');
  await page.waitForSelector('[data-kb="muc-tieu"]', { timeout: 5000 });
  kq.muc_tieu_so_buoc = await page.locator('[data-kb="muc-tieu"] .fbw-kb-buoc').count();
  kq.muc_tieu_buoc_mo_man_xong = await page.locator('[data-kb="muc-tieu"] .fbw-kb-buoc[data-xong="1"]').count() >= 1;
  await page.keyboard.press("Escape");
  await page.evaluate(() => window.FeedbackPlaybook.moThanhTich());
  await page.waitForSelector('[data-kb="thanh-tich"] .fbw-kb-thanh', { timeout: 10000 });
  kq.thanh_tich_hien = true;
  await page.evaluate(() => window.FeedbackPlaybook.moBangVang());
  await page.waitForSelector('[data-kb="bang-vang"] table, [data-kb="bang-vang"] .fbw-kb-phu', { timeout: 10000 });
  kq.bang_vang_hien = true;
  kq.bang_vang_khong_email = !(await page.textContent('[data-kb="bang-vang"]')).includes("@");
  await page.keyboard.press("Escape");
  // Đợi lô sự kiện (có sự kiện `loi`) lên máy chủ.
  await page.evaluate(() => { try { window.__fbw_instance__._flushEvents(); } catch (e) {} });
  await page.waitForTimeout(1500);
  await ctx.close();

  // ---- 390px: khay mục tiêu không tràn ngang ----
  const m = await moTrang(390, 844);
  await m.page.waitForFunction(() => window.FeedbackPlaybook.coKichBan(), null, { timeout: 20000 });
  await m.page.evaluate(() => window.FeedbackPlaybook.moMucTieu());
  await m.page.waitForSelector('[data-kb="muc-tieu"]', { timeout: 5000 });
  kq.dt_khay = await m.page.evaluate(() => {
    const r = document.querySelector('[data-kb="muc-tieu"]').getBoundingClientRect();
    const nut = [...document.querySelectorAll('[data-kb="muc-tieu"] .fbw-kb-nut')].map((b) => Math.round(b.getBoundingClientRect().height));
    return { trai: Math.round(r.left), phai: Math.round(r.right), cuon_ngang: document.scrollingElement.scrollWidth, nut_thap_nhat: Math.min(...nut) };
  });
  kq.dt_khong_tran = kq.dt_khay.phai <= 390 && kq.dt_khay.trai >= 0 && kq.dt_khay.nut_thap_nhat >= 44;
  await m.ctx.close();

  const sv = py(`
import frappe
U, KB = ${JSON.stringify(NGUOI)}, ${JSON.stringify(tenKB)}
print("LOI_EVENT:" + str(frappe.db.count("Feedback Event", {"user": U, "kind": "loi", "message": "kich-ban-chi-vao-mat:" + KB + ":2"})))
print("HD:" + str(frappe.db.get_value("Feedback Playbook Progress", {"kich_ban": KB, "user": U}, "huong_dan")).replace(" ", "_"))
print("TAM_HOAN:" + str(frappe.db.get_value("Feedback Notice Seen", {"thong_bao": ${JSON.stringify(tenTB)}, "user": U}, "tam_hoan")))
print("DA_BAO:" + str(frappe.db.count("Feedback Point", {"user": U, "da_bao": 0})))
`);
  kq.su_kien_loi_ghi_so = Number(lay(sv, "LOI_EVENT")) >= 1;
  kq.huong_dan_trang_thai = lay(sv, "HD");
  kq.nhac_tam_hoan_ghi_so = lay(sv, "TAM_HOAN") === "1";
  kq.chuc_mung_da_danh_dau = lay(sv, "DA_BAO") === "0";
} finally {
  try { console.log("dọn:", donDep(kbCu, tenKB, tenTB).trim().split("\n").slice(-1)[0]); }
  catch (e) { console.log("!! DỌN HỎNG — xoá tay kịch bản/người thử:", e.message); }
  rmSync(tmp, { recursive: true, force: true });
  await browser.close();
}

const loiWidget = loi.filter((l) => /fbw|kich|FeedbackPlaybook|feedback_widget/i.test(l) || l.includes("PAGEERROR"));
kq.loi_console_tong = loi.length;
kq.loi_console_cua_widget = loiWidget.length;
console.log(JSON.stringify(kq, null, 2));
if (loi.length) console.log("console (tham khảo):", loi.slice(0, 8));
const dat = kq.hd_tu_bat && kq.hd_vien_om_phan_tu && kq.the_hong_chi_chu && kq.hd_dong_sach && kq.chuc_mung_hien
  && kq.nhac_co_de_mai && kq.nhac_bien_mat && kq.menu_du_3_loi && kq.muc_tieu_so_buoc === 2 && kq.muc_tieu_buoc_mo_man_xong
  && kq.mot_chong_the && kq.thanh_tich_hien && kq.bang_vang_hien && kq.bang_vang_khong_email && kq.dt_khong_tran && kq.su_kien_loi_ghi_so
  && kq.huong_dan_trang_thai === "Đã_xem" && kq.nhac_tam_hoan_ghi_so && kq.chuc_mung_da_danh_dau && !loiWidget.length;
console.log(dat ? "ĐẠT — kịch bản màn chạy đúng trên trình duyệt thật" : "KHÔNG ĐẠT — xem số ở trên");
process.exit(dat ? 0 : 1);
