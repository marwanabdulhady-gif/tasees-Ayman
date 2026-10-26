// Headless QA for release/islamic-history-atlas.html
// - opened via file:// with ALL network requests blocked (offline test)
// - functional checks for search, navigation, pan/zoom, hotspots, layers, views
// - screenshots for desktop / tablet / mobile / dark mode
// Usage: LD_LIBRARY_PATH=tools/qa/libs/lib node tools/qa/run-qa.mjs
import chromium from "@sparticuz/chromium";
import puppeteer from "puppeteer-core";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const FILE = "file://" + path.join(ROOT, "release", "islamic-history-atlas.html");
const SHOTS = path.join(ROOT, "work", "qa");
fs.mkdirSync(SHOTS, { recursive: true });

const results = []; const errors = []; const blocked = [];
const check = (name, ok, detail = "") => { results.push({ name, ok: !!ok, detail }); console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  — " + detail : ""}`); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({ executablePath: await chromium.executablePath(), args: [...chromium.args, "--no-sandbox", "--allow-file-access-from-files"], headless: true });
async function newPage(w, h, scale = 1) {
  const page = await browser.newPage();
  await page.setViewport({ width: w, height: h, deviceScaleFactor: scale });
  await page.setRequestInterception(true);
  page.on("request", (req) => {
    const u = req.url();
    if (u.startsWith("file:") || u.startsWith("data:") || u.startsWith("blob:")) req.continue();
    else { blocked.push(u); req.abort(); }
  });
  page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
  page.on("console", (m) => { if (m.type() === "error") errors.push("console: " + m.text()); });
  return page;
}
const mapReady = (page, sel = "#viewer-host svg.map-svg") => page.waitForFunction((s) => { const svg = document.querySelector(s); const ld = document.querySelector("#map-loading"); return svg && svg.getAttribute("viewBox") && (!ld || ld.hidden); }, { timeout: 30000 }, sel);

// ---------------- desktop ----------------
const page = await newPage(1440, 900);
let t0 = Date.now();
await page.goto(FILE, { waitUntil: "load" });
await mapReady(page);
check("app loads offline and renders first map", true, `${Date.now() - t0} ms to interactive map`);
check("document is Arabic RTL", await page.evaluate(() => document.documentElement.lang === "ar" && document.documentElement.dir === "rtl"));
const nVector = await page.evaluate(() => document.querySelectorAll("#viewer-host .L-label").length);
check("vector layers present in explorer", nVector > 100, `${nVector} label paths`);
const nHs = await page.evaluate(() => document.querySelectorAll("#viewer-host .hs").length);
check("hotspots rendered for figure 2", nHs > 150, `${nHs} hotspots`);
await page.screenshot({ path: path.join(SHOTS, "01-desktop-explore.png") });

// font actually used
const fontOk = await page.evaluate(async () => { await document.fonts.ready; return document.fonts.check("16px 'IBM Plex Sans Arabic'", "مكة"); });
check("embedded Arabic font available", fontOk);

// zoom buttons
const vb0 = await page.evaluate(() => document.querySelector("#viewer-host svg").getAttribute("viewBox"));
await page.click('[data-act="zoom-in"]'); await sleep(700);
const vb1 = await page.evaluate(() => document.querySelector("#viewer-host svg").getAttribute("viewBox"));
check("zoom in narrows viewBox", parseFloat(vb1.split(" ")[2]) < parseFloat(vb0.split(" ")[2]) * 0.8, `${vb0.split(" ")[2]} → ${vb1.split(" ")[2]}`);
// drag pan
const box = await page.$eval("#viewer-host", (e) => { const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; });
await page.mouse.move(box.x + box.w / 2, box.y + box.h / 2); await page.mouse.down();
await page.mouse.move(box.x + box.w / 2 + 160, box.y + box.h / 2 + 60, { steps: 8 }); await page.mouse.up(); await sleep(400);
const vb2 = await page.evaluate(() => document.querySelector("#viewer-host svg").getAttribute("viewBox"));
check("drag pans the map", vb2.split(" ")[0] !== vb1.split(" ")[0], `x ${vb1.split(" ")[0]} → ${vb2.split(" ")[0]}`);
// wheel zoom
await page.mouse.move(box.x + box.w / 2, box.y + box.h / 2);
await page.mouse.wheel({ deltaY: -400 }); await sleep(500);
const vb3 = await page.evaluate(() => document.querySelector("#viewer-host svg").getAttribute("viewBox"));
check("mouse wheel zooms", parseFloat(vb3.split(" ")[2]) < parseFloat(vb2.split(" ")[2]), `${vb2.split(" ")[2]} → ${vb3.split(" ")[2]}`);
await page.click('[data-act="fit"]'); await sleep(700);
const vb4 = await page.evaluate(() => document.querySelector("#viewer-host svg").getAttribute("viewBox"));
check("fit restores full view", Math.abs(parseFloat(vb4.split(" ")[2]) - parseFloat(vb0.split(" ")[2])) < 2, vb4);

// hotspot click — click centre of the hotspot for «الصين»
const hsBox = await page.evaluate(() => {
  const f = [...document.querySelectorAll("#viewer-host .hs")].find((g) => g.querySelector("title").textContent === "الصين");
  const r = f.querySelector(".hs-shape").getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2, id: f.dataset.id };
});
await page.mouse.click(hsBox.x, hsBox.y); await sleep(900);
const card = await page.evaluate(() => { const c = document.querySelector("#feature-card"); return !c.hidden && c.querySelector("h3").textContent; });
check("clicking a printed label opens its card", card === "الصين", `card: ${card}`);
check("selected hotspot highlighted", await page.evaluate((id) => document.querySelector(`#viewer-host .hs[data-id="${id}"]`).classList.contains("selected"), hsBox.id));
check("deep link updated for selection", await page.evaluate(() => location.hash.includes("/fig/fig-2/p1-")));
await page.screenshot({ path: path.join(SHOTS, "02-desktop-feature.png") });

