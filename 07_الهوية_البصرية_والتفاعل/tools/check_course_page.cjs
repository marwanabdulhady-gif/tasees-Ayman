/* L1 — فحص مشغّل الدورة course.html في jsdom (بلا لقطات).
     node 07_الهوية_البصرية_والتفاعل/tools/check_course_page.cjs
   يتحقق من: تحميل ملفي الفهرس المولَّدين، ٣٢ طوبة + صفَّي تنفس + بطاقتين للتاج،
   ٣٦ بطاقة أسبوع، وأن كل رابط داخلي يفتح ملفًا موجودًا على القرص.
   إن لم يكن jsdom مثبتًا يطبع skip ويخرج بـ0 (node_modules غير محفوظة في المستودع). */
const fs = require("fs");
const path = require("path");
let JSDOM, VirtualConsole;
try { ({ JSDOM, VirtualConsole } = require("jsdom")); }
catch (e) { console.log("skip course.html: jsdom غير مثبت (npm install --no-save jsdom)"); process.exit(0); }

const ROOT = path.resolve(__dirname, "..", "..");
const FILE = path.join(ROOT, "course.html");

const errs = [];
const vc = new VirtualConsole();
const KNOWN = /Could not load link|Not implemented: window\.(scrollTo|scroll)|Could not parse CSS/i;
vc.on("jsdomError", (e) => { const l = String(e.message).split("\n")[0]; if (!KNOWN.test(l)) errs.push(l); });
vc.on("error", (...a) => errs.push(a.join(" ")));

const dom = new JSDOM(fs.readFileSync(FILE, "utf8"), {
  runScripts: "dangerously", resources: "usable", virtualConsole: vc,
  url: "file://" + FILE, pretendToBeVisual: true,
});
const w = dom.window;

setTimeout(() => {
  const d = w.document;
  const q = (s) => d.querySelectorAll(s).length;
  const want = (cond, msg) => { if (!cond) errs.push(msg); };

  want(q("#col .brick[data-week]") === 32, `طوبات العمود ${q("#col .brick[data-week]")} بدل ٣٢`);
  want(q("#col .breath[data-week]") === 2, `صفوف التنفس ${q("#col .breath[data-week]")} بدل ٢`);
  want(q("#cap-row button") === 2, "التاج لازم زرَّين (٣٥ و٣٦)");
  want(q(".card") === 36, `بطاقات الأسابيع ${q(".card")} بدل ٣٦`);
  want(q("#col svg") === 1, "العمود لم يُحقن (course-column.js)");

  const broken = [...d.querySelectorAll("a[href]")]
    .map((a) => a.getAttribute("href"))
    .filter((h) => h && !h.startsWith("#") && !/^(https?:|mailto:)/.test(h) && !h.startsWith("index.html#"))
    .filter((h) => !fs.existsSync(path.join(ROOT, decodeURI(h.split("#")[0]))));
  want(!broken.length, "روابط لا تفتح ملفًا: " + [...new Set(broken)].slice(0, 3).join(", "));

  const atlasLinks = [...d.querySelectorAll('a[href^="index.html#"]')].map((a) => a.getAttribute("href").slice(11));
  want(atlasLinks.length >= 12, "روابط الأطلس العميقة " + atlasLinks.length + " — متوقع ≥١٢");

  w.close();
  if (errs.length) { console.log("FAIL course.html: " + errs.slice(0, 4).join(" | ")); process.exit(1); }
  console.log(`ok course.html: 32 طوبة · 2 تنفس · 36 بطاقة · ${atlasLinks.length} رابط أطلس · 0 أخطاء (jsdom)`);
  process.exit(0);
}, 700);
