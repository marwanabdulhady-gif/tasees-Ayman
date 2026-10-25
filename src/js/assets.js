/* ===== assets.js — embedded data & vector page loading ===== */
"use strict";
const Assets = (() => {
  let data = null;
  const svgDocs = new Map();      // page -> Promise<SVGDocument|null>
  let vectorSupported = typeof DecompressionStream !== "undefined" && typeof Blob !== "undefined" && !!Blob.prototype.stream;

  function load() {
    const node = document.getElementById("atlas-data");
    if (!node) throw new Error("لم يُعثر على بيانات الأطلس المضمّنة في الملف.");
    data = JSON.parse(node.textContent);
    return data;
  }

  function b64ToBytes(b64) {
    const bin = atob(b64.replace(/\s+/g, ""));
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  async function decodeSvg(page) {
    const node = document.querySelector(`script.svg-data[data-page="${page}"]`);
    if (!node) throw new Error("missing vector data for page " + page);
    const enc = node.dataset.encoding || "gzip+base64";
    let text;
    if (enc === "gzip+base64") {
      if (!vectorSupported) throw new Error("DecompressionStream unsupported");
      const stream = new Blob([b64ToBytes(node.textContent)]).stream().pipeThrough(new DecompressionStream("gzip"));
      text = await new Response(stream).text();
    } else {
      text = node.textContent;
    }
    const doc = new DOMParser().parseFromString(text, "image/svg+xml");
    if (doc.querySelector("parsererror")) throw new Error("SVG parse error on page " + page);
    return doc;
  }

  /** Resolves to the parsed SVG document of a PDF page, or null when vector data
   *  cannot be used (the caller then falls back to the raster render). */
  function pageSvg(page) {
    if (!svgDocs.has(page)) {
      svgDocs.set(page, decodeSvg(page).catch((e) => { console.warn("[atlas] vector fallback:", e.message); vectorSupported = false; return null; }));
    }
    return svgDocs.get(page);
  }

  return {
    load,
    get data() { return data; },
    pageSvg,
    get vectorSupported() { return vectorSupported; },
    thumb: (key) => (data.assets && data.assets.thumbs && data.assets.thumbs[key]) || "",
    pageImage: (page) => (data.assets && data.assets.pages && data.assets.pages[String(page)]) || "",
  };
})();
