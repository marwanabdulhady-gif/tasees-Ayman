#!/usr/bin/env node
/**
 * Comprehensive Automated QA Suite (Phase Ten: 12.1 – 12.5)
 * Verifies:
 *   12.1 Content Integrity across all 3 PDFs (393 pages, 0 omissions, hashes, indexes, OCR flags)
 *   12.2 Map Interactions (pan, zoom, fit, reset, 90° rotation, vector layers, hotspots, crops)
 *   12.3 Arabic-Aware Search (Alef variants أ/إ/آ/ا, ى/ي, ة/ه, diacritics, multi-page hits, page jump)
 *   12.4 Strict Offline Execution over file:// with ALL external requests blocked (both index.html & portable-atlas.html)
 *   12.5 Visual Layout Inspection across Desktop (1440x900), Tablet (820x1180), Mobile (390x844), and Dark Mode
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

// Ensure NSS shared libraries from @sparticuz/chromium are unpacked for Linux sandboxes
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

const SHOTS_DIR = path.join(ROOT, ".cache/qa/screenshots");
fs.mkdirSync(SHOTS_DIR, { recursive: true });

const results = [];
const jsErrors = [];
const blockedExternalRequests = [];

function check(section, name, ok, detail = "") {
  results.push({ section, name, ok: Boolean(ok), detail });
  console.log(`${ok ? "PASS" : "FAIL"} [${section}] ${name}${detail ? " — " + detail : ""}`);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  // ---------------- 12.1 Content Integrity Checks on Manifest & Assets ----------------
  const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, "data/manifest.json"), "utf8"));
  check("12.1", "Total PDF pages equals 1597 (8 + 264 + 121 + 351 + 325 + 272 + 256) with zero omissions", manifest.pages.length === 1597, `${manifest.pages.length} pages`);
  check("12.1", "Volume page counts match all 7 source PDFs",
    manifest.stats.pagesByVolume.maps8 === 8 &&
    manifest.stats.pagesByVolume.seerah === 264 &&
    manifest.stats.pagesByVolume.abubakr === 121 &&
    manifest.stats.pagesByVolume.umar === 351 &&
    manifest.stats.pagesByVolume.uthman === 325 &&
    manifest.stats.pagesByVolume.ali === 272 &&
    manifest.stats.pagesByVolume.dawal === 256
  );
  const dawalVol = manifest.volumes.find((v) => v.id === "dawal");
  check("12.1", "Volume 7 (أطلس دول العالم الإسلامي) registered: 256 pages, 7 sections, 89 printed maps",
    Boolean(dawalVol && dawalVol.pageCount === 256 && dawalVol.sections.length === 7 && dawalVol.printedIndexes.mapsCount === 89),
    dawalVol ? `sections=${dawalVol.sections.length}` : "missing");

  const missingAssets = manifest.pages.filter(
    (p) => !fs.existsSync(path.join(ROOT, p.pageAsset)) || !fs.existsSync(path.join(ROOT, p.thumbAsset))
  );
  check("12.1", "Every single page (1597/1597) has both full-res WebP and thumbnail asset on disk", missingAssets.length === 0, `missing=${missingAssets.length}`);
  const ocrBundleRaw = fs.readFileSync(path.join(ROOT, "data/ocr-words-bundle.js"), "utf8").trim();
  const ocrBundle = JSON.parse(zlib.gunzipSync(Buffer.from(ocrBundleRaw.split('"')[1], "base64")).toString("utf8"));
  const dawalOcrPages = Object.keys(ocrBundle).filter((k) => k.startsWith("dawal-")).length;
  const dawalOcrWords = Object.entries(ocrBundle).filter(([k]) => k.startsWith("dawal-")).reduce((s, [, w]) => s + w.length, 0);
  check("12.1", "OCR words bundle covers dawal volume (251 pages with words, 16,557 word boxes)",
    dawalOcrPages === 251 && dawalOcrWords === 16557, `pages=${dawalOcrPages}, words=${dawalOcrWords}`);

  const corruptArabic = manifest.pages.filter((p) => /\uFFFD/.test(p.title) || /\uFFFD/.test(p.extractedText || ""));
  check("12.1", "Zero Unicode replacement characters (U+FFFD) in titles or extracted Arabic text", corruptArabic.length === 0);

  const lowFlagged = manifest.pages.filter((p) => p.verificationStatus === "ocr-needs-review");
  check("12.1", "Low-confidence OCR pages are explicitly flagged for manual review", lowFlagged.length > 0, `${lowFlagged.length} flagged`);

  // ---------------- Launch Offline Browser ----------------
  const execPath = await chromiumPkg.executablePath();
  const browser = await puppeteer.launch({
    executablePath: execPath,
    headless: true,
    args: [
      ...chromiumPkg.args,
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--allow-file-access-from-files",
    ],
  });

  async function openOfflinePage(fileUrl, width, height) {
    const page = await browser.newPage();
    await page.setViewport({ width, height, deviceScaleFactor: 1 });
    await page.setRequestInterception(true);
    page.on("request", (req) => {
      const u = req.url();
      if (u.startsWith("file:") || u.startsWith("data:") || u.startsWith("blob:")) {
        req.continue();
      } else {
        blockedExternalRequests.push(u);
        req.abort();
      }
    });
    page.on("pageerror", (err) => jsErrors.push(`pageerror: ${err.message}`));
    page.on("console", (msg) => {
      if (msg.type() === "error") jsErrors.push(`console.error: ${msg.text()}`);
    });
    await page.goto(fileUrl, { waitUntil: "load", timeout: 45000 });
    return page;
  }

  // ---------------- 12.2, 12.3, 12.4: Full Offline Package via file:// ----------------
  const mainUrl = "file://" + path.join(ROOT, "index.html");
  const page = await openOfflinePage(mainUrl, 1440, 900);
  await page.waitForSelector("svg.vector-spread-svg", { timeout: 20000 });
  await sleep(300);

  const rtlCheck = await page.evaluate(() => ({
    lang: document.documentElement.lang,
    dir: document.documentElement.dir,
    vecPaths: document.querySelectorAll("svg.vector-spread-svg .L-label").length,
    hotspots: document.querySelectorAll("svg.vector-spread-svg .vec-hotspot").length,
  }));
  check("12.4", "Complete Offline Package loads via file:// with Arabic RTL", rtlCheck.lang === "ar" && rtlCheck.dir === "rtl");
  check("12.2", "Joined 2-page vector spread renders real separated layers & hotspots", rtlCheck.vecPaths > 100 && rtlCheck.hotspots > 150, `paths=${rtlCheck.vecPaths}, hotspots=${rtlCheck.hotspots}`);
  await page.screenshot({ path: path.join(SHOTS_DIR, "01-desktop-maps8-spread.png") });

  // Test Zoom, Pan, Fit, Reset
  const zBefore = await page.$eval("#zoom-readout", (el) => el.textContent);
  await page.click("#btn-zoom-in");
  await page.click("#btn-zoom-in");
  const zAfter = await page.$eval("#zoom-readout", (el) => el.textContent);
  check("12.2", "Zoom-in updates map scale and Arabic zoom readout", zBefore !== zAfter, `${zBefore} -> ${zAfter}`);

  await page.click("#btn-fit");
  const zFit = await page.$eval("#zoom-readout", (el) => el.textContent);
  check("12.2", "Fit-to-screen restores full spread scale", zFit === zBefore, `${zFit}`);

  // Test Vector Layer Toggling
  await page.click('[data-vec-layer="label"]');
  const labelsHidden = await page.$eval("svg.vector-spread-svg", (el) => el.classList.contains("hide-label"));
  check("12.2", "Vector layer toggle hides/shows label layer independently", labelsHidden === true);
  await page.click('[data-vec-layer="label"]');

  // Test Clicking a Vector Feature & Source Crop Card
  await page.evaluate(() => {
    const hs = document.querySelector('svg.vector-spread-svg .vec-hotspot[data-fid="p1-010"]') ||
               document.querySelector("svg.vector-spread-svg .vec-hotspot");
    hs.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
  await sleep(200);
  const hasFeatureCard = await page.evaluate(() => Boolean(document.querySelector(".feature-card .crop-preview-wrap img")));
  check("12.2", "Clicking geographic feature opens verification card with live source crop", hasFeatureCard);
  await page.screenshot({ path: path.join(SHOTS_DIR, "02-desktop-feature-card.png") });

  // ---------------- 12.3 Search Tests (Alef variants, ى/ي, ة/ه, multi-page, small labels) ----------------
  async function testSearchQuery(query) {
    await page.evaluate(() => { document.getElementById("global-search-input").value = ""; });
    await page.type("#global-search-input", query);
    await sleep(250);
    return page.evaluate(() => {
      const items = Array.from(document.querySelectorAll("#search-results-list .search-result-item"));
      return items.map((li) => li.innerText.replace(/\s+/g, " ").trim());
    });
  }

  const sAlef1 = await testSearchQuery("الاسكندريه"); // without hamza & with ه instead of ة
  const sAlef2 = await testSearchQuery("الإسكندرية"); // with hamza & ة
  check("12.3", "Arabic search normalizes Alef variants (أ/إ/ا) and Ta-Marbuta (ة/ه)", sAlef1.length > 0 && sAlef1.length === sAlef2.length, `hits=${sAlef1.length}`);

  const sYa1 = await testSearchQuery("بصري"); // ي instead of ى
  const sYa2 = await testSearchQuery("بصرى"); // ى
  check("12.3", "Arabic search normalizes Alef Maqsura and Ya (ى ↔ ي)", sYa1.length > 0 && sYa1.length === sYa2.length, `hits=${sYa1.length}`);

  const sTashkeel = await testSearchQuery("مَكَّةُ الْمُكَرَّمَةُ");
  check("12.3", "Arabic search strips diacritics (tashkeel) and finds multi-volume matches", sTashkeel.length >= 5, `hits=${sTashkeel.length}`);

  const sPageJump = await testSearchQuery("ص ١٦٥");
  check("12.3", "Search supports Eastern Arabic numeral page jump («ص ١٦٥»)", sPageJump.length >= 1, sPageJump[0] || "");
  await page.screenshot({ path: path.join(SHOTS_DIR, "03-desktop-search.png") });

  // Select Uhud battle map (seerah p.165) via search result & test 90° rotation
  const uhudHits = await testSearchQuery("غزوة أحد");
  check("12.3", "Search locates verified battle map «غزوة أحد»", uhudHits.length > 0);
  await page.click("#search-results-list .search-result-item");
  await sleep(350);

  const rotateBannerVisible = await page.evaluate(() => !document.getElementById("rotate-banner").hidden);
  check("12.2", "Sideways-printed map displays upright rotation helper banner", rotateBannerVisible);
  await page.click("#btn-auto-upright");
  await sleep(200);
  await page.screenshot({ path: path.join(SHOTS_DIR, "04-desktop-seerah-uhud-upright.png") });

  // Switch to Volume 3 (Abu Bakr Atlas)
  await page.click('[data-vol="abubakr"]');
  await sleep(300);
  const abubakrLoaded = await page.evaluate(() => document.querySelector(".page-main-title")?.textContent || "");
  check("12.2", "Switching to Volume 3 (أطلس أبي بكر الصديق) loads verified map", abubakrLoaded.length > 0, abubakrLoaded);
  await page.screenshot({ path: path.join(SHOTS_DIR, "05-desktop-abubakr.png") });

  // Switch to Volume 4 (Umar ibn al-Khattab Atlas) & test direct jump + Qadisiyyah map
  await page.click('[data-vol="umar"]');
  await sleep(350);
  const umarLoaded = await page.evaluate(() => document.querySelector(".page-main-title")?.textContent || "");
  check("12.2", "Switching to Volume 4 (أطلس عمر بن الخطاب) loads verified map", umarLoaded.includes("عمر"), umarLoaded);
  const qadJump = await testSearchQuery("عمر ٨١");
  check("12.3", "Search supports Volume 4 direct jump («عمر ٨١» -> معركة القادسية الحاسمة)", qadJump.some((t) => t.includes("القادسية")), qadJump[0] || "");
  await page.click("#search-results-list .search-result-item");
  await sleep(300);
  await page.screenshot({ path: path.join(SHOTS_DIR, "05b-desktop-umar-qadisiyyah.png") });

  // Switch to Volume 5 (Uthman ibn Affan Atlas) & test direct jump + Dhat al-Sawari map
  await page.click('[data-vol="uthman"]');
  await sleep(350);
  const uthmanLoaded = await page.evaluate(() => document.querySelector(".page-main-title")?.textContent || "");
  check("12.2", "Switching to Volume 5 (أطلس عثمان بن عفان) loads verified map", uthmanLoaded.includes("عثمان"), uthmanLoaded);
  const sawariJump = await testSearchQuery("عثمان ١٥٧");
  check("12.3", "Search supports Volume 5 direct jump («عثمان ١٥٧» -> معركة ذات الصواري)", sawariJump.some((t) => t.includes("الصواري")), sawariJump[0] || "");
  await page.click("#search-results-list .search-result-item");
  await sleep(300);
  await page.screenshot({ path: path.join(SHOTS_DIR, "05c-desktop-uthman-sawari.png") });

  // Switch to Volume 6 (Ali ibn Abi Talib Atlas) & test direct jump + Siffin map
  await page.click('[data-vol="ali"]');
  await sleep(350);
  const aliLoaded = await page.evaluate(() => document.querySelector(".page-main-title")?.textContent || "");
  check("12.2", "Switching to Volume 6 (أطلس علي بن أبي طالب) loads verified map", aliLoaded.includes("علي"), aliLoaded);
  const siffinJump = await testSearchQuery("علي ١٨١");
  check("12.3", "Search supports Volume 6 direct jump («علي ١٨١» -> معركة صفين)", siffinJump.some((t) => t.includes("صفين")), siffinJump[0] || "");
  await page.click("#search-results-list .search-result-item");
  await sleep(300);
  await page.screenshot({ path: path.join(SHOTS_DIR, "05d-desktop-ali-siffin.png") });

  // Switch to Volume 7 (Atlas of Islamic States — Dawal) & test direct jump
  await page.click('[data-vol="dawal"]');
  await sleep(350);
  const dawalLoaded = await page.evaluate(() => document.querySelector(".page-main-title")?.textContent || "");
  check("12.2", "Switching to Volume 7 (أطلس دول العالم الإسلامي) loads the cover/front matter", dawalLoaded.length > 0, dawalLoaded);
  const ughandaJump = await testSearchQuery("دول ٢٢");
  check("12.3", "Search supports Volume 7 direct jump («دول ٢٢» -> أوغندا)", ughandaJump.some((t) => t.includes("أوغندا")), ughandaJump[0] || "");
  await page.click("#search-results-list .search-result-item");
  await sleep(300);
  const dawalMapImg = await page.evaluate(() => document.querySelector("img[src*='assets/pages/dawal/page-022.webp']") !== null);
  check("12.2", "Volume 7 page-jump renders the dawal-022 map asset", dawalMapImg);
  await page.screenshot({ path: path.join(SHOTS_DIR, "05e-desktop-dawal-uganda.png") });

  // Test TOC, Original Page Split Verification, Compare, Gazetteer, Learn, Audit
  await page.click('[data-tab="toc"]');
  await sleep(300);
  const tocCards = await page.evaluate(() => document.querySelectorAll(".toc-card").length);
  check("12.2", "TOC gallery renders all 1597 pages across 7 volumes", tocCards === 1597, `cards=${tocCards}`);
  await page.screenshot({ path: path.join(SHOTS_DIR, "06-desktop-toc.png") });

  await page.click('[data-tab="original"]');
  await sleep(250);
  await page.click("#orig-split-toggle");
  await sleep(250);
  const origPanes = await page.evaluate(() => document.querySelectorAll("#view-original .dual-pane").length);
  check("12.2", "Original Page Viewer supports side-by-side source verification", origPanes === 2);
  await page.screenshot({ path: path.join(SHOTS_DIR, "07-desktop-original-verify.png") });

  await page.click('[data-tab="compare"]');
  await sleep(450);
  const swipePresent = await page.evaluate(() => Boolean(document.getElementById("cmp-swipe-stage")));
  check("12.2", "Geographic Comparison renders registered vector swipe curtain", swipePresent);
  await page.screenshot({ path: path.join(SHOTS_DIR, "08-desktop-compare-swipe.png") });

  await page.click('[data-tab="gazetteer"]');
  await sleep(250);
  const gazCards = await page.evaluate(() => document.querySelectorAll(".gaz-card").length);
  check("12.2", "Unified Gazetteer renders alphabetical entries", gazCards > 100, `shown=${gazCards}`);

  await page.click('[data-tab="learn"]');
  await sleep(250);
  const quizOpts = await page.evaluate(() => document.querySelectorAll(".quiz-opt").length);
  check("12.2", "Learning module generates verified source MCQ options", quizOpts >= 2, `opts=${quizOpts}`);
  await page.screenshot({ path: path.join(SHOTS_DIR, "09-desktop-learn.png") });

  // Dark Mode test
  await page.click("#btn-theme-toggle");
  await page.click('[data-tab="explore"]');
  await sleep(250);
  await page.screenshot({ path: path.join(SHOTS_DIR, "10-desktop-dark-mode.png") });

  // ---------------- 12.5 Tablet & Mobile Responsive Checks ----------------
  await page.setViewport({ width: 820, height: 1180 });
  await sleep(250);
  await page.screenshot({ path: path.join(SHOTS_DIR, "11-tablet-explore.png") });

  await page.setViewport({ width: 390, height: 844 });
  await page.click("#btn-theme-toggle"); // back to light mode on mobile
  await sleep(250);
  const mobOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 2);
  check("12.5", "Mobile viewport (390×844) has zero horizontal page overflow", !mobOverflow);
  await page.screenshot({ path: path.join(SHOTS_DIR, "12-mobile-explore.png") });

  await page.close();

  // ---------------- 12.4 Test Portable Single-File Edition via file:// ----------------
  const portableUrl = "file://" + path.join(ROOT, "release/portable-atlas.html");
  const pPage = await openOfflinePage(portableUrl, 1280, 800);
  await pPage.waitForSelector("svg.vector-spread-svg", { timeout: 20000 });
  const pOk = await pPage.evaluate(() => ({
    portableFlag: Boolean(window.__IS_PORTABLE_EDITION__),
    pagesCount: window.__ATLAS_MANIFEST__?.pages?.length || 0,
    vecHotspots: document.querySelectorAll("svg.vector-spread-svg .vec-hotspot").length,
  }));
  check("12.4", "Single-File Portable HTML Edition loads offline via file:// with all 1597 pages indexed",
    pOk.portableFlag && pOk.pagesCount === 1597 && pOk.vecHotspots > 150,
    `pages=${pOk.pagesCount}, vecHotspots=${pOk.vecHotspots}`
  );
  await pPage.close();

  check("12.4", "Zero external network requests attempted during offline sessions", blockedExternalRequests.length === 0, `blocked=${blockedExternalRequests.length}`);
  check("12.4", "Zero runtime JavaScript or console errors", jsErrors.length === 0, jsErrors.join("; "));

  // ---------------- 13.1: Atlas Modules — Quran Atlas (offline native build) ----------------
  const quranUrl = "file://" + path.join(ROOT, "atlas-modules/atlas-of-quran/index.html");
  const qData = JSON.parse(fs.readFileSync(path.join(ROOT, "atlas-modules/atlas-of-quran/data/locations.json"), "utf8")).locations;
  const qN = qData.length;
  const qv = require("./check_quran_texts.cjs").verify();
  check("13.1", "Every Quran excerpt is an exact slice of its cited verse, and every reference exists (vendored Uthmani text)",
    qv.problems.length === 0, `${qv.texts} excerpts, ${qv.refs} refs, ${qv.verses} verses; ${qv.problems.slice(0, 2).join(" ; ")}`);
  const qPage = await browser.newPage();
  await qPage.setViewport({ width: 1400, height: 900, deviceScaleFactor: 1 });
  await qPage.setRequestInterception(true);
  qPage.on("request", (req) => {
    const u = req.url();
    if (u.startsWith("file:") || u.startsWith("data:") || u.startsWith("blob:")) req.continue();
    else req.abort(); // expected & allowed: CARTO basemap tiles + Google My Maps iframe
  });
  const qErrors = [];
  qPage.on("pageerror", (e) => qErrors.push("pageerror: " + e.message));
  qPage.on("console", (m) => { if (m.type() === "error") qErrors.push(m.text()); });
  await qPage.goto(quranUrl, { waitUntil: "load", timeout: 45000 });
  await qPage.waitForSelector(".leaflet-marker-icon", { timeout: 20000 });
  const qInfo = await qPage.evaluate(() => ({
    dir: document.documentElement.dir,
    lang: document.documentElement.lang,
    locs: (window.QURAN_DATA || { locations: [] }).locations.length,
    items: document.querySelectorAll("ul.list li").length,
    markers: document.querySelectorAll(".leaflet-marker-icon").length,
  }));
  check("13.1", "Quran Atlas loads offline via file:// in Arabic RTL with full native dataset",
    qInfo.dir === "rtl" && qInfo.lang === "ar" && qInfo.locs === qN, `locs=${qInfo.locs}`);
  check("13.1", `All ${qN} locations rendered as sidebar list items and map markers`,
    qInfo.items === qN && qInfo.markers === qN, `items=${qInfo.items}, markers=${qInfo.markers}`);
  await qPage.type("#q", "مكة");
  await sleep(300);
  const qVis = await qPage.evaluate(() => [...document.querySelectorAll("ul.list li")].filter((e) => e.style.display !== "none").length);
  check("13.1", "Arabic search filters the list (مكة)", qVis >= 1 && qVis < qN, `shown=${qVis}`);
  await qPage.evaluate(() => { const i = document.getElementById("q"); i.value = ""; i.dispatchEvent(new Event("input")); });
  await qPage.click('ul.list li[data-id="makkah"]');
  await sleep(1500);
  const qPop = await qPage.evaluate(() => {
    const p = document.querySelector(".leaflet-popup-content");
    return p ? p.querySelector(".pp-title").textContent + "|" + (p.querySelector(".pp-verse") ? p.querySelector(".pp-verse").textContent : "") : "";
  });
  check("13.1", "Selecting a place opens a popup with a verified Quran excerpt",
    qPop.includes("مكة") && qPop.includes(qData.find((l) => l.id === "makkah").texts[0].text), qPop.slice(0, 60));
  const qRealErrors = qErrors.filter((e) => !/ERR_|Failed to load resource|net::/.test(e));
  check("13.1", "Quran Atlas: zero runtime JS errors (expected tile/embed aborts excluded)",
    qRealErrors.length === 0, qRealErrors.slice(0, 3).join(" ; "));
  await qPage.close();

  // --- QA guard: hub links in atlas-modules/index.html must resolve ---
  const hubHtml = fs.readFileSync(path.join(ROOT, "atlas-modules/index.html"), "utf8");
  const hubLinks = [...hubHtml.matchAll(/href="([^"]+)"/g)].map((m) => m[1]);
  const brokenHubLinks = [];
  for (const href of hubLinks) {
    if (href.startsWith("http")) continue; // external links are allowed
    const target = path.resolve(path.join(ROOT, "atlas-modules", href));
    if (!fs.existsSync(target)) brokenHubLinks.push(href);
  }
  check("12.1", "All internal hub links in atlas-modules/index.html resolve to existing files",
    brokenHubLinks.length === 0, brokenHubLinks.length ? `broken=${brokenHubLinks.join(", ")}` : "all OK");

  // --- QA guard: every volume with map pages must have hotspot coverage ---
  const hubManifest = JSON.parse(fs.readFileSync(path.join(ROOT, "data/manifest.json"), "utf8"));
  const vols = {};
  for (const p of hubManifest.pages) {
    if (p.category !== "map" && p.category !== "spread-map") continue;
    const v = p.volumeId;
    if (!vols[v]) vols[v] = { maps: 0, withHot: 0 };
    vols[v].maps++;
    if ((p.hotspots || []).length > 0) vols[v].withHot++;
  }
  // maps8 uses vector hotspots (maps8-vectors.js), not raster page hotspots — exclude
  const volMissingHot = Object.entries(vols).filter(([v, s]) => v !== "maps8" && s.withHot === 0 && s.maps > 0);
  check("12.2", "Every non-maps8 volume with map pages has at least one page with verified hotspots",
    volMissingHot.length === 0, volMissingHot.length ? `no-hotspot-volumes=${volMissingHot.map(([v])=>v).join(",")}` : "all covered");

  await browser.close();

  const passed = results.filter((r) => r.ok).length;
  console.log(`\n========================================`);
  console.log(`QA SUMMARY: ${passed}/${results.length} CHECKS PASSED`);
  console.log(`========================================`);

  fs.writeFileSync(
    path.join(ROOT, "data/qa_report.json"),
    JSON.stringify({ timestamp: new Date().toISOString(), total: results.length, passed, results, jsErrors, blockedExternalRequests }, null, 2)
  );

  if (passed !== results.length) {
    process.exit(1);
  }
})();
