/* Opens built week pages in Chromium, walks every screen, and fails on any console error.

     node 07_الهوية_البصرية_والتفاعل/tools/check_week_page.cjs 18          (one week)
     node 07_الهوية_البصرية_والتفاعل/tools/check_week_page.cjs all         (every built page)
     node 07_الهوية_البصرية_والتفاعل/tools/check_week_page.cjs 18 --shots  (also saves a screenshot of every screen)

   Screenshots go to 07_الهوية_البصرية_والتفاعل/screenshots/weeks/wNN-SS.png — attach some to the pull request. */
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..", "..");
const UNITS = path.join(ROOT, "02_الوحدات_التعليمية");
const SHOTS = path.join(__dirname, "..", "screenshots", "weeks");

function pages() {
  const out = {};
  for (const u of fs.readdirSync(UNITS)) {
    const d = path.join(UNITS, u, "04_التفاعلي");
    if (!u.startsWith("v0_4_") || !fs.existsSync(d)) continue;
    for (const f of fs.readdirSync(d)) {
      const m = f.match(/^week-(\d\d)\.html$/);
      if (m) out[+m[1]] = path.join(d, f);
    }
  }
  return out;
}

(async () => {
  const args = process.argv.slice(2);
  const shots = args.includes("--shots");
  const all = pages();
  const wanted = args.includes("all") ? Object.keys(all).map(Number) : args.filter((a) => /^\d+$/.test(a)).map(Number);
  if (!wanted.length) { console.log("usage: check_week_page.cjs <week…|all> [--shots]"); process.exit(2); }
  const browser = await chromium.launch();
  let failed = 0;
  for (const n of wanted.sort((a, b) => a - b)) {
    const f = all[n];
    if (!f) { console.log(`FAIL week ${n}: no page — run build_week_pages.py ${n} first`); failed++; continue; }
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errs = [];
    page.on("pageerror", (e) => errs.push(e.message));
    page.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); });
    await page.goto("file://" + f);
    await page.waitForTimeout(300);
    const week = await page.evaluate(() => document.documentElement.dataset.week);
    if (week !== "w" + String(n).padStart(2, "0")) errs.push(`data-week is «${week}», expected w${String(n).padStart(2, "0")}`);
    let screens = 1;
    for (let i = 0; i < 20; i++) {
      if (shots) {
        fs.mkdirSync(SHOTS, { recursive: true });
        await page.screenshot({ path: path.join(SHOTS, `w${String(n).padStart(2, "0")}-${String(screens).padStart(2, "0")}.png`) });
      }
      const next = await page.$('button:has-text("التالي"), button:has-text("يلا بينا")');
      if (!next) break;
      try { await next.click({ timeout: 1000 }); } catch (e) { break; }
      await page.waitForTimeout(120);
      screens++;
    }
    const wide = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    if (wide) errs.push("horizontal scroll");
    if (errs.length) { failed++; console.log(`FAIL week ${n}: ${errs.slice(0, 3).join(" | ")}`); }
    else console.log(`ok week ${n}: ${screens} screens, 0 console errors`);
    await page.close();
  }
  await browser.close();
  process.exit(failed ? 1 : 0);
})();
