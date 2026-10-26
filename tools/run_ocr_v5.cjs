#!/usr/bin/env node
/**
 * Parallel Arabic OCR pipeline (tesseract.js v5 API) — Node 22 compatible.
 * Output format is identical to tools/run_ocr.cjs: .cache/ocr_out/<slug>.json with
 * {volume, engine, generatedAt, totalPages, pages: [{page, confidence, wordCount, text, words:[[w,x0,y0,x1,y1,conf]]}]}
 * Uses local Tesseract WASM core (tesseract.js-core from node_modules) + ara.traineddata.gz — zero network.
 */
const fs = require("fs");
const path = require("path");
const os = require("os");

const ROOT = path.resolve(__dirname, "..");
const { createWorker } = require(path.join(ROOT, ".cache/ocr/node_modules/tesseract.js"));
const LANG_PATH = path.join(ROOT, ".cache/ocr/lang-data");
const CACHE_PATH = path.join(ROOT, ".cache/ocr");
const OEM = 1; // LSTM_ONLY

const metrics = JSON.parse(fs.readFileSync(path.join(ROOT, "data/raw_page_metrics.json"), "utf8"));

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
  return /[\u0621-\u064A\u0660-\u06690-9]/.test(cleaned);
}

async function processVolume(slug, concurrency) {
  const pagesMeta = metrics[slug];
  const outDir = path.join(ROOT, ".cache/ocr_out");
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, `${slug}.json`);

  const results = new Array(pagesMeta.length);
  let cursor = 0;
  let done = 0;
  const t0 = Date.now();

  async function workerLoop(workerId) {
    const worker = await createWorker("ara", OEM, {
      langPath: LANG_PATH,
      cachePath: CACHE_PATH,
      gzip: true,
      logger: () => {},
    });

    while (true) {
      const idx = cursor++;
      if (idx >= pagesMeta.length) break;
      const pm = pagesMeta[idx];
      const pnum = pm.page;
      const imgPath = path.join(ROOT, `assets/pages/${slug}/page-${String(pnum).padStart(3, "0")}.webp`);

      try {
        const { data } = await worker.recognize(imgPath);
        const lines = (data.text || "")
          .split(/\r?\n/)
          .map(cleanArabicLine)
          .filter((l) => l.length > 1 && /[\u0621-\u064A]/.test(l));

        const words = [];
        for (const w of data.words || []) {
          const wt = cleanArabicLine(w.text || "");
          const wc = Math.round(w.confidence || 0);
          if (isUsefulWord(wt, wc) && w.bbox) {
            words.push([wt, w.bbox.x0, w.bbox.y0, w.bbox.x1, w.bbox.y1, wc]);
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
  const cliTargets = process.argv.slice(2);
  const targets = cliTargets.length ? cliTargets : ["dawal"];
  console.log(`Starting OCR (tesseract.js v5, ${nWorkers} workers) for: ${targets.join(", ")}...`);
  for (const slug of targets) {
    if (metrics[slug]) {
      await processVolume(slug, nWorkers);
    } else {
      console.log(`Skipping unknown slug: ${slug}`);
    }
  }
})().catch((e) => { console.error(e); process.exit(1); });
