/* ==========================================================================
   viewer.js — Hybrid Vector Spread + High-Res Scanned Map & Hotspot Renderer
   ========================================================================== */
(function () {
  "use strict";

  const {
    resolveAsset,
    isAssetAvailable,
    getMaps8SvgText,
    escapeHtml,
    toArabicDigits,
  } = window.AtlasUtils;

  let svgUidCounter = 0;

  /**
   * Namespaces internal SVG ids & url(#...) references so multiple inline SVGs
   * never collide in the DOM (critical for joined spreads & dual compare).
   */
  function namespaceSvgIds(svgMarkup, prefix) {
    const uid = `${prefix}_${++svgUidCounter}_`;
    return svgMarkup
      .replace(/\bid="([^"]+)"/g, (_, id) => `id="${uid}${id}"`)
      .replace(/url\(#([^)]+)\)/g, (_, id) => `url(#${uid}${id})`)
      .replace(/(xlink:href|href)="#([^"]+)"/g, (_, attr, id) => `${attr}="#${uid}${id}"`);
  }

  function extractSvgInner(svgMarkup) {
    const m = svgMarkup.match(/<svg[^>]*>([\s\S]*?)<\/svg>/i);
    return m ? m[1] : svgMarkup;
  }

  /**
   * Renders a joined 2-page vector spread for Volume 1 (maps8) inside worldEl,
   * complete with separable cartographic layers and glyph-anchored hotspots.
   */
  async function renderMaps8Spread({
    worldEl,
    panzoom,
    maps8Vol,
    figure,
    hiddenLayers,
    showHotspots,
    selectedFeatureId,
    onSelectFeature,
    onHoverFeature,
    quizHideLabels,
  }) {
    worldEl.innerHTML = `<div style="padding:32px;color:#555;font-family:inherit">جاري تركيب الخريطة المتجهية المزدوجة…</div>`;

    const [eastRaw, westRaw] = await Promise.all([
      getMaps8SvgText(figure.eastPage),
      getMaps8SvgText(figure.westPage),
    ]);

    // Fallback to side-by-side raster images if DecompressionStream unavailable
    if (!eastRaw || !westRaw) {
      const wImg = resolveAsset(`assets/pages/maps8/page-${String(figure.westPage).padStart(3, "0")}.webp`);
      const eImg = resolveAsset(`assets/pages/maps8/page-${String(figure.eastPage).padStart(3, "0")}.webp`);
      worldEl.innerHTML = `
        <div class="page-frame" style="display:flex;width:1190px;height:842px">
          <img src="${wImg}" alt="" style="width:595px;height:842px" />
          <img src="${eImg}" alt="" style="width:595px;height:842px" />
        </div>`;
      panzoom.setContentSize(1190, 842, 0);
      return { mode: "raster-fallback", scaleFactor: 1 };
    }

    const westInner = extractSvgInner(namespaceSvgIds(westRaw, `w${figure.westPage}`));
    const eastInner = extractSvgInner(namespaceSvgIds(eastRaw, `e${figure.eastPage}`));

    const [vx, vy, vw, vh] = figure.spreadViewBox;
    const padX = 18;
    const topY = Math.max(0, vy - 16);
    const botY = Math.max(vy + vh + 22, 790); // include figure caption at y ~ 765
    const boxX = vx - padX;
    const boxW = vw + padX * 2;
    const boxH = botY - topY;

    const [wx0, wy0, wx1, wy1] = figure.westClip;
    const [ex0, ey0, ex1] = figure.eastClip;
    const clipUid = `spclip_${++svgUidCounter}`;

    // Build clickable SVG hotspots for all features in this figure
    const feats = (maps8Vol.features || []).filter(
      (f) => f.figure === figure.id && f.kind !== "unreadable"
    );

    const hotspotEls = [];
    for (const ft of feats) {
      const isSel = ft.id === selectedFeatureId ? " is-selected" : "";
      if (ft.spreadPoly && ft.spreadPoly.length >= 3) {
        const pts = ft.spreadPoly.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
        hotspotEls.push(
          `<polygon class="vec-hotspot${isSel}" tabindex="0" role="button" data-fid="${ft.id}" aria-label="${escapeHtml(ft.text)}" points="${pts}" />`
        );
      } else if (ft.spreadRects && ft.spreadRects.length) {
        // Compute tight union or individual word rects inside one <g>
        const rectsMarkup = ft.spreadRects
          .map(([x0, y0, x1, y1]) => {
            const pad = 2.2;
            return `<rect x="${(x0 - pad).toFixed(1)}" y="${(y0 - pad).toFixed(1)}" width="${Math.max(6, x1 - x0 + pad * 2).toFixed(1)}" height="${Math.max(6, y1 - y0 + pad * 2).toFixed(1)}" rx="2" />`;
          })
          .join("");
        const markerMarkup = ft.spreadMarker
          ? `<circle cx="${ft.spreadMarker[0].toFixed(1)}" cy="${ft.spreadMarker[1].toFixed(1)}" r="5.5" />`
          : "";
        hotspotEls.push(
          `<g class="vec-hotspot${isSel}" tabindex="0" role="button" data-fid="${ft.id}" aria-label="${escapeHtml(ft.text)}">${rectsMarkup}${markerMarkup}</g>`
        );
      }
    }

    const scalePx = 1.65; // crisp base pixel sizing for panzoom coordinate space
    const svgW = Math.round(boxW * scalePx);
    const svgH = Math.round(boxH * scalePx);

    const layerClasses = [];
    for (const lyr of hiddenLayers || []) layerClasses.push(`hide-${lyr}`);
    if (quizHideLabels) layerClasses.push("hide-label");
    if (showHotspots) layerClasses.push("show-hotspots");

    worldEl.innerHTML = `
      <svg class="vector-spread-svg ${layerClasses.join(" ")}"
           width="${svgW}" height="${svgH}"
           viewBox="${boxX.toFixed(2)} ${topY.toFixed(2)} ${boxW.toFixed(2)} ${boxH.toFixed(2)}"
           xmlns="http://www.w3.org/2000/svg"
           xmlns:xlink="http://www.w3.org/1999/xlink">
        <defs>
          <clipPath id="${clipUid}_west">
            <rect x="${wx0}" y="${wy0}" width="${(wx1 - wx0).toFixed(2)}" height="${(wy1 - wy0).toFixed(2)}" />
          </clipPath>
          <clipPath id="${clipUid}_east">
            <rect x="${ex0}" y="${Math.max(0, ey0 - 8)}" width="${(ex1 - ex0 + 18).toFixed(2)}" height="${(795 - Math.max(0, ey0 - 8)).toFixed(2)}" />
          </clipPath>
        </defs>
        <rect x="${boxX}" y="${topY}" width="${boxW}" height="${boxH}" fill="#ffffff" />
        <g clip-path="url(#${clipUid}_west)">${westInner}</g>
        <g transform="translate(${figure.eastOffsetX}, 0)">
          <g clip-path="url(#${clipUid}_east)">${eastInner}</g>
        </g>
        <g class="hotspots-group">${hotspotEls.join("")}</g>
      </svg>
    `;

    const svgEl = worldEl.querySelector("svg.vector-spread-svg");
    panzoom.setContentSize(svgW, svgH, 0);

    // Wire events
    const findFeat = (el) => {
      const node = el && el.closest ? el.closest("[data-fid]") : null;
      if (!node) return null;
      const fid = node.getAttribute("data-fid");
      return feats.find((f) => f.id === fid) || null;
    };

    svgEl.addEventListener("click", (e) => {
      if (panzoom.wasDragging()) return;
      const ft = findFeat(e.target);
      if (ft && onSelectFeature) onSelectFeature(ft, svgEl);
    });

    svgEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        const ft = findFeat(e.target);
        if (ft && onSelectFeature) {
          e.preventDefault();
          onSelectFeature(ft, svgEl);
        }
      }
    });

    svgEl.addEventListener("pointermove", (e) => {
      const ft = findFeat(e.target);
      if (onHoverFeature) onHoverFeature(ft, e.clientX, e.clientY);
    });
    svgEl.addEventListener("pointerleave", () => {
      if (onHoverFeature) onHoverFeature(null, 0, 0);
    });

    return {
      mode: "vector-spread",
      svgEl,
      boxX,
      topY,
      scalePx,
      focusFeature(fid) {
        const ft = feats.find((f) => f.id === fid);
        if (!ft || !ft.spreadRects || !ft.spreadRects.length) return;
        let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
        for (const r of ft.spreadRects) {
          x0 = Math.min(x0, r[0]);
          y0 = Math.min(y0, r[1]);
          x1 = Math.max(x1, r[2]);
          y1 = Math.max(y1, r[3]);
        }
        const px = (x0 - boxX) * scalePx;
        const py = (y0 - topY) * scalePx;
        const pw = (x1 - x0) * scalePx;
        const ph = (y1 - y0) * scalePx;
        panzoom.focusRect(px, py, pw, ph);
      },
    };
  }

  /**
   * Renders a high-resolution scanned page (seerah / abubakr / maps8 single page)
   * with verified coordinate hotspots, optional OCR word boxes, and search-hit highlights.
   */
  function renderScannedPage({
    worldEl,
    panzoom,
    page,
    ocrWords,
    showHotspots,
    showOcrLayer,
    selectedHotspotId,
    highlightQuery,
    initialRotation,
    onSelectHotspot,
    onSelectOcrWord,
    onHoverItem,
  }) {
    const w = page.width || 816;
    const h = page.height || 1146;
    const assetAvailable = isAssetAvailable(page.pageAsset);
    const imgSrc = resolveAsset(page.pageAsset);

    if (!assetAvailable) {
      const totalPagesCount = (window.__ATLAS_MANIFEST__ && window.__ATLAS_MANIFEST__.pages && window.__ATLAS_MANIFEST__.pages.length) || 1069;
      worldEl.innerHTML = `
        <div class="page-frame" style="width:${w}px;height:${h}px;padding:48px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;background:#faf6ec;direction:rtl">
          <span class="badge badge-warn" style="margin-bottom:12px">النسخة المحمولة المختصرة (ملف HTML واحد)</span>
          <h3 style="margin:0 0 8px 0">${escapeHtml(page.title)}</h3>
          <p style="max-width:520px;color:#43515c;font-size:14px">
            للحفاظ على خفة النسخة المحمولة ذات الملف الواحد، ضُمِّنت الخرائط المتجهية المزدوجة كاملةً مع ٤٤ خريطة محورية عالية الدقة وجميع البيانات والفهارس والنصوص القابلة للبحث لـ ${toArabicDigits(totalPagesCount)} صفحة.
            لعرض الصورة النقطية الكاملة لهذه الصفحة (ص ${toArabicDigits(page.sourcePage)})، افتح الحزمة الكاملة غير المتصلة بالإنترنت (<code>index.html</code> مع مجلد <code>assets/</code>).
          </p>
        </div>`;
      panzoom.setContentSize(w, h, 0);
      return { mode: "portable-placeholder" };
    }

    // Verified hotspots (percentage coordinates x, y, w, h)
    const hsHtml = (page.hotspots || [])
      .map((hs, idx) => {
        const isSel = hs.id === selectedHotspotId ? " is-selected" : "";
        return `
          <div class="raster-hotspot${isSel}"
               tabindex="0" role="button"
               data-hsid="${escapeHtml(hs.id)}"
               aria-label="${escapeHtml(hs.name)}"
               style="left:${hs.x}%;top:${hs.y}%;width:${hs.w}%;height:${hs.h}%">
            <span class="hs-pin">${toArabicDigits(idx + 1)}</span>
          </div>`;
      })
      .join("");

    // OCR Word boxes (optional layer)
    let ocrHtml = "";
    if (showOcrLayer && Array.isArray(ocrWords)) {
      ocrHtml = ocrWords
        .map((wItem, idx) => {
          const [wt, x0, y0, x1, y1, conf] = wItem;
          return `<div class="ocr-word-box" data-ocridx="${idx}"
                       title="${escapeHtml(wt)} (ثقة OCR: ${conf}%)"
                       style="left:${x0}px;top:${y0}px;width:${Math.max(8, x1 - x0)}px;height:${Math.max(8, y1 - y0)}px"></div>`;
        })
        .join("");
    }

    // Search query highlight boxes on scanned page
    let hitsHtml = "";
    const hitRects = [];
    if (highlightQuery && Array.isArray(ocrWords)) {
      const qNorm = window.AtlasUtils.normAr(highlightQuery);
      const tokens = qNorm.split(" ").filter((t) => t.length >= 2);
      if (tokens.length) {
        for (const wItem of ocrWords) {
          const [wt, x0, y0, x1, y1] = wItem;
          if (page.volumeId !== "maps8" && page.sourcePage >= 9 && y1 < h * 0.09) continue;
          const wn = window.AtlasUtils.normAr(wt);
          if (wn && tokens.some((tk) => wn.includes(tk) || (wn.length >= 3 && tk.includes(wn)))) {
            const pad = 4;
            hitRects.push([x0 - pad, y0 - pad, x1 - x0 + pad * 2, y1 - y0 + pad * 2]);
            hitsHtml += `<div class="search-hit-box" style="left:${x0 - pad}px;top:${y0 - pad}px;width:${Math.max(12, x1 - x0 + pad * 2)}px;height:${Math.max(12, y1 - y0 + pad * 2)}px"></div>`;
          }
        }
      }
    }

    worldEl.innerHTML = `
      <div class="page-frame ${showHotspots ? "" : "hide-hotspots"}" style="width:${w}px;height:${h}px">
        <img class="page-raster" src="${imgSrc}" alt="${escapeHtml(page.title)}" width="${w}" height="${h}" decoding="async" />
        <div class="overlay-layer">${ocrHtml}${hitsHtml}${hsHtml}</div>
      </div>
    `;

    const rot = typeof initialRotation === "number" ? initialRotation : 0;
    panzoom.setContentSize(w, h, rot);

    // Auto-focus first search hit if present
    if (hitRects.length > 0) {
      const [hx, hy, hw, hh] = hitRects[0];
      setTimeout(() => panzoom.focusRect(hx, hy, hw, hh), 40);
    }

    const frameEl = worldEl.querySelector(".page-frame");
    frameEl.addEventListener("click", (e) => {
      if (panzoom.wasDragging()) return;
      const hsNode = e.target.closest("[data-hsid]");
      if (hsNode) {
        const hsid = hsNode.getAttribute("data-hsid");
        const hs = (page.hotspots || []).find((x) => x.id === hsid);
        if (hs && onSelectHotspot) onSelectHotspot(hs);
        return;
      }
      const ocrNode = e.target.closest("[data-ocridx]");
      if (ocrNode && Array.isArray(ocrWords)) {
        const wItem = ocrWords[Number(ocrNode.getAttribute("data-ocridx"))];
        if (wItem && onSelectOcrWord) onSelectOcrWord(wItem);
      }
    });

    frameEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        const hsNode = e.target.closest("[data-hsid]");
        if (hsNode) {
          e.preventDefault();
          const hsid = hsNode.getAttribute("data-hsid");
          const hs = (page.hotspots || []).find((x) => x.id === hsid);
          if (hs && onSelectHotspot) onSelectHotspot(hs);
        }
      }
    });

    frameEl.addEventListener("pointermove", (e) => {
      const hsNode = e.target.closest("[data-hsid]");
      if (hsNode && onHoverItem) {
        const hsid = hsNode.getAttribute("data-hsid");
        const hs = (page.hotspots || []).find((x) => x.id === hsid);
        onHoverItem(hs ? hs.name : null, e.clientX, e.clientY);
        return;
      }
      const ocrNode = e.target.closest("[data-ocridx]");
      if (ocrNode && onHoverItem && Array.isArray(ocrWords)) {
        const wItem = ocrWords[Number(ocrNode.getAttribute("data-ocridx"))];
        onHoverItem(wItem ? `${wItem[0]} (OCR: ${wItem[5]}%)` : null, e.clientX, e.clientY);
        return;
      }
      if (onHoverItem) onHoverItem(null, 0, 0);
    });

    frameEl.addEventListener("pointerleave", () => {
      if (onHoverItem) onHoverItem(null, 0, 0);
    });

    return {
      mode: "scanned-page",
      focusHotspot(hsid) {
        const hs = (page.hotspots || []).find((x) => x.id === hsid);
        if (!hs) return;
        panzoom.focusRect((hs.x / 100) * w, (hs.y / 100) * h, (hs.w / 100) * w, (hs.h / 100) * h);
      },
    };
  }

  /**
   * Builds a pure CSS-clipped source-page crop preview (works 100% on file:// and http://
   * with zero canvas CORS taint errors!).
   */
  function buildSourceCropHtml({ pageAsset, imgW, imgH, cropRect, maxBoxW = 270 }) {
    if (!isAssetAvailable(pageAsset)) return "";
    const src = resolveAsset(pageAsset);
    let [cx, cy, cw, ch] = cropRect;
    const padX = Math.max(18, cw * 0.35);
    const padY = Math.max(14, ch * 0.45);
    const rx = Math.max(0, cx - padX);
    const ry = Math.max(0, cy - padY);
    const rw = Math.min(imgW - rx, cw + padX * 2);
    const rh = Math.min(imgH - ry, ch + padY * 2);

    const scale = Math.min(maxBoxW / Math.max(1, rw), 160 / Math.max(1, rh), 2.2);
    const dispW = Math.round(rw * scale);
    const dispH = Math.round(rh * scale);

    return `
      <div class="crop-preview-wrap">
        <div style="width:${dispW}px;height:${dispH}px;overflow:hidden;position:relative;margin-inline:auto;border-radius:4px;border:1px solid var(--border-subtle);background:#fff;direction:ltr">
          <img src="${src}" alt="مقتطف من الصفحة الأصلية"
               style="position:absolute;left:${(-rx * scale).toFixed(1)}px;top:${(-ry * scale).toFixed(1)}px;width:${(imgW * scale).toFixed(1)}px;height:${(imgH * scale).toFixed(1)}px;max-width:none;pointer-events:none" />
        </div>
        <div class="crop-caption">مقتطف بصري مباشر من الصفحة الأصلية للتحقق المصدري</div>
      </div>
    `;
  }

  window.AtlasViewer = {
    renderMaps8Spread,
    renderScannedPage,
    buildSourceCropHtml,
  };
})();
