#!/usr/bin/env node
/**
 * Builds a standalone, git-tracked, snapshot-safe offline bundle for
 * `atlas-modules/islamic-dynasties` directly inside `public/bundle/` +
 * `public/index.html` WITHOUT duplicating the 136 MB `public/` data folder
 * and WITHOUT `type="module"` / `crossorigin` so it works over both `file://`
 * and `http://` with zero external requests.
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const appRoot = path.join(repoRoot, 'atlas-modules', 'islamic-dynasties');
const publicDir = path.join(appRoot, 'public');
const bundleDir = path.join(publicDir, 'bundle');

const appRequire = createRequire(path.join(appRoot, 'package.json'));
const viteMod = await import(pathToFileURL(appRequire.resolve('vite')).href);
const reactPluginMod = await import(pathToFileURL(appRequire.resolve('@vitejs/plugin-react')).href);

const build = viteMod.build || (viteMod.default && viteMod.default.build);
const react = reactPluginMod.default || reactPluginMod;

fs.rmSync(bundleDir, { recursive: true, force: true });

await build({
  root: appRoot,
  configFile: false,
  base: './',
  publicDir: false,
  plugins: [react()],
  build: {
    outDir: bundleDir,
    emptyOutDir: true,
    copyPublicDir: false,
    cssCodeSplit: false,
    assetsInlineLimit: 8192,
    chunkSizeWarningLimit: 12000,
    rollupOptions: {
      input: path.join(appRoot, 'src', 'main.jsx'),
      output: {
        format: 'iife',
        name: 'IslamicDynastiesAtlasApp',
        inlineDynamicImports: true,
        entryFileNames: 'app.js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name && assetInfo.name.endsWith('.css')) return 'app.css';
          return 'assets/[name]-[hash][extname]';
        },
      },
    },
  },
});

const outHtml = `<!DOCTYPE html>
<html lang="ar" dir="rtl" data-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>أطلس السلالات الإسلامية — Islamic Dynasties Atlas</title>
  <meta name="description" content="أطلس تفاعلي لتاريخ السلالات الإسلامية: ١٨٦ سلالة، ٨٣٠ حاكمًا (٦٣٢–١٩٢٤م)، مرتبط بمسار دورة تأسيس والمحاضرات (الوحدتان ٦ و٧)." />
  <script>
    try {
      const t = localStorage.getItem('atlas-theme');
      if (t) document.documentElement.setAttribute('data-theme', t);
    } catch (e) {}
  </script>
  <link rel="icon" type="image/svg+xml" href="./favicon.svg" />
  <link rel="stylesheet" href="./leaflet/leaflet.css" />
  <link rel="stylesheet" href="./bundle/app.css" />
  <style>
    .tasees-FloatingBridge {
      position: fixed;
      bottom: 14px;
      left: 14px;
      z-index: 9999;
      display: inline-flex;
      gap: 6px;
      align-items: center;
      background: rgba(15, 20, 28, 0.92);
      border: 1px solid rgba(201, 168, 76, 0.45);
      border-radius: 999px;
      padding: 6px 12px;
      font-family: "Tajawal", "Noto Naskh Arabic", system-ui, sans-serif;
      font-size: 12px;
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45);
      backdrop-filter: blur(8px);
    }
    .tasees-FloatingBridge a {
      color: #e8cfa0;
      text-decoration: none;
      font-weight: 700;
      padding: 2px 6px;
    }
    .tasees-FloatingBridge a:hover {
      text-decoration: underline;
      color: #fff;
    }
    .tasees-FloatingBridge span.sep {
      color: rgba(201, 168, 76, 0.4);
    }
    @media (max-width: 768px) {
      .tasees-FloatingBridge {
        top: 56px;
        bottom: auto;
        left: 8px;
        padding: 4px 10px;
        font-size: 11px;
      }
    }
  </style>
</head>
<body>
  <div id="root"></div>
  <nav class="tasees-FloatingBridge" aria-label="روابط منصة تأسيس والأطالس">
    <a href="../../../index.html#tab=courses&unit=6" title="العودة إلى مسار دورة تأسيس والمحاضرات (الوحدتان ٦ و٧)">🧭 مسار دورة تأسيس</a>
    <span class="sep">|</span>
    <a href="../../index.html" title="العودة إلى بوابة الأطالس الإضافية">← الأطالس الإضافية</a>
  </nav>
  <script defer src="./bundle/app.js"></script>
</body>
</html>
`;

fs.writeFileSync(path.join(publicDir, 'index.html'), outHtml, 'utf8');
const jsSize = (fs.statSync(path.join(bundleDir, 'app.js')).size / (1024 * 1024)).toFixed(2);
const cssPath = path.join(bundleDir, 'app.css');
const cssSize = fs.existsSync(cssPath) ? (fs.statSync(cssPath).size / 1024).toFixed(1) : '0';
console.log(`Built offline Islamic Dynasties bundle: app.js=${jsSize} MB, app.css=${cssSize} KB -> public/index.html`);
