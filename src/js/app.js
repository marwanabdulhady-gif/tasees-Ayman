/* ==========================================================================
   app.js — Main Controller for the 5-Volume Interactive Arabic Atlas Platform
   ========================================================================== */
(function () {
  "use strict";

  const {
    normAr,
    toArabicDigits,
    escapeHtml,
    loadState,
    saveState,
    clearStoredState,
    resolveAsset,
    gunzipBase64Json,
    CATEGORY_LABELS,
    VERIFICATION_LABELS,
    debounce,
  } = window.AtlasUtils;
  const { PanZoomController } = window.AtlasPanZoom;
  const { renderMaps8Spread, renderScannedPage, buildSourceCropHtml } = window.AtlasViewer;
  const { AtlasSearchEngine } = window.AtlasSearch;
  const { ComparisonController } = window.AtlasCompare;
  const { LearningController } = window.AtlasLearn;

  function initApp() {
    const manifest = window.__ATLAS_MANIFEST__;
    const ocrWordsMap = window.__ATLAS_OCR_WORDS__ || {};
    if (!manifest) {
      document.body.innerHTML = `<div style="padding:40px;text-align:center">تعذّر تحميل بيانات الأطلس (manifest). تأكد من وجود ملف <code>data/atlas-bundle.js</code>.</div>`;
      return;
    }

    const pageById = new Map(manifest.pages.map((p) => [p.id, p]));
    const volById = new Map(manifest.volumes.map((v) => [v.id, v]));
    const searchEngine = new AtlasSearchEngine(manifest);

    // Persisted user preferences
    const persisted = loadState();
    const state = {
      activeTab: "explore", // explore | toc | original | compare | gazetteer | learn | audit
      activeVolumeId: persisted.activeVolumeId || "maps8",
      lastPageByVol: Object.assign(
        {
          maps8: "maps8-001",
          seerah: "seerah-018",
          abubakr: "abubakr-011",
          umar: "umar-038",
          uthman: "uthman-042",
          ali: "ali-131",
        },
        persisted.lastPageByVol || {}
      ),
      currentPageId: persisted.currentPageId || "maps8-001",
      bookmarks: persisted.bookmarks || [],
      recentPages: persisted.recentPages || [],
      theme: persisted.theme || "light",
      referenceOnly: Boolean(persisted.referenceOnly),
      showHotspots: true,
      showOcrLayer: false,
      showFilmstrip: true,
      hiddenVectorLayers: new Set(),
      selectedFeature: null, // { type: 'vector'|'hotspot'|'ocr', data: ... }
      highlightQuery: "",
      // Navigator filters
      navFilterCat: "all",
      navFilterQuery: "",
      // TOC state
      tocVol: "all",
      tocCat: "all",
      tocListMode: "gallery", // gallery | compact
      tocSubset: "all", // all | bookmarks | recent
      tocQuery: "",
      // Gazetteer state
      gazLetter: "all",
      gazVol: "all",
      gazCrossOnly: false,
      gazQuery: "",
      // Original viewer state
      origSplitVerify: false,
    };

    if (!pageById.has(state.currentPageId)) {
      state.currentPageId = "maps8-001";
    }

    // Apply initial theme & reference-only mode
    document.documentElement.setAttribute("data-theme", state.theme);

    // DOM References
    const elSearchInput = document.getElementById("global-search-input");
    const elSearchClear = document.getElementById("global-search-clear");
    const elSearchDropdown = document.getElementById("search-dropdown");
    const elSearchList = document.getElementById("search-results-list");
    const elSearchVolFilter = document.getElementById("search-vol-filter");
    const elSearchTierFilter = document.getElementById("search-tier-filter");
    const elSearchCount = document.getElementById("search-count-label");

    const elVolPills = document.getElementById("volume-pills");
    const elContextCrumb = document.getElementById("context-crumb");
    const elTooltip = document.getElementById("map-tooltip");

    // Explorer DOM
    const elSideDrawer = document.getElementById("explorer-side-drawer");
    const elInfoDrawer = document.getElementById("explorer-info-drawer");
    const elNavCatSelect = document.getElementById("nav-cat-select");
    const elNavFilterInput = document.getElementById("nav-filter-input");
    const elNavigatorList = document.getElementById("navigator-list");
    const elViewport = document.getElementById("explorer-viewport");
    const elWorld = document.getElementById("explorer-world");
    const elZoomReadout = document.getElementById("zoom-readout");
    const elRotateBanner = document.getElementById("rotate-banner");
    const elFilmstrip = document.getElementById("explorer-filmstrip");
    const elInfoContent = document.getElementById("explorer-info-content");

    // Controllers
    const explorerPz = new PanZoomController(elViewport, elWorld, {
      onChange: (st) => {
        elZoomReadout.textContent = `${toArabicDigits(Math.round(st.scale * 100))}%`;
      },
    });
    let activeViewerHandle = null;
    let compareCtrl = null;
    let learnCtrl = null;
    let origPzMain = null;
    let origPzInteractive = null;

    // Tooltip helper
    function showTooltip(text, x, y) {
      if (!text) {
        elTooltip.hidden = true;
        return;
      }
      elTooltip.textContent = text;
      elTooltip.hidden = false;
      const pad = 14;
      const left = Math.min(window.innerWidth - 260, Math.max(8, x + pad));
      const top = Math.min(window.innerHeight - 60, Math.max(8, y + pad));
      elTooltip.style.left = `${left}px`;
      elTooltip.style.top = `${top}px`;
    }

    // Track recent pages
    function recordRecent(pageId) {
      state.recentPages = [pageId, ...state.recentPages.filter((id) => id !== pageId)].slice(0, 24);
      saveState({
        currentPageId: state.currentPageId,
        activeVolumeId: state.activeVolumeId,
        lastPageByVol: state.lastPageByVol,
        recentPages: state.recentPages,
      });
    }

    function toggleBookmark(pageId) {
      if (state.bookmarks.includes(pageId)) {
        state.bookmarks = state.bookmarks.filter((id) => id !== pageId);
      } else {
        state.bookmarks = [pageId, ...state.bookmarks];
      }
      saveState({ bookmarks: state.bookmarks });
      renderExplorerInfo();
      if (state.activeTab === "toc") renderTocView();
    }

    // ==================== Header & Volume Switcher ====================
    function syncHeaderUi() {
      document.querySelectorAll(".nav-tab[data-tab]").forEach((btn) => {
        const t = btn.getAttribute("data-tab");
        if (t === "learn") {
          btn.hidden = state.referenceOnly;
        }
        btn.classList.toggle("is-active", t === state.activeTab);
        btn.setAttribute("aria-selected", t === state.activeTab ? "true" : "false");
      });

      document.querySelectorAll(".view-panel[data-view]").forEach((panel) => {
        panel.hidden = panel.getAttribute("data-view") !== state.activeTab;
      });

      const themeBtn = document.getElementById("btn-theme-toggle");
      if (themeBtn) {
        themeBtn.textContent = state.theme === "dark" ? "الوضع النهاري ☀" : "الوضع الليلي ☾";
      }

      // Render volume pills
      elVolPills.innerHTML = manifest.volumes
        .map((vol) => {
          const isAct = vol.id === state.activeVolumeId ? "is-active" : "";
          const countTxt =
            vol.id === "maps8"
              ? "٤ خرائط متجهية (٨ ص)"
              : `${toArabicDigits(vol.pageCount)} ص`;
          return `
            <button type="button" class="vol-pill ${isAct}" data-vol="${vol.id}">
              <span>${escapeHtml(vol.shortTitle)}</span>
              <span class="vol-count">${countTxt}</span>
            </button>`;
        })
        .join("");

      elVolPills.querySelectorAll("[data-vol]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const vid = btn.getAttribute("data-vol");
          switchVolume(vid);
        });
      });

      const curPage = pageById.get(state.currentPageId);
      if (curPage) {
        const vol = volById.get(curPage.volumeId);
        const bm = state.bookmarks.includes(curPage.id);
        elContextCrumb.innerHTML = `
          <span>${escapeHtml(vol.shortTitle)}</span>
          <span>‹</span>
          <strong>ص ${toArabicDigits(curPage.sourcePage)} من ${toArabicDigits(vol.pageCount)}</strong>
          <button type="button" class="btn ${bm ? "is-on" : ""}" id="crumb-bm-btn" style="padding:2px 8px;font-size:11.5px">
            ${bm ? "محفوظة ★" : "حفظ ☆"}
          </button>
        `;
        const bmBtn = document.getElementById("crumb-bm-btn");
        if (bmBtn) bmBtn.addEventListener("click", () => toggleBookmark(curPage.id));
      }
    }

    function switchTab(tabName) {
      if (tabName === "learn" && state.referenceOnly) tabName = "explore";
      state.activeTab = tabName;
      syncHeaderUi();

      if (tabName === "explore") {
        renderExplorerAll();
      } else if (tabName === "toc") {
        renderTocView();
      } else if (tabName === "original") {
        renderOriginalView();
      } else if (tabName === "compare") {
        if (!compareCtrl) {
          compareCtrl = new ComparisonController(
            document.getElementById("view-compare"),
            manifest,
            (pid) => openPageInExplorer(pid)
          );
        }
        compareCtrl.render();
      } else if (tabName === "gazetteer") {
        renderGazetteerView();
      } else if (tabName === "learn") {
        if (!learnCtrl) {
          learnCtrl = new LearningController(
            document.getElementById("view-learn"),
            manifest,
            (pid) => openPageInExplorer(pid)
          );
        }
        learnCtrl.render();
      } else if (tabName === "audit") {
        renderAuditView();
      }
    }

    function switchVolume(volumeId) {
      if (!volById.has(volumeId)) return;
      state.activeVolumeId = volumeId;
      const targetPageId = state.lastPageByVol[volumeId] || `${volumeId}-001`;
      state.currentPageId = pageById.has(targetPageId) ? targetPageId : `${volumeId}-001`;
      state.selectedFeature = null;
      state.highlightQuery = "";
      recordRecent(state.currentPageId);

      if (state.activeTab === "toc") {
        state.tocVol = volumeId;
        syncHeaderUi();
        renderTocView();
      } else if (state.activeTab === "original") {
        syncHeaderUi();
        renderOriginalView();
      } else {
        state.activeTab = "explore";
        syncHeaderUi();
        renderExplorerAll();
      }
    }

    function openPageInExplorer(pageId, opts = {}) {
      const page = pageById.get(pageId);
      if (!page) return;
      state.currentPageId = page.id;
      state.activeVolumeId = page.volumeId;
      state.lastPageByVol[page.volumeId] = page.id;
      state.selectedFeature = opts.selectedFeature || null;
      state.highlightQuery = opts.highlightQuery || "";
      state.activeTab = opts.targetTab || "explore";
      recordRecent(page.id);
      syncHeaderUi();

      if (state.activeTab === "original") {
        renderOriginalView();
      } else {
        renderExplorerAll(opts);
      }
    }

    // ==================== Module A, B, F: Interactive Explorer ====================
    function getVolumeFilteredPages() {
      const pages = manifest.pages.filter((p) => p.volumeId === state.activeVolumeId);
      const qNorm = normAr(state.navFilterQuery);
      return pages.filter((p) => {
        if (state.navFilterCat === "maps" && p.category !== "map" && p.category !== "spread-map") return false;
        if (state.navFilterCat === "tables" && p.category !== "table-diagram") return false;
        if (state.navFilterCat === "photos" && p.category !== "photo-landmark") return false;
        if (qNorm && !p.titleNorm.includes(qNorm) && !String(p.sourcePage).includes(qNorm)) return false;
        return true;
      });
    }

    function renderNavigatorSidebar() {
      const list = getVolumeFilteredPages();
      if (!list.length) {
        elNavigatorList.innerHTML = `<li style="padding:18px;text-align:center;color:var(--ink-muted);font-size:12.5px">لا توجد صفحات تطابق التصفية الحالية.</li>`;
        return;
      }

      // For maps8, show the 4 joined spreads prominently + individual halves note
      if (state.activeVolumeId === "maps8" && !state.navFilterQuery) {
        const maps8Vol = volById.get("maps8");
        elNavigatorList.innerHTML = maps8Vol.figures
          .map((fig) => {
            const eastPid = `maps8-${String(fig.eastPage).padStart(3, "0")}`;
            const westPid = `maps8-${String(fig.westPage).padStart(3, "0")}`;
            const cur = state.currentPageId === eastPid || state.currentPageId === westPid;
            const thumb = resolveAsset(`assets/thumbs/maps8/page-${String(fig.eastPage).padStart(3, "0")}.webp`);
            return `
              <li class="nav-page-item ${cur ? "is-current" : ""}" data-pid="${eastPid}">
                <img class="nav-page-thumb" src="${thumb}" alt="" loading="lazy" />
                <div class="nav-page-meta">
                  <div class="nav-page-title">${escapeHtml(fig.caption)}</div>
                  <div class="nav-page-sub">
                    <span>ص ${toArabicDigits(fig.eastPage)}–${toArabicDigits(fig.westPage)}</span>
                    <span>·</span>
                    <span>${toArabicDigits(fig.featureCount)} تسمية تفاعلية</span>
                  </div>
                </div>
              </li>`;
          })
          .join("");
      } else {
        elNavigatorList.innerHTML = list
          .map((p) => {
            const cur = p.id === state.currentPageId;
            const thumb = resolveAsset(p.thumbAsset);
            const catLbl = CATEGORY_LABELS[p.category] || p.category;
            return `
              <li class="nav-page-item ${cur ? "is-current" : ""}" data-pid="${p.id}">
                <img class="nav-page-thumb" src="${thumb}" alt="" loading="lazy" />
                <div class="nav-page-meta">
                  <div class="nav-page-title">${escapeHtml(p.title)}</div>
                  <div class="nav-page-sub">
                    <strong>ص ${toArabicDigits(p.sourcePage)}</strong>
                    <span>·</span>
                    <span>${escapeHtml(catLbl)}</span>
                  </div>
                </div>
              </li>`;
          })
          .join("");
      }

      elNavigatorList.querySelectorAll("[data-pid]").forEach((li) => {
        li.addEventListener("click", () => {
          elSideDrawer.classList.remove("is-open");
          openPageInExplorer(li.getAttribute("data-pid"));
        });
      });

      const activeItem = elNavigatorList.querySelector(".nav-page-item.is-current");
      if (activeItem && activeItem.scrollIntoView) {
        activeItem.scrollIntoView({ block: "nearest" });
      }
    }

    function renderFilmstrip() {
      elFilmstrip.hidden = !state.showFilmstrip;
      if (!state.showFilmstrip) return;

      const vPages = manifest.pages.filter((p) => p.volumeId === state.activeVolumeId);
      elFilmstrip.innerHTML = vPages
        .map((p) => {
          const cur = p.id === state.currentPageId ? "is-current" : "";
          return `
            <button type="button" class="film-item ${cur}" data-fpid="${p.id}" title="${escapeHtml(p.title)}">
              <img src="${resolveAsset(p.thumbAsset)}" alt="" loading="lazy" />
              <span>${toArabicDigits(p.sourcePage)}</span>
            </button>`;
        })
        .join("");

      elFilmstrip.querySelectorAll("[data-fpid]").forEach((btn) => {
        btn.addEventListener("click", () => openPageInExplorer(btn.getAttribute("data-fpid")));
      });

      const curBtn = elFilmstrip.querySelector(".film-item.is-current");
      if (curBtn && curBtn.scrollIntoView) {
        curBtn.scrollIntoView({ inline: "center", block: "nearest" });
      }
    }

    async function renderExplorerCanvas(opts = {}) {
      const page = pageById.get(state.currentPageId);
      if (!page) return;

      // Toolbar active toggles
      document.getElementById("btn-toggle-hotspots").classList.toggle("is-on", state.showHotspots);
      const ocrBtn = document.getElementById("btn-toggle-ocr");
      ocrBtn.hidden = page.volumeId === "maps8";
      ocrBtn.classList.toggle("is-on", state.showOcrLayer);

      // Rotate banner for sideways maps
      if (page.rotated && explorerPz.rotation === 0) {
        elRotateBanner.hidden = false;
        elRotateBanner.innerHTML = `
          <span>تنبيه بصري: طُبعت هذه الخريطة بالوضع الأفقي في الكتاب الأصلي.</span>
          <button type="button" class="btn btn-primary" id="btn-auto-upright" style="padding:3px 10px;font-size:12px">
            تدوير للوضع القرائي المعتدل ↻
          </button>`;
        document.getElementById("btn-auto-upright").addEventListener("click", () => {
          explorerPz.setRotation(page.rotated);
          elRotateBanner.hidden = true;
        });
      } else {
        elRotateBanner.hidden = true;
      }

      if (page.volumeId === "maps8") {
        const maps8Vol = volById.get("maps8");
        const fig = maps8Vol.figures.find((f) => f.id === page.figureId) || maps8Vol.figures[0];
        const selFid =
          state.selectedFeature && state.selectedFeature.type === "vector"
            ? state.selectedFeature.data.id
            : null;

        activeViewerHandle = await renderMaps8Spread({
          worldEl: elWorld,
          panzoom: explorerPz,
          maps8Vol,
          figure: fig,
          hiddenLayers: state.hiddenVectorLayers,
          showHotspots: state.showHotspots,
          selectedFeatureId: selFid,
          onSelectFeature: (ft) => {
            state.selectedFeature = { type: "vector", data: ft };
            // Update visual highlight without resetting zoom
            elWorld.querySelectorAll(".vec-hotspot").forEach((el) => {
              el.classList.toggle("is-selected", el.getAttribute("data-fid") === ft.id);
            });
            renderExplorerInfo();
            if (window.innerWidth <= 900) elInfoDrawer.classList.add("is-open");
          },
          onHoverFeature: (ft, cx, cy) => {
            showTooltip(ft ? `${ft.text} (${ft.kindLabel})` : null, cx, cy);
          },
        });

        if (opts.focusFeatureId && activeViewerHandle && activeViewerHandle.focusFeature) {
          setTimeout(() => activeViewerHandle.focusFeature(opts.focusFeatureId), 40);
        }
      } else {
        const words = ocrWordsMap[page.id] || [];
        const selHid =
          state.selectedFeature && state.selectedFeature.type === "hotspot"
            ? state.selectedFeature.data.id
            : null;

        activeViewerHandle = renderScannedPage({
          worldEl: elWorld,
          panzoom: explorerPz,
          page,
          ocrWords: words,
          showHotspots: state.showHotspots,
          showOcrLayer: state.showOcrLayer,
          selectedHotspotId: selHid,
          highlightQuery: state.highlightQuery,
          initialRotation: opts.autoRotateUpright && page.rotated ? page.rotated : 0,
          onSelectHotspot: (hs) => {
            state.selectedFeature = { type: "hotspot", data: hs };
            elWorld.querySelectorAll(".raster-hotspot").forEach((el) => {
              el.classList.toggle("is-selected", el.getAttribute("data-hsid") === hs.id);
            });
            renderExplorerInfo();
            if (window.innerWidth <= 900) elInfoDrawer.classList.add("is-open");
          },
          onSelectOcrWord: (wItem) => {
            state.selectedFeature = {
              type: "ocr",
              data: { word: wItem[0], bbox: [wItem[1], wItem[2], wItem[3], wItem[4]], conf: wItem[5] },
            };
            renderExplorerInfo();
            if (window.innerWidth <= 900) elInfoDrawer.classList.add("is-open");
          },
          onHoverItem: (label, cx, cy) => showTooltip(label, cx, cy),
        });

        if (opts.focusHotspotId && activeViewerHandle && activeViewerHandle.focusHotspot) {
          setTimeout(() => activeViewerHandle.focusHotspot(opts.focusHotspotId), 40);
        }
      }
    }

    function renderSelectedFeatureCard(page) {
      if (!state.selectedFeature) return "";
      const sel = state.selectedFeature;

      if (sel.type === "vector") {
        const ft = sel.data;
        const srcPageId = `maps8-${String(ft.page).padStart(3, "0")}`;
        const srcPage = pageById.get(srcPageId) || page;
        const scaleX = srcPage.width / (srcPage.pdfWidthPt || 595);
        const scaleY = srcPage.height / (srcPage.pdfHeightPt || 842);
        const [bx0, by0, bx1, by1] = ft.bbox || [200, 200, 280, 230];
        const cropHtml = buildSourceCropHtml({
          pageAsset: srcPage.pageAsset,
          imgW: srcPage.width,
          imgH: srcPage.height,
          cropRect: [bx0 * scaleX, by0 * scaleY, (bx1 - bx0) * scaleX, (by1 - by0) * scaleY],
        });

        const confMap = { high: "عالية", medium: "متوسطة", low: "منخفضة (تحتاج مراجعة)" };
        const confCls = ft.conf === "high" ? "badge-verified" : ft.conf === "medium" ? "badge-warn" : "badge-low";

        // Cross-atlas occurrences from unified gazetteer
        const nk = normAr(ft.text);
        const gaz = manifest.gazetteer.find((g) => g.norm === nk);
        const related = gaz
          ? gaz.occurrences.filter((o) => !(o.pageId === srcPageId && o.featureId === ft.id)).slice(0, 8)
          : [];

        return `
          <div class="info-section">
            <div class="feature-card">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:6px">
                <h4>${escapeHtml(ft.text)}</h4>
                <button type="button" class="icon-btn-sm" id="close-feat-btn" aria-label="إغلاق البطاقة">✕</button>
              </div>
              <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px">
                <span class="badge ${confCls}">ثقة النسخ: ${confMap[ft.conf] || ft.conf}</span>
                <span class="badge badge-ocr">${escapeHtml(ft.kindLabel || ft.kind)}</span>
              </div>
              ${ft.note ? `<p style="margin:6px 0;font-size:12px;color:var(--gold)">ملاحظة تدقيقية: ${escapeHtml(ft.note)}</p>` : ""}
              ${cropHtml}
              <div style="font-size:12px;color:var(--ink-secondary);display:flex;justify-content:space-between;align-items:center;margin-top:6px">
                <span>المصدر: خرائط التاريخ الإسلامي — ص ${toArabicDigits(ft.page)}</span>
                <button type="button" class="btn" style="padding:3px 8px;font-size:11.5px" data-open-orig="${srcPageId}">تحقق من الأصل</button>
              </div>
              ${
                related.length
                  ? `<div style="margin-top:10px;padding-top:8px;border-top:1px solid var(--border-subtle)">
                       <div style="font-size:11.5px;font-weight:700;margin-bottom:5px">مواضع أخرى في الأطالس الستة (${toArabicDigits(related.length)}):</div>
                       <div style="display:flex;flex-wrap:wrap;gap:5px">
                         ${related
                           .map((r) => {
                             const rv = volById.get(r.volumeId);
                             return `<button type="button" class="btn" style="padding:2px 7px;font-size:11px" data-rel-pid="${r.pageId}" data-rel-fid="${r.featureId || ""}">${escapeHtml(rv ? rv.shortTitle : r.volumeId)} ص ${toArabicDigits(r.sourcePage)}</button>`;
                           })
                           .join("")}
                       </div>
                     </div>`
                  : ""
              }
            </div>
          </div>`;
      }

      if (sel.type === "hotspot") {
        const hs = sel.data;
        const cx = (hs.x / 100) * page.width;
        const cy = (hs.y / 100) * page.height;
        const cw = (hs.w / 100) * page.width;
        const ch = (hs.h / 100) * page.height;
        const cropHtml = buildSourceCropHtml({
          pageAsset: page.pageAsset,
          imgW: page.width,
          imgH: page.height,
          cropRect: [cx, cy, cw, ch],
        });

        return `
          <div class="info-section">
            <div class="feature-card">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:6px">
                <h4>${escapeHtml(hs.name)}</h4>
                <button type="button" class="icon-btn-sm" id="close-feat-btn" aria-label="إغلاق البطاقة">✕</button>
              </div>
              <span class="badge badge-verified" style="margin-bottom:6px">معلم خريطة محقق بصريًا</span>
              <p style="margin:6px 0;font-size:13px;line-height:1.5">${escapeHtml(hs.fact || "")}</p>
              ${cropHtml}
              <div style="font-size:12px;color:var(--ink-secondary);display:flex;justify-content:space-between;align-items:center;margin-top:6px">
                <span>المصدر: ص ${toArabicDigits(page.sourcePage)}</span>
                <button type="button" class="btn" style="padding:3px 8px;font-size:11.5px" data-open-orig="${page.id}">افتح الصفحة الأصلية</button>
              </div>
            </div>
          </div>`;
      }

      if (sel.type === "ocr") {
        const d = sel.data;
        const [x0, y0, x1, y1] = d.bbox;
        const cropHtml = buildSourceCropHtml({
          pageAsset: page.pageAsset,
          imgW: page.width,
          imgH: page.height,
          cropRect: [x0, y0, x1 - x0, y1 - y0],
        });
        return `
          <div class="info-section">
            <div class="feature-card">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:6px">
                <h4>«${escapeHtml(d.word)}»</h4>
                <button type="button" class="icon-btn-sm" id="close-feat-btn" aria-label="إغلاق">✕</button>
              </div>
              <span class="badge badge-ocr">قراءة استخراج ضوئي آلي (OCR: ${toArabicDigits(d.conf)}%)</span>
              <p style="font-size:12px;color:var(--ink-secondary);margin:6px 0">تحقق من الرسم المطبوع أدناه — لا تُعتمد قراءات OCR وحدها دون مطابقة بصرية:</p>
              ${cropHtml}
            </div>
          </div>`;
      }
      return "";
    }

    function renderExplorerInfo() {
      const page = pageById.get(state.currentPageId);
      if (!page) return;
      const vol = volById.get(page.volumeId);
      const vBadge = VERIFICATION_LABELS[page.verificationStatus] || {
        text: page.verificationStatus,
        cls: "badge-ocr",
      };

      // Build layers / overlays section honestly based on volume type
      let layersHtml = "";
      if (page.volumeId === "maps8") {
        const maps8Vol = volById.get("maps8");
        const fig = maps8Vol.figures.find((f) => f.id === page.figureId) || maps8Vol.figures[0];
        const layerEntries = Object.entries(maps8Vol.layerNames).filter(([k]) => (fig.layers[k] || 0) > 0);
        layersHtml = `
          <div class="info-section">
            <h3>الطبقات المتجهية الحقيقية (مفصولة من PDF)</h3>
            <div class="layer-toggles">
              ${layerEntries
                .map(([key, label]) => {
                  const checked = !state.hiddenVectorLayers.has(key);
                  return `
                    <div class="layer-row">
                      <label>
                        <input type="checkbox" data-vec-layer="${key}" ${checked ? "checked" : ""} />
                        <span>${escapeHtml(label)}</span>
                      </label>
                      <span style="font-size:11px;color:var(--ink-muted)">${toArabicDigits(fig.layers[key])} عنصر</span>
                    </div>`;
                })
                .join("")}
            </div>
          </div>`;
      } else {
        layersHtml = `
          <div class="info-section">
            <h3>طبقات العرض والإفصاح الكارتوغرافي</h3>
            <p style="margin:0 0 8px 0;font-size:11.5px;color:var(--ink-muted)">
              المصدر الأصلي لهذا المجلد ممسوح ضوئيًا كصورة نقطية مدمجة (لا يحتوي طبقات متجهية قابلة للفصل). تُوفّر المنصة طبقات تفاعلية فوق الصورة الأصلية:
            </p>
            <div class="layer-toggles">
              <div class="layer-row">
                <label>
                  <input type="checkbox" id="chk-info-hotspots" ${state.showHotspots ? "checked" : ""} />
                  <span>المعالم المحققة القابلة للنقر (${toArabicDigits((page.hotspots || []).length)})</span>
                </label>
              </div>
              <div class="layer-row">
                <label>
                  <input type="checkbox" id="chk-info-ocr" ${state.showOcrLayer ? "checked" : ""} />
                  <span>طبقة كلمات الاستخراج الضوئي OCR (${toArabicDigits(page.ocrWordCount || 0)})</span>
                </label>
              </div>
            </div>
          </div>`;
      }

      // Legends section
      const legendsHtml =
        page.legends && page.legends.length
          ? `<div class="info-section">
               <h3>مفتاح الخريطة ودلالات الألوان والرموز</h3>
               <ul class="legend-list">
                 ${page.legends
                   .map(
                     (lg) => `
                   <li class="legend-item">
                     <span class="legend-swatch" style="background:${escapeHtml(lg.color || "#888")}"></span>
                     <span>${escapeHtml(lg.label || lg.text || "")}</span>
                   </li>`
                   )
                   .join("")}
               </ul>
             </div>`
          : "";

      // Quick clickable hotspot chips for scanned maps with verified hotspots
      const hotspotsListHtml =
        page.hotspots && page.hotspots.length
          ? `<div class="info-section">
               <h3>معالم الخريطة الموثقة (${toArabicDigits(page.hotspots.length)})</h3>
               <div style="display:flex;flex-wrap:wrap;gap:5px">
                 ${page.hotspots
                   .map(
                     (hs, idx) => `
                   <button type="button" class="btn" style="padding:3px 8px;font-size:11.5px" data-chip-hs="${hs.id}">
                     ${toArabicDigits(idx + 1)}. ${escapeHtml(hs.name)}
                   </button>`
                   )
                   .join("")}
               </div>
             </div>`
          : "";

      // Printed index references on this page
      const idxHtml =
        page.indexEntries && page.indexEntries.length
          ? `<div class="info-section">
               <h3>التوثيق في فهارس الكتاب المطبوعة</h3>
               <ul style="margin:0;padding-inline-start:18px;font-size:12px;color:var(--ink-secondary)">
                 ${page.indexEntries
                   .map(
                     (e) =>
                       `<li><strong>${escapeHtml(e.title)}</strong> (فهرس ص ${toArabicDigits(e.indexPage)})</li>`
                   )
                   .join("")}
               </ul>
             </div>`
          : "";

      // Extracted Text / OCR inspection
      const isCleanText = page.volumeId === "maps8" || (page.ocrConfidence !== null && page.ocrConfidence >= 65);
      const textSectionHtml = page.extractedText
        ? `<div class="info-section">
             <h3>
               <span>${page.volumeId === "maps8" ? "التسميات المتجهية المنسوخة في الصفحة" : "النص المستخرج ضوئيًا (OCR)"}</span>
               ${
                 page.ocrConfidence !== null
                   ? `<span class="badge ${page.verificationStatus === "ocr-needs-review" ? "badge-warn" : "badge-ocr"}">ثقة ${toArabicDigits(page.ocrConfidence)}%</span>`
                   : ""
               }
             </h3>
             ${
               page.volumeId !== "maps8"
                 ? `<p style="margin:0 0 6px 0;font-size:11px;color:var(--ink-muted)">مُستخرج آليًا لأغراض البحث؛ اعتمد دائمًا على الصورة الأصلية عند التحقيق العلمي.</p>`
                 : ""
             }
             ${
               isCleanText
                 ? `<div class="ocr-box-text">${escapeHtml(page.extractedText)}</div>`
                 : `<details style="margin-top:4px">
                      <summary style="cursor:pointer;font-size:12px;font-weight:700;color:var(--accent)">عرض النص الخام المستخرج ضوئيًا</summary>
                      <div class="ocr-box-text" style="margin-top:6px">${escapeHtml(page.extractedText)}</div>
                    </details>`
             }
           </div>`
        : "";

      elInfoContent.innerHTML = `
        ${renderSelectedFeatureCard(page)}
        <div class="info-section">
          <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">
            <span class="badge ${vBadge.cls}">${escapeHtml(vBadge.text)}</span>
            <span class="badge badge-ocr">${escapeHtml(CATEGORY_LABELS[page.category] || page.category)}</span>
          </div>
          <h2 class="page-main-title">${escapeHtml(page.title)}</h2>
          <p class="page-desc">${escapeHtml(page.description || "")}</p>
          ${
            page.scaleText
              ? `<div style="margin-top:6px;font-size:12px;color:var(--ink-secondary)"><strong>مقياس الرسم في المصدر:</strong> <bdi>${escapeHtml(page.scaleText)}</bdi></div>`
              : ""
          }
          ${
            page.notes && page.notes.length
              ? `<div style="margin-top:8px;padding:7px 10px;border-radius:6px;background:var(--gold-soft);font-size:12px">${page.notes.map(escapeHtml).join(" · ")}</div>`
              : ""
          }
          <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px">
            <button type="button" class="btn btn-primary" style="flex:1;justify-content:center" id="info-open-orig">
              معاينة الصفحة الأصلية ومطابقتها
            </button>
          </div>
        </div>
        ${legendsHtml}
        ${hotspotsListHtml}
        ${layersHtml}
        ${idxHtml}
        ${textSectionHtml}
      `;

      // Bind info panel interactions
      const closeFeat = elInfoContent.querySelector("#close-feat-btn");
      if (closeFeat) {
        closeFeat.addEventListener("click", () => {
          state.selectedFeature = null;
          renderExplorerInfo();
        });
      }

      const openOrigBtn = elInfoContent.querySelector("#info-open-orig");
      if (openOrigBtn) {
        openOrigBtn.addEventListener("click", () => {
          state.origSplitVerify = true;
          switchTab("original");
        });
      }

      elInfoContent.querySelectorAll("[data-open-orig]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const pid = btn.getAttribute("data-open-orig");
          state.currentPageId = pid;
          state.origSplitVerify = true;
          switchTab("original");
        });
      });

      elInfoContent.querySelectorAll("[data-rel-pid]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const pid = btn.getAttribute("data-rel-pid");
          const fid = btn.getAttribute("data-rel-fid");
          openPageInExplorer(pid, { focusFeatureId: fid || undefined });
        });
      });

      elInfoContent.querySelectorAll("[data-chip-hs]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const hsid = btn.getAttribute("data-chip-hs");
          const hs = (page.hotspots || []).find((x) => x.id === hsid);
          if (hs) {
            state.selectedFeature = { type: "hotspot", data: hs };
            if (activeViewerHandle && activeViewerHandle.focusHotspot) {
              activeViewerHandle.focusHotspot(hsid);
            }
            renderExplorerInfo();
          }
        });
      });

      elInfoContent.querySelectorAll("[data-vec-layer]").forEach((chk) => {
        chk.addEventListener("change", () => {
          const key = chk.getAttribute("data-vec-layer");
          if (chk.checked) state.hiddenVectorLayers.delete(key);
          else state.hiddenVectorLayers.add(key);
          const svg = elWorld.querySelector("svg.vector-spread-svg");
          if (svg) svg.classList.toggle(`hide-${key}`, !chk.checked);
        });
      });

      const chkHs = elInfoContent.querySelector("#chk-info-hotspots");
      if (chkHs) {
        chkHs.addEventListener("change", () => {
          state.showHotspots = chkHs.checked;
          renderExplorerCanvas();
        });
      }
      const chkOcr = elInfoContent.querySelector("#chk-info-ocr");
      if (chkOcr) {
        chkOcr.addEventListener("change", () => {
          state.showOcrLayer = chkOcr.checked;
          renderExplorerCanvas();
        });
      }
    }

    function renderExplorerAll(opts = {}) {
      renderNavigatorSidebar();
      renderFilmstrip();
      renderExplorerCanvas(opts);
      renderExplorerInfo();
    }

    function stepPage(delta) {
      const vPages = manifest.pages.filter((p) => p.volumeId === state.activeVolumeId);
      const idx = vPages.findIndex((p) => p.id === state.currentPageId);
      if (idx < 0) return;
      // In maps8 explorer, step by spread (2 pages) unless in original page viewer
      const step = state.activeVolumeId === "maps8" && state.activeTab === "explore" ? delta * 2 : delta;
      const nextIdx = Math.min(vPages.length - 1, Math.max(0, idx + step));
      if (nextIdx !== idx) {
        openPageInExplorer(vPages[nextIdx].id, { targetTab: state.activeTab });
      }
    }

    // ==================== Module D: Dynamic Table of Contents ====================
    function renderTocView() {
      const container = document.getElementById("view-toc");
      const qNorm = normAr(state.tocQuery);

      let pages = manifest.pages;
      if (state.tocSubset === "bookmarks") {
        pages = pages.filter((p) => state.bookmarks.includes(p.id));
      } else if (state.tocSubset === "recent") {
        pages = state.recentPages.map((id) => pageById.get(id)).filter(Boolean);
      }
      if (state.tocVol !== "all") {
        pages = pages.filter((p) => p.volumeId === state.tocVol);
      }
      if (state.tocCat !== "all") {
        pages = pages.filter((p) => p.category === state.tocCat);
      }
      if (qNorm) {
        pages = pages.filter(
          (p) =>
            p.titleNorm.includes(qNorm) ||
            normAr(p.sectionTitle).includes(qNorm) ||
            String(p.sourcePage).includes(qNorm)
        );
      }

      // Verified chapters summary for selected volume
      const activeVolObj = state.tocVol !== "all" ? volById.get(state.tocVol) : null;
      const chaptersBar = activeVolObj
        ? `<div style="margin-bottom:16px;padding:12px 14px;background:var(--bg-surface);border:1px solid var(--border-subtle);border-radius:10px">
             <div style="font-weight:700;font-size:13.5px;margin-bottom:8px">الأبواب والفصول الأصلية في «${escapeHtml(activeVolObj.title)}»:</div>
             <div style="display:flex;flex-wrap:wrap;gap:6px">
               ${activeVolObj.sections
                 .map(
                   (s) =>
                     `<button type="button" class="btn" data-sec-jump="${activeVolObj.id}-${String(s.startPage).padStart(3, "0")}" style="font-size:12px">
                        ${escapeHtml(s.title)} (ص ${toArabicDigits(s.startPage)})
                      </button>`
                 )
                 .join("")}
             </div>
           </div>`
        : "";

      container.innerHTML = `
        <div class="content-container">
          <div class="section-header-bar">
            <div>
              <h2 style="margin:0;font-size:18px">الفهرس العام للأطالس الستة (${toArabicDigits(pages.length)} صفحة معروضة من أصل ${toArabicDigits(manifest.pages.length)})</h2>
              <p style="margin:4px 0 0 0;font-size:12.5px;color:var(--ink-secondary)">
                مُستخرج مباشرة من الفهارس المطبوعة والإشارات المرجعية الأصلية دون اختلاق أقسام إضافية.
              </p>
            </div>
            <div style="display:flex;gap:6px;flex-wrap:wrap">
              <button type="button" class="btn ${state.tocSubset === "all" ? "is-on" : ""}" data-sub="all">كل الصفحات (${toArabicDigits(manifest.pages.length)})</button>
              <button type="button" class="btn ${state.tocSubset === "bookmarks" ? "is-on" : ""}" data-sub="bookmarks">المحفوظات ★ (${toArabicDigits(state.bookmarks.length)})</button>
              <button type="button" class="btn ${state.tocSubset === "recent" ? "is-on" : ""}" data-sub="recent">شوهد مؤخرًا (${toArabicDigits(state.recentPages.length)})</button>
              <button type="button" class="btn ${state.tocListMode === "gallery" ? "btn-primary" : ""}" data-mode="gallery">معرض مصور</button>
              <button type="button" class="btn ${state.tocListMode === "compact" ? "btn-primary" : ""}" data-mode="compact">قائمة مدمجة</button>
            </div>
          </div>

          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">
            <select id="toc-vol-sel" style="padding:7px 10px;border-radius:8px;border:1px solid var(--border-subtle);background:var(--bg-surface)">
              <option value="all" ${state.tocVol === "all" ? "selected" : ""}>جميع الأطالس الستة</option>
              ${manifest.volumes
                .map(
                  (v) =>
                    `<option value="${v.id}" ${state.tocVol === v.id ? "selected" : ""}>${escapeHtml(v.title)}</option>`
                )
                .join("")}
            </select>
            <select id="toc-cat-sel" style="padding:7px 10px;border-radius:8px;border:1px solid var(--border-subtle);background:var(--bg-surface)">
              <option value="all" ${state.tocCat === "all" ? "selected" : ""}>جميع التصنيفات</option>
              ${Object.entries(CATEGORY_LABELS)
                .map(
                  ([k, lbl]) =>
                    `<option value="${k}" ${state.tocCat === k ? "selected" : ""}>${escapeHtml(lbl)}</option>`
                )
                .join("")}
            </select>
            <input type="search" id="toc-filter-inp" value="${escapeHtml(state.tocQuery)}" placeholder="صفِّ الفهرس بالعنوان أو الباب أو رقم الصفحة…" style="flex:1;min-width:220px;padding:7px 12px;border-radius:8px;border:1px solid var(--border-subtle);background:var(--bg-surface)" />
          </div>

          ${chaptersBar}

          ${
            !pages.length
              ? `<div class="quiz-card" style="text-align:center;padding:40px">لا توجد صفحات مطابقة لمعايير التصفية الحالية.</div>`
              : state.tocListMode === "gallery"
              ? `<div class="toc-grid">
                   ${pages
                     .map((p) => {
                       const vol = volById.get(p.volumeId);
                       const vb = VERIFICATION_LABELS[p.verificationStatus] || { text: "", cls: "badge-ocr" };
                       return `
                         <article class="toc-card" data-open-pid="${p.id}" tabindex="0" role="button">
                           <img class="toc-card-img" src="${resolveAsset(p.thumbAsset)}" alt="${escapeHtml(p.title)}" loading="lazy" />
                           <div class="toc-card-body">
                             <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--ink-muted)">
                               <span>${escapeHtml(vol.shortTitle)} · ص ${toArabicDigits(p.sourcePage)}</span>
                               <span>${escapeHtml(CATEGORY_LABELS[p.category] || "")}</span>
                             </div>
                             <div class="toc-card-title">${escapeHtml(p.title)}</div>
                             <div style="margin-top:auto;padding-top:6px">
                               <span class="badge ${vb.cls}" style="font-size:10px">${escapeHtml(vb.text)}</span>
                             </div>
                           </div>
                         </article>`;
                     })
                     .join("")}
                 </div>`
              : `<table class="toc-compact-table">
                   <thead>
                     <tr>
                       <th>الأطلس</th>
                       <th>ص</th>
                       <th>العنوان</th>
                       <th>الباب / القسم</th>
                       <th>الفئة</th>
                       <th>حالة التحقق</th>
                     </tr>
                   </thead>
                   <tbody>
                     ${pages
                       .map((p) => {
                         const vol = volById.get(p.volumeId);
                         const vb = VERIFICATION_LABELS[p.verificationStatus] || { text: "", cls: "badge-ocr" };
                         return `
                           <tr data-open-pid="${p.id}">
                             <td>${escapeHtml(vol.shortTitle)}</td>
                             <td><strong>${toArabicDigits(p.sourcePage)}</strong></td>
                             <td><strong>${escapeHtml(p.title)}</strong></td>
                             <td>${escapeHtml(p.sectionTitle)}</td>
                             <td>${escapeHtml(CATEGORY_LABELS[p.category] || "")}</td>
                             <td><span class="badge ${vb.cls}">${escapeHtml(vb.text)}</span></td>
                           </tr>`;
                       })
                       .join("")}
                   </tbody>
                 </table>`
          }
        </div>
      `;

      container.querySelectorAll("[data-sub]").forEach((b) =>
        b.addEventListener("click", () => {
          state.tocSubset = b.getAttribute("data-sub");
          renderTocView();
        })
      );
      container.querySelectorAll("[data-mode]").forEach((b) =>
        b.addEventListener("click", () => {
          state.tocListMode = b.getAttribute("data-mode");
          renderTocView();
        })
      );
      container.querySelector("#toc-vol-sel").addEventListener("change", (e) => {
        state.tocVol = e.target.value;
        renderTocView();
      });
      container.querySelector("#toc-cat-sel").addEventListener("change", (e) => {
        state.tocCat = e.target.value;
        renderTocView();
      });
      container.querySelector("#toc-filter-inp").addEventListener(
        "input",
        debounce((e) => {
          state.tocQuery = e.target.value;
          renderTocView();
        }, 180)
      );
      container.querySelectorAll("[data-sec-jump]").forEach((b) =>
        b.addEventListener("click", () => openPageInExplorer(b.getAttribute("data-sec-jump")))
      );
      container.querySelectorAll("[data-open-pid]").forEach((el) => {
        el.addEventListener("click", () => openPageInExplorer(el.getAttribute("data-open-pid")));
        el.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            openPageInExplorer(el.getAttribute("data-open-pid"));
          }
        });
      });
    }

    // ==================== Module E: Original Source Page Viewer ====================
    async function renderOriginalView() {
      const container = document.getElementById("view-original");
      const page = pageById.get(state.currentPageId);
      if (!page) return;
      const vol = volById.get(page.volumeId);
      const srcMeta = manifest.sources.find((s) => s.volumeId === page.volumeId);
      const vPages = manifest.pages.filter((p) => p.volumeId === page.volumeId);

      container.innerHTML = `
        <div class="dual-stage">
          <div class="dual-controls">
            <div class="toolbar-group">
              <button type="button" class="btn" id="orig-prev">→ الصفحة السابقة</button>
              <select id="orig-page-sel" aria-label="اختر صفحة من المصدر" style="padding:5px 10px;border-radius:6px;border:1px solid var(--border-subtle);background:var(--bg-elevated);max-width:360px">
                ${vPages
                  .map(
                    (p) =>
                      `<option value="${p.id}" ${p.id === page.id ? "selected" : ""}>ص ${toArabicDigits(p.sourcePage)} — ${escapeHtml(p.title)}</option>`
                  )
                  .join("")}
              </select>
              <button type="button" class="btn" id="orig-next">الصفحة التالية ←</button>
            </div>
            <div class="toolbar-group">
              <button type="button" class="btn" id="orig-zoom-in" title="تكبير">+</button>
              <button type="button" class="btn" id="orig-zoom-out" title="تصغير">−</button>
              <button type="button" class="btn" id="orig-fit">ملاءمة</button>
              <button type="button" class="btn" id="orig-rot">تدوير 90° ↻</button>
              <button type="button" class="btn ${state.origSplitVerify ? "is-on" : ""}" id="orig-split-toggle">
                مقارنة جنبًا إلى جنب مع العرض التفاعلي
              </button>
              <button type="button" class="btn btn-primary" id="orig-back-exp">فتح في المستكشف</button>
            </div>
          </div>

          <div style="padding:5px 16px;background:var(--bg-muted);border-block-end:1px solid var(--border-subtle);font-size:11.5px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px">
            <span><strong>مسار التحقق المصدري الأصلي:</strong> الملف <code>${escapeHtml(srcMeta ? srcMeta.fileName : "")}</code> · الصفحة ${toArabicDigits(page.sourcePage)} من ${toArabicDigits(vol.pageCount)} · الأبعاد الأصلية: <bdi>${page.width}×${page.height} px</bdi></span>
            <span>بصمة SHA-256: <code class="ltr">${srcMeta ? srcMeta.sha256.slice(0, 20) + "…" : ""}</code></span>
          </div>

          <div class="dual-panes" style="grid-template-columns:${state.origSplitVerify ? "1fr 1fr" : "1fr"}">
            <div class="dual-pane">
              <div class="dual-pane-head">
                <span>الصورة الأصلية المستخرجة من PDF دون تعديل (ص ${toArabicDigits(page.sourcePage)})</span>
                <span class="badge badge-verified">مرجع التحقق الأساسي</span>
              </div>
              <div class="map-viewport" id="orig-vp-raw">
                <div class="panzoom-world" id="orig-world-raw"></div>
              </div>
            </div>
            ${
              state.origSplitVerify
                ? `<div class="dual-pane">
                     <div class="dual-pane-head">
                       <span>التمثيل التفاعلي للمطابقة البصرية</span>
                       <span class="badge badge-ocr">${page.volumeId === "maps8" ? "رسم متجهي + مناطق تفاعل" : "معالم محققة + طبقة OCR"}</span>
                     </div>
                     <div class="map-viewport" id="orig-vp-inter">
                       <div class="panzoom-world" id="orig-world-inter"></div>
                     </div>
                   </div>`
                : ""
            }
          </div>
        </div>
      `;

      const vpRaw = container.querySelector("#orig-vp-raw");
      const wRaw = container.querySelector("#orig-world-raw");
      let syncingOrig = false;

      origPzMain = new PanZoomController(vpRaw, wRaw, {
        onChange: (st) => {
          if (!state.origSplitVerify || syncingOrig || !origPzInteractive || page.volumeId === "maps8") return;
          syncingOrig = true;
          origPzInteractive.setState(st, true);
          syncingOrig = false;
        },
      });

      // Render untouched original page image (no overlays!)
      renderScannedPage({
        worldEl: wRaw,
        panzoom: origPzMain,
        page,
        ocrWords: [],
        showHotspots: false,
        showOcrLayer: false,
        initialRotation: 0,
      });

      if (state.origSplitVerify) {
        const vpInter = container.querySelector("#orig-vp-inter");
        const wInter = container.querySelector("#orig-world-inter");
        origPzInteractive = new PanZoomController(vpInter, wInter, {
          onChange: (st) => {
            if (syncingOrig || page.volumeId === "maps8") return;
            syncingOrig = true;
            origPzMain.setState(st, true);
            syncingOrig = false;
          },
        });

        if (page.volumeId === "maps8") {
          const maps8Vol = volById.get("maps8");
          const fig = maps8Vol.figures.find((f) => f.id === page.figureId) || maps8Vol.figures[0];
          await renderMaps8Spread({
            worldEl: wInter,
            panzoom: origPzInteractive,
            maps8Vol,
            figure: fig,
            hiddenLayers: [],
            showHotspots: true,
          });
        } else {
          renderScannedPage({
            worldEl: wInter,
            panzoom: origPzInteractive,
            page,
            ocrWords: ocrWordsMap[page.id] || [],
            showHotspots: true,
            showOcrLayer: true,
            initialRotation: 0,
          });
        }
      }

      // Controls
      container.querySelector("#orig-prev").addEventListener("click", () => {
        const idx = vPages.findIndex((p) => p.id === page.id);
        if (idx > 0) {
          state.currentPageId = vPages[idx - 1].id;
          syncHeaderUi();
          renderOriginalView();
        }
      });
      container.querySelector("#orig-next").addEventListener("click", () => {
        const idx = vPages.findIndex((p) => p.id === page.id);
        if (idx >= 0 && idx < vPages.length - 1) {
          state.currentPageId = vPages[idx + 1].id;
          syncHeaderUi();
          renderOriginalView();
        }
      });
      container.querySelector("#orig-page-sel").addEventListener("change", (e) => {
        state.currentPageId = e.target.value;
        syncHeaderUi();
        renderOriginalView();
      });
      container.querySelector("#orig-zoom-in").addEventListener("click", () => origPzMain.zoomAt(1.25));
      container.querySelector("#orig-zoom-out").addEventListener("click", () => origPzMain.zoomAt(1 / 1.25));
      container.querySelector("#orig-fit").addEventListener("click", () => {
        origPzMain.fit();
        if (origPzInteractive) origPzInteractive.fit();
      });
      container.querySelector("#orig-rot").addEventListener("click", () => {
        origPzMain.rotateBy(90);
        if (origPzInteractive && page.volumeId !== "maps8") origPzInteractive.rotateBy(90);
      });
      container.querySelector("#orig-split-toggle").addEventListener("click", () => {
        state.origSplitVerify = !state.origSplitVerify;
        renderOriginalView();
      });
      container.querySelector("#orig-back-exp").addEventListener("click", () => openPageInExplorer(page.id));
    }

    // ==================== Module C: Searchable Geographic Gazetteer ====================
    function renderGazetteerView() {
      const container = document.getElementById("view-gazetteer");
      const letters = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي".split("");
      const qNorm = normAr(state.gazQuery);

      const filtered = manifest.gazetteer.filter((g) => {
        if (state.gazCrossOnly && g.volumeCount < 2) return false;
        if (state.gazVol !== "all" && !g.occurrences.some((o) => o.volumeId === state.gazVol)) return false;
        if (state.gazLetter !== "all") {
          const stripped = g.norm.replace(/^ال/, "");
          if (!stripped.startsWith(normAr(state.gazLetter))) return false;
        }
        if (qNorm && !g.norm.includes(qNorm)) return false;
        return true;
      });

      container.innerHTML = `
        <div class="content-container">
          <div class="section-header-bar">
            <div>
              <h2 style="margin:0;font-size:18px">الموسوعة والفهرس الجغرافي الموحّد (${toArabicDigits(filtered.length)} مدخل موثق)</h2>
              <p style="margin:4px 0 0 0;font-size:12.5px;color:var(--ink-secondary)">
                مرتب أبجديًا مع تجاهل «الـ» التعريف، ويوفر وصولًا نصيًا كاملًا لجميع المواقع والخرائط دون اشتراط التفاعل البصري مع الخريطة.
              </p>
            </div>
            <label style="font-size:13px;display:inline-flex;align-items:center;gap:6px;cursor:pointer">
              <input type="checkbox" id="gaz-cross-chk" ${state.gazCrossOnly ? "checked" : ""} />
              إظهار الأسماء المشتركة بين أكثر من أطلس فقط
            </label>
          </div>

          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
            <select id="gaz-vol-sel" style="padding:7px 10px;border-radius:8px;border:1px solid var(--border-subtle);background:var(--bg-surface)">
              <option value="all" ${state.gazVol === "all" ? "selected" : ""}>جميع الأطالس الستة</option>
              ${manifest.volumes
                .map(
                  (v) =>
                    `<option value="${v.id}" ${state.gazVol === v.id ? "selected" : ""}>${escapeHtml(v.shortTitle)}</option>`
                )
                .join("")}
            </select>
            <input type="search" id="gaz-search-inp" value="${escapeHtml(state.gazQuery)}" placeholder="ابحث في المدخلات الجغرافية والتاريخية…" style="flex:1;min-width:220px;padding:7px 12px;border-radius:8px;border:1px solid var(--border-subtle);background:var(--bg-surface)" />
          </div>

          <div class="alpha-bar" role="toolbar" aria-label="الحروف الأبجدية">
            <button type="button" class="alpha-btn ${state.gazLetter === "all" ? "is-active" : ""}" data-let="all">الكل</button>
            ${letters
              .map(
                (ch) =>
                  `<button type="button" class="alpha-btn ${state.gazLetter === ch ? "is-active" : ""}" data-let="${ch}">${ch}</button>`
              )
              .join("")}
          </div>

          <div class="gaz-grid">
            ${filtered
              .slice(0, 240)
              .map(
                (g) => `
              <div class="gaz-card">
                <h4>
                  <span>${escapeHtml(g.name)}</span>
                  <span class="badge ${g.volumeCount > 1 ? "badge-verified" : "badge-ocr"}">
                    ${toArabicDigits(g.occurrences.length)} موضع
                  </span>
                </h4>
                ${
                  g.variants.length > 1
                    ? `<div style="font-size:11.5px;color:var(--ink-muted)">صيغ واردة: ${escapeHtml(g.variants.join(" ، "))}</div>`
                    : ""
                }
                <div class="gaz-occ-list">
                  ${g.occurrences
                    .map((occ) => {
                      const vol = volById.get(occ.volumeId);
                      return `<button type="button" class="btn" style="padding:3px 8px;font-size:11.5px"
                                data-gaz-pid="${occ.pageId}"
                                data-gaz-fid="${occ.source === "maps8-vector-label" ? occ.featureId || "" : ""}"
                                data-gaz-hid="${occ.source === "verified-hotspot" ? occ.featureId || "" : ""}">
                                ${escapeHtml(vol ? vol.shortTitle : occ.volumeId)} · ص ${toArabicDigits(occ.sourcePage)}
                              </button>`;
                    })
                    .join("")}
                </div>
              </div>`
              )
              .join("")}
          </div>
          ${
            filtered.length > 240
              ? `<p style="text-align:center;color:var(--ink-muted);margin-top:16px">يُعرض أول ٢٤٠ مدخلًا؛ استخدم شريط الحروف أو البحث أعلاه لتضييق النتيجة.</p>`
              : ""
          }
        </div>
      `;

      container.querySelector("#gaz-cross-chk").addEventListener("change", (e) => {
        state.gazCrossOnly = e.target.checked;
        renderGazetteerView();
      });
      container.querySelector("#gaz-vol-sel").addEventListener("change", (e) => {
        state.gazVol = e.target.value;
        renderGazetteerView();
      });
      container.querySelector("#gaz-search-inp").addEventListener(
        "input",
        debounce((e) => {
          state.gazQuery = e.target.value;
          renderGazetteerView();
        }, 160)
      );
      container.querySelectorAll("[data-let]").forEach((b) =>
        b.addEventListener("click", () => {
          state.gazLetter = b.getAttribute("data-let");
          renderGazetteerView();
        })
      );
      container.querySelectorAll("[data-gaz-pid]").forEach((b) =>
        b.addEventListener("click", () => {
          const pid = b.getAttribute("data-gaz-pid");
          const fid = b.getAttribute("data-gaz-fid");
          const hid = b.getAttribute("data-gaz-hid");
          openPageInExplorer(pid, {
            focusFeatureId: fid || undefined,
            focusHotspotId: hid || undefined,
          });
        })
      );
    }

    // ==================== Audit, Limitations & Settings View ====================
    function renderAuditView() {
      const container = document.getElementById("view-audit");
      const st = manifest.stats;

      container.innerHTML = `
        <div class="content-container">
          <div class="section-header-bar">
            <div>
              <h2 style="margin:0;font-size:18px">تقرير التدقيق المصدري والمنهجية والإعدادات</h2>
              <p style="margin:4px 0 0 0;font-size:12.5px;color:var(--ink-secondary)">
                جميع الأرقام أدناه مقيسة فعليًا من الملفات المصدرية الستة بعد فحص جنائي شامل لـ ${toArabicDigits(st.totalPdfPages)} صفحة.
              </p>
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <label class="btn ${state.referenceOnly ? "is-on" : ""}" style="cursor:pointer">
                <input type="checkbox" id="audit-refonly-chk" ${state.referenceOnly ? "checked" : ""} />
                وضع المرجع العلمي فقط (إيقاف التعلّم والتلعيب)
              </label>
              <button type="button" class="btn" id="audit-clear-storage">مسح البيانات المحلية المحفوظة</button>
            </div>
          </div>

          <div class="stat-cards">
            <div class="stat-card">
              <div class="stat-num">${toArabicDigits(st.totalPdfPages)}</div>
              <div class="stat-label">إجمالي صفحات PDF المعالجة (٠ صفحات محذوفة)</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">${toArabicDigits(st.mapsIdentified.totalDistinctMaps)}</div>
              <div class="stat-label">خريطة تاريخية وجغرافية موثقة في الأطالس الستة</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">${toArabicDigits(st.interactiveFeatures.totalVerifiedHotspots)}</div>
              <div class="stat-label">معلم وتسمية خريطة محققة قابلة للنقر المباشر</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">${toArabicDigits(st.searchableGazetteerEntries)}</div>
              <div class="stat-label">مدخل موسوعي مفهرس وقابل للبحث العربي المطبّع</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">${toArabicDigits(st.totalOcrWordBoxes)}</div>
              <div class="stat-label">مربع كلمة مستخرجة ضوئيًا (OCR) مرتبط بإحداثياته</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">${toArabicDigits(st.indexedTablesAndDiagrams + st.indexedPhotographs + (st.indexedBiographies || 0))}</div>
              <div class="stat-label">جدول ومشجّر وترجمة وصورة فوتوغرافية مفهرسة</div>
            </div>
          </div>

          <div class="quiz-card" style="margin-bottom:16px">
            <h3 style="margin-top:0">١. المصادر الستة وبصماتها التشفيرية</h3>
            <table class="toc-compact-table">
              <thead>
                <tr>
                  <th>المجلد</th>
                  <th>الملف الأصلي</th>
                  <th>عدد الصفحات</th>
                  <th>طبيعة البيانات في PDF</th>
                  <th>SHA-256</th>
                </tr>
              </thead>
              <tbody>
                ${manifest.sources
                  .map((s) => {
                    const nature =
                      s.volumeId === "maps8"
                        ? "رسومات متجهية كاملة بلا طبقة نصية (٤ خرائط مزدوجة عبر ٨ صفحات A4)"
                        : "صفحات ممسوحة ضوئيًا كصور نقطية DCTDecode بلا طبقة نصية + فهارس مطبوعة وإشارات مرجعية";
                    return `
                      <tr>
                        <td><strong>${escapeHtml(volById.get(s.volumeId).title)}</strong></td>
                        <td>${escapeHtml(s.fileName)}</td>
                        <td>${toArabicDigits(s.pageCount)}</td>
                        <td>${nature}</td>
                        <td><code class="ltr" style="font-size:11px">${s.sha256.slice(0, 24)}…</code></td>
                      </tr>`;
                  })
                  .join("")}
              </tbody>
            </table>
          </div>

          <div class="quiz-card" style="margin-bottom:16px">
            <h3 style="margin-top:0">٢. ملاحظات التدقيق الجنائي على الفهارس المطبوعة</h3>
            <ul style="line-height:1.8;font-size:13.5px">
              <li><strong>الأطلس التاريخي لسيرة الرسول ﷺ — فهرس المواضيع (ص ٢٥٥):</strong> طُبع في الفهرس أن الباب السابع يبدأ في ص ١٩٩ والباب الثامن في ص ٢١١، بينما أثبت الفحص البصري المباشر للصفحات أن لوحة الباب السابع تقع فعليًا في <strong>ص ٢١١</strong> ولوحة الباب الثامن في <strong>ص ٢٢٣</strong> (وص ١٩٩ هي خريطة «بعث النبي ﷺ أمراء على الصدقات»). ضُبط التوجيه الفعلي على الصفحات الحقيقية مع توثيق الرقم المطبوع.</li>
              <li><strong>الأطلس التاريخي لسيرة الرسول ﷺ — فهرس الجداول (ص ٢٦٠):</strong> طُبع رقم صفحة «الخريطة التنظيمية للعهد النبوي» سهوًا <code>٢٢٩</code> بين ص ١٢٣ وص ١٣١، وموضعها الفعلي الموثق بصريًا هو <strong>ص ١٢٩</strong>.</li>
              <li><strong>الأطلس التاريخي لسيرة الرسول ﷺ — فهرس الخرائط (ص ٢٥٩):</strong> ورد سطر «غزوات السنة التاسعة من الهجرة» دون رقم صفحة مستقل، وتحققنا بصريًا من وجود الخريطة في <strong>ص ١٩٦</strong>.</li>
              <li><strong>أطلس الخليفة عثمان بن عفان رضي الله عنه — فهرس العناوين والأبواب (ص ٣٠٩):</strong> طُبع رقم بداية «الفصل الثاني: الفتح الإسلامي على الجبهة الشمالية» سهوًا <code>١٣١</code>، بينما تقع لوحة الفصل الثاني فعليًا في <strong>ص ١٢١</strong> (مطابقة للإشارات المرجعية في الملف الأصلي). كما تضمّن الفهرس والفهارس الفرعية هفوات مطبعية يسيرة وُثِّقت مع الحفاظ على الأصل: «الخيفة» بدل «الخليفة» (ص ٣٠٩)، و«جرير بت» بدل «جرير بن» (ص ٣١٠)، و«اليمينة» بدل «اليمنية» (ص ٣٢٢)، وتقدير مسبق في بطاقة الفهرسة (ص ٣) بعدد «٣٧٢ ص» ورقم السلسلة «٢» بينما الكتاب يقع فعليًا في <strong>٣٢٥ صفحة</strong> وهو الحلقة الثالثة من السلسلة.</li>
              <li><strong>أطلس الخليفة علي بن أبي طالب رضي الله عنه — فهرس التراجم والخرائط (ص ٢٦٢، ٢٦٩):</strong> طُبع في فهرس التراجم (ص ٢٦٩) أن ترجمة «فاطمة الزهراء رضي الله عنها» تقع في <code>ص ١٥</code>، بينما تتناول ص ١٥ نسب علي بن أبي طالب وأمّه فاطمة بنت أسد، وتقع ترجمة السيدة فاطمة الزهراء فعليًا في <strong>ص ٣٨</strong> (فوُجِّه الرابط الفعلي إلى ص ٣٨ مع توثيق الرقم المطبوع). كما رُصدت ووُثِّقت الهفوات المطبعية الأصلية دون طمسها: «معوية» بدل «معاوية» و«جرير بت» بدل «جرير بن» (ص ٢٦٩)، و«سن ٣٩ هـ» بدل «سنة ٣٩ هـ» (ص ٢٦٢)، وإغفال إدراج جدول ولاة علي بن أبي طالب الـ ٤١ المطبوع في <strong>ص ١٣٣</strong> ضمن فهرس الأشكال، وورود خطأ مطبعي في البيانات الوصفية الداخلية لملف PDF («الملغوث» بدل «المغلوث»).</li>
              <li><strong>خرائط التاريخ الإسلامي المجمّعة:</strong> يضم الملف الأشكال (٢، ١-١، ١-٣، ١-٤)؛ ولا يتضمن الملف المصدر الأصلي «شكل ١-٢».</li>
            </ul>
          </div>

          <div class="quiz-card">
            <h3 style="margin-top:0">٣. الحدود التقنية المعروفة والإفصاح العلمي الصريح</h3>
            <ul style="line-height:1.8;font-size:13.5px">
              <li><strong>لا حدود GIS مختلقة:</strong> لا تحتوي ملفات PDF المصدرية على إحداثيات مكانية جغرافية (GeoJSON / خطوط طول وعرض رقمية). التفاعل في <em>خرائط التاريخ الإسلامي</em> مبني على <strong>أشكال الحروف المتجهية الأصلية وعلامات المدن</strong>، وفي الأطالس الخمسة الممسوحة ضوئيًا (<em>السيرة</em>، <em>الصديق</em>، <em>الفاروق</em>، <em>ذي النورين</em>، <em>أبي الحسنين</em>) مبني على <strong>إحداثيات الصورة الموثقة بصريًا</strong> للخرائط المحورية ومربعات كلمات OCR، دون ادعاء وجود مضلعات حدودية مستقلة حيث لا يدعمها المصدر.</li>
              <li><strong>دقة الاستخراج الضوئي الآلي (OCR) للخرائط الكثيفة:</strong> نظرًا لأن دقة المسح الأصلية تبلغ نحو ٨٠٠×١٢٠٠ بكسل، فإن النصوص الصغيرة والمائلة داخل الخرائط قد تنتج عنها أخطاء في محرك OCR الآلي (متوسط الثقة ${toArabicDigits(st.meanOcrConfidence)}%). لذلك فُصلت العناوين والفهارس والمعالم المحققة بصريًا فصلًا تامًا عن نصوص OCR الآلية، ووُسمت صفحات OCR منخفضة الثقة (${toArabicDigits(st.lowConfidenceOcrPageIds.length)} صفحة) بوسم «يحتاج مراجعة» مع توفير <strong>عارض الصفحة الأصلية</strong> دائمًا للمطابقة.</li>
              <li><strong>الفرق بين الحزمة الكاملة والنسخة المحمولة (ملف HTML واحد):</strong> تتضمن الحزمة الكاملة (<code>index.html</code> + <code>assets/</code>) جميع صور الصفحات الـ ${toArabicDigits(st.totalPdfPages)} بدقتها الأصلية الكاملة وتعمل دون إنترنت ودون خادم؛ أما ملف <code>release/portable-atlas.html</code> المستقل فيضم جميع الخرائط المتجهية المزدوجة + ٥٦ خريطة وغلافًا محوريًا عالي الدقة + كامل الفهارس والبحث لـ ${toArabicDigits(st.totalPdfPages)} صفحة في ملف واحد لتسهيل المشاركة السريعة.</li>
            </ul>
          </div>
        </div>
      `;

      container.querySelector("#audit-refonly-chk").addEventListener("change", (e) => {
        state.referenceOnly = e.target.checked;
        saveState({ referenceOnly: state.referenceOnly });
        syncHeaderUi();
        renderAuditView();
      });

      container.querySelector("#audit-clear-storage").addEventListener("click", () => {
        clearStoredState();
        state.bookmarks = [];
        state.recentPages = [];
        if (learnCtrl) {
          learnCtrl.progress = { answered: 0, correct: 0 };
          learnCtrl.reviewDeck = [];
        }
        syncHeaderUi();
        renderAuditView();
      });
    }

    // ==================== Global Search Dropdown Wiring ====================
    let activeSearchIdx = -1;
    let currentSearchResults = [];

    function runGlobalSearch() {
      const q = elSearchInput.value.trim();
      elSearchClear.hidden = !q;
      if (!q) {
        elSearchDropdown.hidden = true;
        currentSearchResults = [];
        return;
      }

      currentSearchResults = searchEngine.search(q, {
        volume: elSearchVolFilter.value,
        tier: elSearchTierFilter.value,
        limit: 40,
      });
      activeSearchIdx = currentSearchResults.length ? 0 : -1;
      elSearchDropdown.hidden = false;
      elSearchCount.textContent = `${toArabicDigits(currentSearchResults.length)} نتيجة`;

      if (!currentSearchResults.length) {
        elSearchList.innerHTML = `<li style="padding:20px;text-align:center;color:var(--ink-muted);font-size:13px">لا توجد نتائج مطابقة لـ «${escapeHtml(q)}». جرّب كلمات أعمّ أو غيّر تصفية الأطلس.</li>`;
        return;
      }

      elSearchList.innerHTML = currentSearchResults
        .map((r, idx) => {
          const act = idx === activeSearchIdx ? "is-active" : "";
          const badgeCls = r.sourceTier === "verified" ? "badge-verified" : "badge-ocr";
          return `
            <li class="search-result-item ${act}" data-sridx="${idx}" role="option" aria-selected="${idx === activeSearchIdx}">
              <img class="sr-thumb" src="${resolveAsset(r.thumb)}" alt="" loading="lazy" />
              <div class="sr-body">
                <div class="sr-title">
                  <span>${r.titleHtml}</span>
                  <span class="badge ${badgeCls}" style="font-size:10px">${escapeHtml(r.badge)}</span>
                </div>
                ${r.snippetHtml ? `<div class="sr-snippet">${r.snippetHtml}</div>` : ""}
                <div class="sr-meta">
                  <span>${escapeHtml(r.volumeTitle)}</span>
                  <span>·</span>
                  <strong>ص ${toArabicDigits(r.sourcePage)}</strong>
                </div>
              </div>
            </li>`;
        })
        .join("");

      elSearchList.querySelectorAll("[data-sridx]").forEach((li) => {
        li.addEventListener("click", () => {
          selectSearchResult(Number(li.getAttribute("data-sridx")));
        });
      });
    }

    function selectSearchResult(idx) {
      const r = currentSearchResults[idx];
      if (!r) return;
      elSearchDropdown.hidden = true;

      let selectedFeature = null;
      if (r.type === "feature" && r.featureId) {
        const maps8Vol = volById.get("maps8");
        const ft = (maps8Vol.features || []).find((f) => f.id === r.featureId);
        if (ft) selectedFeature = { type: "vector", data: ft };
      } else if (r.type === "hotspot" && r.hotspotId) {
        const p = pageById.get(r.pageId);
        const hs = (p.hotspots || []).find((h) => h.id === r.hotspotId);
        if (hs) selectedFeature = { type: "hotspot", data: hs };
      }

      openPageInExplorer(r.pageId, {
        selectedFeature,
        focusFeatureId: r.featureId || undefined,
        focusHotspotId: r.hotspotId || undefined,
        highlightQuery: r.type === "page-jump" ? "" : r.rawQuery,
      });
    }

    elSearchInput.addEventListener("input", debounce(runGlobalSearch, 110));
    elSearchInput.addEventListener("focus", () => {
      if (elSearchInput.value.trim()) runGlobalSearch();
    });
    elSearchVolFilter.addEventListener("change", runGlobalSearch);
    elSearchTierFilter.addEventListener("change", runGlobalSearch);
    elSearchClear.addEventListener("click", () => {
      elSearchInput.value = "";
      elSearchClear.hidden = true;
      elSearchDropdown.hidden = true;
      state.highlightQuery = "";
      if (state.activeTab === "explore") renderExplorerCanvas();
      elSearchInput.focus();
    });

    elSearchInput.addEventListener("keydown", (e) => {
      if (elSearchDropdown.hidden || !currentSearchResults.length) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        activeSearchIdx = (activeSearchIdx + 1) % currentSearchResults.length;
        updateActiveSearchDom();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        activeSearchIdx = (activeSearchIdx - 1 + currentSearchResults.length) % currentSearchResults.length;
        updateActiveSearchDom();
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (activeSearchIdx >= 0) selectSearchResult(activeSearchIdx);
      } else if (e.key === "Escape") {
        elSearchDropdown.hidden = true;
      }
    });

    function updateActiveSearchDom() {
      elSearchList.querySelectorAll(".search-result-item").forEach((li, i) => {
        const on = i === activeSearchIdx;
        li.classList.toggle("is-active", on);
        if (on && li.scrollIntoView) li.scrollIntoView({ block: "nearest" });
      });
    }

    document.addEventListener("click", (e) => {
      if (!e.target.closest(".global-search-wrap")) {
        elSearchDropdown.hidden = true;
      }
    });

    // ==================== Explorer Toolbar & Global Bindings ====================
    document.querySelectorAll(".nav-tab[data-tab]").forEach((btn) => {
      btn.addEventListener("click", () => switchTab(btn.getAttribute("data-tab")));
    });

    document.getElementById("btn-theme-toggle").addEventListener("click", () => {
      state.theme = state.theme === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", state.theme);
      saveState({ theme: state.theme });
      syncHeaderUi();
    });

    document.getElementById("btn-zoom-in").addEventListener("click", () => explorerPz.zoomAt(1.25));
    document.getElementById("btn-zoom-out").addEventListener("click", () => explorerPz.zoomAt(1 / 1.25));
    document.getElementById("btn-fit").addEventListener("click", () => explorerPz.fit());
    document.getElementById("btn-reset").addEventListener("click", () => explorerPz.reset());
    document.getElementById("btn-rot-cw").addEventListener("click", () => {
      explorerPz.rotateBy(90);
      elRotateBanner.hidden = true;
    });
    document.getElementById("btn-rot-ccw").addEventListener("click", () => {
      explorerPz.rotateBy(-90);
      elRotateBanner.hidden = true;
    });
    document.getElementById("btn-prev-page").addEventListener("click", () => stepPage(-1));
    document.getElementById("btn-next-page").addEventListener("click", () => stepPage(1));
    document.getElementById("btn-toggle-hotspots").addEventListener("click", () => {
      state.showHotspots = !state.showHotspots;
      renderExplorerCanvas();
      renderExplorerInfo();
    });
    document.getElementById("btn-toggle-ocr").addEventListener("click", () => {
      state.showOcrLayer = !state.showOcrLayer;
      renderExplorerCanvas();
      renderExplorerInfo();
    });
    document.getElementById("btn-toggle-filmstrip").addEventListener("click", () => {
      state.showFilmstrip = !state.showFilmstrip;
      elFilmstrip.classList.toggle("mobile-force-show", state.showFilmstrip && window.innerWidth <= 900);
      renderFilmstrip();
      setTimeout(() => explorerPz.fit(), 30);
    });
    document.getElementById("btn-fullscreen").addEventListener("click", () => {
      const stage = document.getElementById("explorer-center-col");
      if (!document.fullscreenElement) {
        if (stage.requestFullscreen) stage.requestFullscreen().catch(() => {});
      } else if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      }
    });

    // Mobile drawers
    document.getElementById("btn-mob-pages").addEventListener("click", () => {
      elInfoDrawer.classList.remove("is-open");
      elSideDrawer.classList.toggle("is-open");
    });
    document.getElementById("btn-mob-info").addEventListener("click", () => {
      elSideDrawer.classList.remove("is-open");
      elInfoDrawer.classList.toggle("is-open");
    });
    document.getElementById("btn-close-side-drawer")?.addEventListener("click", () => {
      elSideDrawer.classList.remove("is-open");
    });
    document.getElementById("btn-close-info-drawer")?.addEventListener("click", () => {
      elInfoDrawer.classList.remove("is-open");
    });

    // Sidebar filter controls
    elNavCatSelect.addEventListener("change", () => {
      state.navFilterCat = elNavCatSelect.value;
      renderNavigatorSidebar();
    });
    elNavFilterInput.addEventListener(
      "input",
      debounce(() => {
        state.navFilterQuery = elNavFilterInput.value;
        renderNavigatorSidebar();
      }, 150)
    );

    // Global Keyboard Shortcuts
    window.addEventListener("keydown", (e) => {
      const tag = (e.target && e.target.tagName) || "";
      const isTyping = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";

      if (e.key === "/" && !isTyping) {
        e.preventDefault();
        elSearchInput.focus();
        return;
      }
      if (e.key === "Escape") {
        elSearchDropdown.hidden = true;
        elSideDrawer.classList.remove("is-open");
        elInfoDrawer.classList.remove("is-open");
        return;
      }
      if (isTyping || state.activeTab !== "explore") return;

      if (e.key === "+" || e.key === "=") {
        e.preventDefault();
        explorerPz.zoomAt(1.22);
      } else if (e.key === "-") {
        e.preventDefault();
        explorerPz.zoomAt(1 / 1.22);
      } else if (e.key === "0") {
        e.preventDefault();
        explorerPz.fit();
      } else if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        explorerPz.rotateBy(90);
      } else if (e.key === "h" || e.key === "H") {
        e.preventDefault();
        state.showHotspots = !state.showHotspots;
        renderExplorerCanvas();
      }
    });

    window.addEventListener(
      "resize",
      debounce(() => {
        if (state.activeTab === "explore") explorerPz.fit();
      }, 180)
    );

    // Deep links, used by the Tasees course screens (07_الهوية_البصرية_والتفاعل):
    //   index.html#ali-181            open a page
    //   index.html#ali-181~<hotspot>  open a page with a verified hotspot selected
    //   index.html#cmp-<id>           open a comparison preset
    function applyDeepLink() {
      let h = "";
      try { h = decodeURIComponent((location.hash || "").slice(1)); } catch (err) { return false; }
      if (!h) return false;
      const preset = (manifest.comparisons || []).find((c) => c.id === h);
      if (preset) {
        switchTab("compare");
        compareCtrl.activePresetId = preset.id;
        compareCtrl.leftId = preset.leftId;
        compareCtrl.rightId = preset.rightId;
        compareCtrl.syncZoom = Boolean(preset.syncAllowed);
        compareCtrl.swipeMode = preset.mode === "vector-registered";
        compareCtrl.render();
        return true;
      }
      const [pid, hid] = h.split("~");
      const page = pageById.get(pid);
      if (!page) return false;
      const hs = hid ? (page.hotspots || []).find((x) => x.id === hid) : null;
      openPageInExplorer(page.id, hs ? { selectedFeature: { type: "hotspot", data: hs } } : {});
      return true;
    }
    window.addEventListener("hashchange", applyDeepLink);

    // Boot!
    if (!applyDeepLink()) {
      recordRecent(state.currentPageId);
      syncHeaderUi();
      renderExplorerAll();
    }
  }

  async function bootApp() {
    try {
      if (!window.__ATLAS_MANIFEST__ && window.__ATLAS_MANIFEST_GZ__) {
        window.__ATLAS_MANIFEST__ = await gunzipBase64Json(window.__ATLAS_MANIFEST_GZ__);
      }
      if (!window.__ATLAS_OCR_WORDS__ && window.__ATLAS_OCR_WORDS_GZ__) {
        window.__ATLAS_OCR_WORDS__ = await gunzipBase64Json(window.__ATLAS_OCR_WORDS_GZ__);
      }
    } catch (err) {
      console.error("Failed to decompress offline atlas bundles:", err);
    }
    initApp();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootApp);
  } else {
    bootApp();
  }
})();