// layers
await page.click('[data-act="layers"]'); await sleep(200);
await page.click("#layer-label"); await sleep(300);
check("label layer can be hidden", await page.evaluate(() => document.querySelector("#viewer-host svg").classList.contains("hide-label")));
await page.screenshot({ path: path.join(SHOTS, "03-layers-no-labels.png") });
await page.click("#layer-label"); await page.keyboard.press("Escape");

// ---------------- search ----------------
async function search(q) {
  await page.click("#search-input", { clickCount: 3 }); await page.keyboard.press("Backspace");
  await page.type("#search-input", q, { delay: 10 }); await sleep(400);
  return page.evaluate(() => [...document.querySelectorAll("#search-results .result .r-title")].map((e) => e.textContent));
}
let r = await search("مكة");
check("search «مكة» returns all printed occurrences", r.filter((t) => t === "مكة").length >= 3, r.slice(0, 6).join(" | "));
r = await search("اسكندرية");
check("alef-insensitive: «اسكندرية» → الإسكندرية / الاسكندرية", r.some((t) => t === "الإسكندرية") && r.some((t) => t === "الاسكندرية"), r.slice(0, 4).join(" | "));
r = await search("الاحواز");
check("hamza-insensitive: «الاحواز» → الأحواز", r.includes("الأحواز"), r.slice(0, 3).join(" | "));
r = await search("بخاري");
check("ى/ي-insensitive: «بخاري» → بخارى", r.includes("بخارى"), r.slice(0, 3).join(" | "));
r = await search("سفالة");
check("diacritic-insensitive: «سفالة» → سُفالة", r.includes("سُفالة"), r.slice(0, 3).join(" | "));
r = await search("640");
check("digit-insensitive: «640» → ٦٤٠", r.includes("٦٤٠"), `${r.filter((t) => t === "٦٤٠").length} hits`);
r = await search("الإمبراطورية");
check("prefix search finds polity names", r.length >= 8, `${r.length} results`);
r = await search("ص ٥");
check("page search «ص ٥»", r[0] && r[0].includes("الصفحة"), r[0]);
r = await search("zzzz");
const empty = await page.evaluate(() => document.querySelector("#search-results .empty") && document.querySelector("#search-results .empty").textContent);
check("empty state for no results", !!empty, empty);
r = await search("تيمبوكتو");
await page.screenshot({ path: path.join(SHOTS, "04-search.png") });
await page.keyboard.press("ArrowDown"); await page.keyboard.press("Enter"); await sleep(2500);
await mapReady(page);
const sel = await page.evaluate(() => ({ hash: location.hash, card: document.querySelector("#feature-card h3") && document.querySelector("#feature-card h3").textContent }));
check("keyboard: Enter opens result on its map", sel.card === "تيمبوكتو", JSON.stringify(sel));

// ---------------- page viewer ----------------
await page.goto(FILE + "#/page/2", { waitUntil: "load" });
await page.waitForSelector("#page-panes svg image", { timeout: 20000 }); await sleep(800);
check("original page view shows raster render", await page.evaluate(() => !!document.querySelector("#page-panes svg image").getAttribute("href").startsWith("data:image/webp")));
await page.screenshot({ path: path.join(SHOTS, "05-page-raster.png") });
await page.click('[data-pagemode="side"]'); await sleep(2500);
check("side-by-side page comparison builds two panes", await page.evaluate(() => document.querySelectorAll("#page-panes .pane").length === 2));
await page.screenshot({ path: path.join(SHOTS, "06-page-side.png") });
await page.click('[data-pact="next"]'); await sleep(2500);
check("page navigation next", await page.evaluate(() => location.hash === "#/page/3"));

