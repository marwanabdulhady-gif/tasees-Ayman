/* ==========================================================================
   utils.js — Arabic Normalization, Persistence, Asset & Vector Decompression
   ========================================================================== */
(function () {
  "use strict";

  const AR_DIGITS_MAP = {
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
    "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
    "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
  };
  const EN_TO_AR = ["٠", "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩"];
  const TASHKEEL_RE = /[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]/g;

  function toWesternDigits(str) {
    return String(str || "").replace(/[٠-٩۰-۹]/g, (d) => AR_DIGITS_MAP[d] || d);
  }

  function toArabicDigits(numOrStr) {
    return String(numOrStr ?? "").replace(/[0-9]/g, (d) => EN_TO_AR[Number(d)]);
  }

  function normAr(str) {
    if (!str) return "";
    let s = String(str).replace(/ﷺ/g, " صلى الله عليه وسلم ");
    s = s.replace(TASHKEEL_RE, "").replace(/\u0640/g, "");
    s = s.replace(/[أإآٱ]/g, "ا");
    s = s.replace(/ى/g, "ي").replace(/ؤ/g, "و").replace(/ئ/g, "ي").replace(/ة/g, "ه");
    s = toWesternDigits(s);
    s = s.replace(/[^\w\s\u0621-\u064A]/g, " ");
    return s.replace(/\s+/g, " ").trim().toLowerCase();
  }

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /**
   * Highlights query matches inside original Arabic text without altering
   * the displayed spelling, diacritics, or Alef/Ya/Ta-Marbuta forms.
   */
  function highlightAr(originalText, rawQuery) {
    const text = String(originalText || "");
    const qNorm = normAr(rawQuery);
    if (!qNorm || !text) return escapeHtml(text);

    const tokens = qNorm.split(" ").filter((t) => t.length >= 2);
    if (!tokens.length) return escapeHtml(text);

    // Build regex pattern tolerant of Arabic diacritics, tatweel, and Alef/Ya/Ta variants
    const charPattern = (ch) => {
      if (ch === "ا") return "[اأإآٱ][\\u0610-\\u061A\\u064B-\\u065F\\u0670\\u0640]*";
      if (ch === "ي") return "[يىئ][\\u0610-\\u061A\\u064B-\\u065F\\u0670\\u0640]*";
      if (ch === "ه") return "[هة][\\u0610-\\u061A\\u064B-\\u065F\\u0670\\u0640]*";
      if (ch === "و") return "[وؤ][\\u0610-\\u061A\\u064B-\\u065F\\u0670\\u0640]*";
      if (/[0-9]/.test(ch)) {
        const arD = EN_TO_AR[Number(ch)];
        return `[${ch}${arD}]`;
      }
      const esc = ch.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return `${esc}[\\u0610-\\u061A\\u064B-\\u065F\\u0670\\u0640]*`;
    };

    try {
      const alt = tokens
        .slice(0, 5)
        .map((tok) => tok.split("").map(charPattern).join(""))
        .join("|");
      const rx = new RegExp(`(${alt})`, "gi");
      const parts = text.split(rx);
      if (parts.length <= 1) return escapeHtml(text);
      return parts
        .map((part, idx) => (idx % 2 === 1 ? `<mark>${escapeHtml(part)}</mark>` : escapeHtml(part)))
        .join("");
    } catch (_) {
      return escapeHtml(text);
    }
  }

  function makeSnippet(text, rawQuery, maxLen) {
    const clean = String(text || "").replace(/\s+/g, " ").trim();
    if (!clean) return "";
    const limit = maxLen || 140;
    const qNorm = normAr(rawQuery);
    if (!qNorm) return highlightAr(clean.slice(0, limit) + (clean.length > limit ? "…" : ""), "");

    const firstTok = qNorm.split(" ").find((t) => t.length >= 2) || qNorm;
    const normClean = normAr(clean);
    const pos = normClean.indexOf(firstTok);
    if (pos < 0 || clean.length <= limit) {
      const sub = clean.slice(0, limit) + (clean.length > limit ? "…" : "");
      return highlightAr(sub, rawQuery);
    }
    const approxIdx = Math.max(0, Math.floor((pos / Math.max(1, normClean.length)) * clean.length) - 35);
    const slice = (approxIdx > 0 ? "…" : "") + clean.slice(approxIdx, approxIdx + limit) + (approxIdx + limit < clean.length ? "…" : "");
    return highlightAr(slice, rawQuery);
  }

  // Safe localStorage wrapper (namespaced per edition so full & portable don't collide on file://)
  function getStorageKey() {
    return window.__IS_PORTABLE_EDITION__ ? "arabic_atlas_portable_v2" : "arabic_atlas_platform_v2";
  }
  let memoryFallback = {};

  function loadState() {
    try {
      const raw = window.localStorage.getItem(getStorageKey());
      return raw ? JSON.parse(raw) : {};
    } catch (_) {
      return { ...memoryFallback };
    }
  }

  function saveState(patch) {
    const next = { ...loadState(), ...patch };
    memoryFallback = next;
    try {
      window.localStorage.setItem(getStorageKey(), JSON.stringify(next));
    } catch (_) {
      // Ignore quota or disabled-storage errors gracefully
    }
    return next;
  }

  function clearStoredState() {
    memoryFallback = {};
    try {
      window.localStorage.removeItem(getStorageKey());
    } catch (_) {}
  }

  // Asset URL resolution (supports embedded data URLs in portable single-file build)
  function resolveAsset(relPath) {
    if (!relPath) return "";
    if (window.__PORTABLE_ASSETS__ && window.__PORTABLE_ASSETS__[relPath]) {
      return window.__PORTABLE_ASSETS__[relPath];
    }
    return relPath;
  }

  function isAssetAvailable(relPath) {
    if (!relPath) return false;
    if (window.__IS_PORTABLE_EDITION__) {
      return Boolean(window.__PORTABLE_ASSETS__ && window.__PORTABLE_ASSETS__[relPath]);
    }
    return true;
  }

  // Decompress gzipped base64 SVG for maps8 vector pages
  const svgCache = new Map();

  async function getMaps8SvgText(pageNum) {
    const key = String(pageNum);
    if (svgCache.has(key)) return svgCache.get(key);

    const gzMap = window.__MAPS8_SVG_GZ__ || {};
    const b64 = gzMap[key];
    if (!b64) return null;

    if (typeof DecompressionStream === "function") {
      try {
        const bin = atob(b64);
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        const ds = new DecompressionStream("gzip");
        const stream = new Blob([bytes]).stream().pipeThrough(ds);
        const text = await new Response(stream).text();
        svgCache.set(key, text);
        return text;
      } catch (err) {
        console.warn("SVG decompression fallback:", err);
      }
    }
    return null;
  }

  const CATEGORY_LABELS = {
    "spread-map": "خريطة متجهية مزدوجة",
    "map": "خريطة جغرافية / تاريخية",
    "table-diagram": "جدول / شكل توضيحي",
    "photo-landmark": "صورة / معلم أثري",
    "chapter-divider": "لوحة باب / فصل",
    "narrative-text": "مادة علمية وسرد تاريخي",
    "index-reference": "فهرس / مراجع",
    "cover-frontmatter": "غلاف / مقدمة",
  };

  const VERIFICATION_LABELS = {
    "verified": { text: "محقق بصريًا ومصدريًا", cls: "badge-verified" },
    "partially-verified": { text: "منسوخ بصريًا (جزئي)", cls: "badge-warn" },
    "verified-title-ocr-body": { text: "عنوان مفهرس محقق + نص OCR", cls: "badge-verified" },
    "ocr-text": { text: "نص مستخرج ضوئيًا (OCR)", cls: "badge-ocr" },
    "ocr-needs-review": { text: "يحتاج مراجعة (OCR منخفض الثقة)", cls: "badge-low" },
  };

  function debounce(fn, wait) {
    let t = null;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  window.AtlasUtils = {
    toWesternDigits,
    toArabicDigits,
    normAr,
    escapeHtml,
    highlightAr,
    makeSnippet,
    loadState,
    saveState,
    clearStoredState,
    resolveAsset,
    isAssetAvailable,
    getMaps8SvgText,
    CATEGORY_LABELS,
    VERIFICATION_LABELS,
    debounce,
  };
})();
