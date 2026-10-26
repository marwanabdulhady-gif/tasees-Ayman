/* Fallback for check_week_page.cjs when Chromium cannot be installed (no root / CDN blocked).

     node 07_الهوية_البصرية_والتفاعل/tools/check_week_page_dom.cjs 19
     node 07_الهوية_البصرية_والتفاعل/tools/check_week_page_dom.cjs all

   يفتح الصفحة في jsdom، يشغّل نفس سكربتات الصفحة، ويمشي على الشاشات بزر «التالي»،
   ويفشل على أي خطأ JS أو console.error. لا يلتقط لقطات ولا يقيس العرض الأفقي —
   ده اللي بيعمله فاحص Chromium. إن اشتغل Chromium فهو الأصل، وده بديل فقط.
*/
const fs = require("fs");
const path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");

const ROOT = path.resolve(__dirname, "..", "..");
const UNITS = path.join(ROOT, "02_الوحدات_التعليمية");

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

// عيوب jsdom المعروفة وليست أخطاء صفحة: تحميل خطوط الشبكة (الصفحة تعمل أوفلاين بالخط البديل)،
// وscrollTo غير المنفذ. Chromium لا يعاني منها، فيُتجاهل هذان النوعان هنا فقط.
const KNOWN_JSDOM_GAP = /Could not load link|Not implemented: window\.(scrollTo|scroll)|Could not parse CSS/i;

async function check(n, file) {
  const errs = [];
  const vc = new VirtualConsole();
  const push = (m) => {
    const line = String(m).split("\n")[0];
    if (!KNOWN_JSDOM_GAP.test(line)) errs.push(line);
  };
  vc.on("jsdomError", (e) => push(e.message));
  vc.on("error", (...a) => push(a.join(" ")));
  const dom = new JSDOM(fs.readFileSync(file, "utf8"), {
    runScripts: "dangerously",
    resources: "usable",
    virtualConsole: vc,
    url: "file://" + file,
    pretendToBeVisual: true,
  });
  const { window } = dom;
  await new Promise((r) => setTimeout(r, 400));

  const week = window.document.documentElement.dataset.week;
  if (week !== "w" + String(n).padStart(2, "0"))
    errs.push(`data-week is «${week}», expected w${String(n).padStart(2, "0")}`);

  const block = window.document.querySelector('script[type="application/json"]#week');
  let screens = 0;
  try {
    const data = JSON.parse(block.textContent);
    screens = (data.screens || []).length;
    if (!screens) errs.push("كتلة JSON بلا شاشات");
  } catch (e) {
    errs.push("كتلة JSON غير صالحة: " + e.message);
  }

  // المشي على الشاشات: نفس زر الفاحص الأصلي.
  let seen = 1;
  for (let i = 0; i < 20; i++) {
    const btn = [...window.document.querySelectorAll("button")].find((b) =>
      /التالي|يلا بينا/.test(b.textContent || "")
    );
    if (!btn) break;
    btn.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 30));
    seen++;
  }
  if (screens && seen < screens)
    errs.push(`زر «التالي» وقف عند الشاشة ${seen} من ${screens}`);

  window.close();
  if (errs.length) {
    console.log(`FAIL week ${n}: ${errs.slice(0, 3).join(" | ")}`);
    return false;
  }
  console.log(`ok week ${n}: ${seen} screens reached, 0 console errors (jsdom)`);
  return true;
}

(async () => {
  const args = process.argv.slice(2);
  const all = pages();
  const wanted = args.includes("all")
    ? Object.keys(all).map(Number)
    : args.filter((a) => /^\d+$/.test(a)).map(Number);
  if (!wanted.length) {
    console.log("usage: check_week_page_dom.cjs <week…|all>");
    process.exit(2);
  }
  let failed = 0;
  for (const n of wanted.sort((a, b) => a - b)) {
    const f = all[n];
    if (!f) {
      console.log(`FAIL week ${n}: no page — run build_week_pages.py ${n} first`);
      failed++;
      continue;
    }
    if (!(await check(n, f))) failed++;
  }
  process.exit(failed ? 1 : 0);
})();