// ---------------- compare ----------------
await page.goto(FILE + "#/compare?a=fig-1-1&b=fig-1-4&mode=swipe", { waitUntil: "load" });
await page.waitForSelector("#compare-panes .swipe-handle", { timeout: 30000 }); await sleep(1500);
check("swipe comparison for registered pair", true);
await page.screenshot({ path: path.join(SHOTS, "07-compare-swipe.png") });
await page.goto(FILE + "#/compare?a=fig-1-3&b=fig-2&mode=side", { waitUntil: "load" });
await page.waitForFunction(() => document.querySelectorAll("#compare-panes .pane svg.map-svg").length === 2, { timeout: 30000 }); await sleep(1000);
check("unrelated maps: sync disabled", await page.evaluate(() => document.querySelector("#cmp-sync").disabled));
await page.screenshot({ path: path.join(SHOTS, "08-compare-side.png") });

// ---------------- index / learn / about ----------------
await page.goto(FILE + "#/index", { waitUntil: "load" }); await sleep(800);
const idx = await page.evaluate(() => document.querySelectorAll(".idx-item").length);
check("gazetteer lists names", idx > 250, `${idx} entries`);
await page.screenshot({ path: path.join(SHOTS, "09-index.png") });
await page.goto(FILE + "#/learn/name", { waitUntil: "load" });
await page.waitForSelector(".choices button", { timeout: 30000 }); await sleep(800);
check("quiz «name» shows 4 choices", await page.evaluate(() => document.querySelectorAll(".choices button").length === 4));
check("quiz map hides labels", await page.evaluate(() => document.querySelector("#learn-map svg").classList.contains("hide-label")));
await page.screenshot({ path: path.join(SHOTS, "10-learn.png") });
await page.goto(FILE + "#/about", { waitUntil: "load" }); await sleep(600);
await page.screenshot({ path: path.join(SHOTS, "11-about.png"), fullPage: false });

// dark theme
await page.goto(FILE + "#/fig/fig-1-3", { waitUntil: "load" }); await mapReady(page);
await page.click("#btn-theme"); await sleep(500);
check("dark theme toggles", await page.evaluate(() => document.documentElement.dataset.theme === "dark"));
await page.screenshot({ path: path.join(SHOTS, "12-dark.png") });
await page.click("#btn-theme");

// performance: page-2 heavy figure re-render time after zoom commit
await page.goto(FILE + "#/fig/fig-2", { waitUntil: "load" }); await mapReady(page);
const perf = await page.evaluate(async () => {
  const svg = document.querySelector("#viewer-host svg");
  const t = performance.now(); svg.setAttribute("viewBox", "200 200 200 150");
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))); return performance.now() - t;
});
check("vector re-render after zoom (heaviest figure)", perf < 1500, `${perf.toFixed(0)} ms`);
await page.close();

// ---------------- tablet & mobile ----------------
const tab = await newPage(900, 1180);
await tab.goto(FILE + "#/fig/fig-1-3", { waitUntil: "load" }); await mapReady(tab); await sleep(500);
await tab.screenshot({ path: path.join(SHOTS, "13-tablet.png") });
await tab.close();
const mob = await newPage(390, 844, 2);
await mob.goto(FILE + "#/fig/fig-1-4", { waitUntil: "load" }); await mapReady(mob); await sleep(500);
const overflow = await mob.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
check("mobile: no horizontal overflow", !overflow);
await mob.screenshot({ path: path.join(SHOTS, "14-mobile-explore.png") });
await mob.click("#btn-toc"); await sleep(400);
await mob.screenshot({ path: path.join(SHOTS, "15-mobile-toc.png") });
await mob.keyboard.press("Escape"); await sleep(300);
// touch tap a hotspot
const mh = await mob.evaluate(() => { const g = [...document.querySelectorAll("#viewer-host .hs")].find((x) => x.querySelector("title").textContent === "فزان"); const r = g.querySelector(".hs-shape").getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; });
await mob.mouse.click(mh.x, mh.y); await sleep(800);
check("mobile: tapping label opens info sheet", await mob.evaluate(() => document.querySelector("#panel-info").classList.contains("open") && document.querySelector("#feature-card h3").textContent === "فزان"));
await mob.screenshot({ path: path.join(SHOTS, "16-mobile-card.png") });
await mob.close();

await browser.close();
check("no network requests attempted (fully offline)", blocked.length === 0, blocked.slice(0, 3).join(", "));
check("no JavaScript errors", errors.length === 0, errors.slice(0, 5).join(" || "));
const failed = results.filter((x) => !x.ok);
fs.writeFileSync(path.join(SHOTS, "qa-results.json"), JSON.stringify({ when: new Date().toISOString(), results, errors, blocked }, null, 1));
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
process.exit(failed.length ? 1 : 0);
