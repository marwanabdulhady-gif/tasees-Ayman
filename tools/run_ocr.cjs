#!/usr/bin/env node
/**
 * Parallel Arabic OCR pipeline for scanned atlas volumes (seerah & abubakr).
 * Uses local Tesseract WASM + ara.traineddata.gz (zero network requests).
 * Outputs per-volume JSON with page text, mean confidence, and filtered word boxes
 * in native page-image pixel coordinates.
 */
const fs = require("fs");
const path = require("path");
const os = require("os");

const ROOT = path.resolve(__dirname, "..");
const TESS_PATH = fs.existsSync(path.join(ROOT, ".cache/ocr/node_modules/tesseract.js"))
  ? path.join(ROOT, ".cache/ocr/node_modules/tesseract.js")
  : "tesseract.js";
const { createWorker } = require(TESS_PATH);

const LANG_PATH = fs.existsSync(path.join(ROOT, ".cache/ocr/lang-data"))
  ? path.join(ROOT, ".cache/ocr/lang-data")
  : path.join(ROOT, "tools/ocr/lang-data");
const CACHE_PATH = path.join(ROOT, ".cache/ocr");

const metrics = JSON.parse(fs.readFileSync(path.join(ROOT, "data/raw_page_metrics.json"), "utf8"));

// Known full-bleed / divider / cover pages in seerah where outer strip should NOT be cropped
const SEERAH_FULL_PAGES = new Set([1, 2, 3, 15, 31, 51, 71, 83, 121, 211, 223, 255, 264]);

function cleanArabicLine(line) {
  return line
    .replace(/[\u200e\u200f\u202a-\u202e]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function isUsefulWord(text, conf) {
  if (!text || conf < 42) return false;
  const cleaned = text.replace(/[\u200e\u200f\s.,:;!؟،ـ\-_|/\\()[\]{}"'«»<>~`@#$%^&*+=]+/g, "");
  if (cleaned.length < 2) return false;
  // Require at least one Arabic letter or Arabic-Indic/Western digit sequence
  return /[\u0621-\u064A\u0660-\u06690-9]/.test(cleaned);
}

async function processVolume(slug, concurrency) {
  const pagesMeta = metrics[slug];
  const outDir = path.join(ROOT, "data/ocr");
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, `${slug}.json`);

  const results = new Array(pagesMeta.length);
  let cursor = 0;
  let done = 0;
  const t0 = Date.now();

  async function workerLoop(workerId) {
    const worker = await createWorker("ara", 1, {
      langPath: LANG_PATH,
      cachePath: CACHE_PATH,
      gzip: true,
      logger: () => {},
      errorHandler: () => {},
    });

    while (true) {
      const idx = cursor++;
      if (idx >= pagesMeta.length) break;
      const pm = pagesMeta[idx];
      const pnum = pm.page;
      const imgPath = path.join(ROOT, `assets/pages/${slug}/page-${String(pnum).padStart(3, "0")}.webp`);

      let recOpts = {};
      if (slug === "seerah" && !SEERAH_FULL_PAGES.has(pnum)) {
        // Odd pages have vertical title strip on left ~8.2%, even pages on right ~8.2%
        const stripW = Math.round(pm.width * 0.085);
        if (pnum % 2 === 1) {
          recOpts = { rectangle: { left: stripW, top: 0, width: pm.width - stripW, height: pm.height } };
        } else {
          recOpts = { rectangle: { left: 0, top: 0, width: pm.width - stripW, height: pm.height } };
        }
      } else if (slug === "abubakr" && pnum >= 4 && pnum <= 120) {
        // Skip top decorative running header bar (~5.5% height)
        const topH = Math.round(pm.height * 0.055);
        recOpts = { rectangle: { left: 0, top: topH, width: pm.width, height: pm.height - topH } };
      }

      try {
        const { data } = await worker.recognize(imgPath, recOpts);
        const lines = (data.text || "")
          .split(/\r?\n/)
          .map(cleanArabicLine)
          .filter((l) => l.length > 1 && /[\u0621-\u064A]/.test(l));

        const words = [];
        for (const w of data.words || []) {
          const wt = cleanArabicLine(w.text || "");
          const wc = Math.round(w.confidence || 0);
          if (isUsefulWord(wt, wc) && w.bbox) {
            words.push([
              wt,
              w.bbox.x0,
              w.bbox.y0,
              w.bbox.x1,
              w.bbox.y1,
              wc,
            ]);
          }
        }

        results[idx] = {
          page: pnum,
          confidence: Math.round(data.confidence || 0),
          wordCount: words.length,
          text: lines.join("\n"),
          words,
        };
      } catch (err) {
        results[idx] = {
          page: pnum,
          confidence: 0,
          wordCount: 0,
          text: "",
          words: [],
          error: String(err.message || err),
        };
      }

      done++;
      if (done % 25 === 0 || done === pagesMeta.length) {
        const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
        console.log(`[${slug}] ${done}/${pagesMeta.length} pages (${elapsed}s)`);
      }
    }

    await worker.terminate();
  }

  const workers = [];
  for (let i = 0; i < concurrency; i++) {
    workers.push(workerLoop(i));
  }
  await Promise.all(workers);

  fs.writeFileSync(outFile, JSON.stringify({
    volume: slug,
    engine: "tesseract.js-5.1.1 (ara tessdata_fast)",
    generatedAt: new Date().toISOString(),
    totalPages: results.length,
    pages: results,
  }));
  const sz = (fs.statSync(outFile).size / 1024 / 1024).toFixed(2);
  console.log(`[${slug}] Saved ${outFile} (${sz} MB) in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
}

(async () => {
  const nWorkers = Math.max(2, Math.min(4, os.cpus().length));
  console.log(`Starting OCR with ${nWorkers} parallel workers...`);
  await processVolume("abubakr", nWorkers);
  await processVolume("seerah", nWorkers);
})();
