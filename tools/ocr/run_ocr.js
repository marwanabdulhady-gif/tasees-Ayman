#!/usr/bin/env node
/**
 * Offline Arabic OCR for all atlas pages (Tesseract.js LSTM, local WASM core).
 *
 * Input : data/ocr_jobs.json        (from tools/prepare_ocr_images.py)
 * Output: assets/ocr/<doc>/pNNN.json
 *
 * Each output keeps the ORIGINAL OCR string untouched, plus per-word bounding
 * boxes and confidence. Words below CONF_FLOOR are flagged `uncertain` and are
 * never promoted to verified geographic facts. Coordinates are stored in
 * OCR-image pixels together with the image width/height so the viewer can map
 * them back onto the displayed page at any zoom level.
 *
 * Usage: node tools/ocr/run_ocr.js [numberOfWorkers]
 */
const fs = require('fs');
const path = require('path');
const { createWorker, createScheduler, OEM } = require('tesseract.js');

const ROOT = path.resolve(__dirname, '../..');
const JOBS = path.join(ROOT, 'data/ocr_jobs.json');
const OUT = path.join(ROOT, 'assets/ocr');
const LANG_PATH = path.join(__dirname, 'lang-data');
const CACHE_PATH = path.join(__dirname, '.cache');
const CONF_FLOOR = 60;
const WORKERS = Math.max(1, Math.min(8, Number(process.argv[2] || 4)));

function wordsFromBlocks(blocks) {
  const words = [];
  for (const block of blocks || []) {
    for (const para of block.paragraphs || []) {
      for (const line of para.lines || []) {
        for (const w of line.words || []) {
          if (!w.text || !w.text.trim()) continue;
          words.push({
            t: w.text,
            bbox: w.bbox,               // {x0,y0,x1,y1} in OCR-image pixels
            conf: Math.round(w.confidence),
            uncertain: w.confidence < CONF_FLOOR,
          });
        }
      }
    }
  }
  return words;
}

(async () => {
  const jobs = JSON.parse(fs.readFileSync(JOBS, 'utf8'));
  const pending = jobs.filter((j) => {
    const out = path.join(OUT, j.documentId, `${String(j.sourcePage).padStart(3, '0')}.json`);
    return !fs.existsSync(out);
  });
  console.log(`OCR jobs: ${jobs.length}, pending: ${pending.length}, workers: ${WORKERS}`);
  if (!pending.length) return;

  const scheduler = createScheduler();
  for (let i = 0; i < WORKERS; i++) {
    const worker = await createWorker('ara', OEM.LSTM_ONLY, {
      langPath: LANG_PATH,
      cachePath: CACHE_PATH,
      gzip: true,
      // Tesseract parameters: keep inter-word spaces; Arabic page segmentation.
      logger: () => {},
    });
    await worker.setParameters({ preserve_interword_spaces: '1' });
    scheduler.addWorker(worker);
  }

  let done = 0;
  let confSum = 0;
  const t0 = Date.now();
  await Promise.all(
    pending.map(async (job) => {
      const imagePath = path.join(ROOT, job.image);
      const { data } = await scheduler.addJob('recognize', imagePath, {}, {
        text: true, blocks: true,
      });
      const words = wordsFromBlocks(data.blocks);
      const mean = words.length
        ? Math.round(words.reduce((a, w) => a + w.conf, 0) / words.length)
        : 0;
      const record = {
        id: job.id,
        documentId: job.documentId,
        sourcePage: job.sourcePage,
        engine: 'tesseract.js/5 LSTM ara (tessdata_fast)',
        language: 'ara',
        imageWidth: job.width,
        imageHeight: job.height,
        meanConfidence: mean,
        uncertainWordCount: words.filter((w) => w.uncertain).length,
        wordCount: words.length,
        verificationStatus: 'ocr-unverified',
        extractedText: data.text || '',
        words,
      };
      const dir = path.join(OUT, job.documentId);
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(
        path.join(dir, `${String(job.sourcePage).padStart(3, '0')}.json`),
        JSON.stringify(record),
      );
      done += 1;
      confSum += mean;
      if (done % 10 === 0 || done === pending.length) {
        const secs = ((Date.now() - t0) / 1000).toFixed(0);
        console.log(`  ${done}/${pending.length} pages, avg conf ${Math.round(confSum / done)}, ${secs}s`);
      }
    }),
  );
  await scheduler.terminate();
  console.log(`OCR complete in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
})().catch((err) => { console.error(err); process.exit(1); });
