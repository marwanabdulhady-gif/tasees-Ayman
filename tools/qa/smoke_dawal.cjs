#!/usr/bin/env node
/**
 * smoke_dawal.cjs — integration smoke test for the new «دول العالم الإسلامي» volume.
 * Verifies: manifest 7 volumes / 1597 pages, volume pills, dawal filter,
 * Arabic search hits in dawal, page-jump query «دول 22», and the rendered page asset.
 */
const fs = require("fs");
const path = require("path");
const zlib = require("zlib");
const { execSync } = require("child_process");

const ROOT = path.resolve(__dirname, "../..");
const QA_MODS = fs.existsSync(path.join(ROOT, ".cache/qa/node_modules"))
  ? path.join(ROOT, ".cache/qa/node_modules")
  : path.join(__dirname, "node_modules");

const puppeteer = require(path.join(QA_MODS, "puppeteer-core"));
const chromiumPkg = require(path.join(QA_MODS, "@sparticuz/chromium"));

const libsDir = path.join(ROOT, ".cache/qa/libs");
if (!fs.existsSync(path.join(libsDir, "lib/libnss3.so"))) {
  fs.mkdirSync(libsDir, { recursive: true });
  const brPath = path.join(QA_MODS, "@sparticuz/chromium/bin/al2023.tar.br");
  if (fs.existsSync(brPath)) {
    const tarPath = path.join(libsDir, "al2023.tar");
    fs.writeFileSync(tarPath, zlib.brotliDecompressSync(fs.readFileSync(brPath)));
    execSync(`tar -xf "${tarPath}" -C "${libsDir}"`);
  }
}
process.env.LD_LIBRARY_PATH = `${path.join(libsDir, "lib")}:${process.env.LD_LIBRARY_PATH || ""}`;

let pass = 0, fail = 0;
function check(name, ok, detail = "") {
  console.log(`${ok ? "PASS" : "FAIL"} ${name}${detail ? " — " + detail : ""}`);
  ok ? pass++ : fail++;
}

(async () => {
  const browser = await puppeteer.launch({
    executablePath: await chromiumPkg.executablePath(),
    args: chromiumPkg.args.filter((a) => !String(a).startsWith("--enable-automation")),
  });
  const page = await browser.newPage();
  const jsErrors = [];
  page.on("pageerror", (e) => jsErrors.push(String(e)));
  await page.setViewport({ width: 1440, height: 900 });

  await page.goto("file://" + path.join(ROOT, "index.html"), { waitUntil: "networkidle0", timeout: 60000 });
  await page.waitForSelector(".vol-pill", { timeout: 30000 });

  const manifestInfo = await page.evaluate(() => {
    const m = window.__ATLAS_MANIFEST__;
    return {
      volumes: m.volumes.length,
      pages: m.pages.length,
      dawalVol: m.volumes.find((v) => v.id === "dawal"),
      dawalPages: m.pages.filter((p) => p.volumeId === "dawal").length,
    };
  });
  check("manifest: 7 volumes", manifestInfo.volumes === 7, `${manifestInfo.volumes}`);
  check("manifest: 1597 pages", manifestInfo.pages === 1597, `${manifestInfo.pages}`);
  check("manifest: dawal volume registered (256 pages)", manifestInfo.dawalVol && manifestInfo.dawalVol.pageCount === 256,
    manifestInfo.dawalVol ? `sections=${manifestInfo.dawalVol.sections.length}` : "missing");

  const pills = await page.$$eval(".vol-pill", (els) => els.map((e) => e.dataset.vol));
  check("volume pills: 7 rendered incl. dawal", pills.length === 7 && pills.includes("dawal"), pills.join(","));

  // set the SEARCH volume filter to dawal (the pill controls the explorer, not search)
  await page.evaluate(() => {
    const sel = document.getElementById("search-vol-filter");
    sel.value = "dawal";
    sel.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await new Promise((r) => setTimeout(r, 400));

  // search «أفغانستان» inside the dawal volume
  await page.evaluate(() => {
    const inp = document.getElementById("global-search-input");
    inp.value = "أفغانستان";
    inp.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await new Promise((r) => setTimeout(r, 900));
  const hits = await page.evaluate(() =>
    [...document.querySelectorAll("#search-results-list .search-result-item")].map((e) => {
      const strong = e.querySelector("strong");
      const spans = e.querySelectorAll(".sr-meta span");
      return { vol: spans[0] ? spans[0].textContent : "", page: strong ? strong.textContent : "" };
    })
  );
  const hitPages = hits.filter((h) => h.vol.includes("دول العالم الإسلامي")).map((h) => h.page);
  check("search «أفغانستان» (dawal filter): hits on ص ١٢ (map) + ص ١٣ (data)",
    hitPages.includes("ص ١٢") && hitPages.includes("ص ١٣"),
    JSON.stringify(hits.slice(0, 8)));

  // page jump «دول 22» → dawal-022 (map of أوغندا)
  await page.evaluate(() => {
    const inp = document.getElementById("global-search-input");
    inp.value = "";
    inp.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await new Promise((r) => setTimeout(r, 400));
  await page.evaluate(() => {
    const inp = document.getElementById("global-search-input");
    inp.value = "دول 22";
    inp.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await new Promise((r) => setTimeout(r, 900));
  const jumped = await page.evaluate(() => {
    const items = [...document.querySelectorAll("#search-results-list .search-result-item")];
    const target = items.find((e) => {
      const strong = e.querySelector("strong");
      return strong && strong.textContent.trim() === "ص ٢٢";
    }) || items[0];
    if (target) target.click();
    return items.slice(0, 5).map((e) => (e.querySelector("strong") || {}).textContent);
  });
  await new Promise((r) => setTimeout(r, 1200));
  const openState = await page.evaluate(() => {
    const img = document.querySelector("#explorer-viewport img[src*='assets/pages/dawal/']") ||
                document.querySelector("img[src*='assets/pages/dawal/']");
    return { img: img ? img.getAttribute("src") : null };
  });
  check("page-jump «دول 22» opens dawal-022 (map page)", openState.img && openState.img.includes("page-022.webp"),
    JSON.stringify({ jumped, openState }));

  check("no page JS errors", jsErrors.length === 0, jsErrors.slice(0, 3).join(" | "));

  await browser.close();
  console.log(`\nsmoke result: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error("smoke crashed:", e); process.exit(2); });
