// quick screenshot helper: node shot.mjs <hash> <out.png> [w] [h]
import chromium from "@sparticuz/chromium";
import puppeteer from "puppeteer-core";
import path from "path"; import { fileURLToPath } from "url";
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const [hash, out, w = 1440, h = 900] = process.argv.slice(2);
const b = await puppeteer.launch({ executablePath: await chromium.executablePath(), args: [...chromium.args, "--no-sandbox"], headless: true });
const p = await b.newPage(); await p.setViewport({ width: +w, height: +h });
await p.goto("file://" + path.join(ROOT, "release/islamic-history-atlas.html") + hash, { waitUntil: "load" });
await new Promise((r) => setTimeout(r, 3500)); await p.screenshot({ path: out }); await b.close();
