/* ==========================================================================
   compare.js — Module G: Side-by-Side & Registered Swipe Map Comparison
   Supports both vector-registered spreads (maps8) and visually verified
   raster-registered historical map pairs across the 7 atlases.
   ========================================================================== */
(function () {
  "use strict";

  const { escapeHtml, toArabicDigits } = window.AtlasUtils;
  const { PanZoomController } = window.AtlasPanZoom;
  const { renderMaps8Spread, renderScannedPage } = window.AtlasViewer;

  function isSwipeCapable(preset) {
    if (!preset) return false;
    return Boolean(
      preset.swipeAllowed ||
        preset.mode === "vector-registered" ||
        preset.mode === "raster-registered"
    );
  }

  class ComparisonController {
    constructor(containerEl, manifest, onOpenInExplorer) {
      this.container = containerEl;
      this.manifest = manifest;
      this.onOpenInExplorer = onOpenInExplorer;
      this.pageById = new Map(manifest.pages.map((p) => [p.id, p]));
      this.volById = new Map(manifest.volumes.map((v) => [v.id, v]));

      const firstPreset = manifest.comparisons[0];
      this.activePresetId = firstPreset ? firstPreset.id : "custom";
      this.leftId = firstPreset ? firstPreset.leftId : "maps8-003";
      this.rightId = firstPreset ? firstPreset.rightId : "maps8-007";
      this.swipeMode = isSwipeCapable(firstPreset);
      this.syncZoom = firstPreset ? Boolean(firstPreset.syncAllowed) : true;
      this.swipePct = 50;

      this.pzLeft = null;
      this.pzRight = null;
      this._syncing = false;
    }

    selectPreset(presetId) {
      const p = (this.manifest.comparisons || []).find((c) => c.id === presetId);
      if (!p) return false;
      this.activePresetId = p.id;
      this.leftId = p.leftId;
      this.rightId = p.rightId;
      this.syncZoom = Boolean(p.syncAllowed);
      this.swipeMode = isSwipeCapable(p);
      this.swipePct = 50;
      this.render();
      return true;
    }

    render() {
      const presets = this.manifest.comparisons || [];
      const curPreset = presets.find((c) => c.id === this.activePresetId);
      const canSwipe = isSwipeCapable(curPreset);
      const pageLeft = this.pageById.get(this.leftId);
      const pageRight = this.pageById.get(this.rightId);

      // Build map/page options grouped by volume
      const buildOptions = (selectedId) => {
        return this.manifest.volumes
          .map((vol) => {
            const vPages = this.manifest.pages.filter((p) => p.volumeId === vol.id);
            const mapPages = vPages.filter((p) => p.category === "map" || p.category === "spread-map");
            const opts = mapPages
              .map(
                (p) =>
                  `<option value="${p.id}" ${p.id === selectedId ? "selected" : ""}>ص ${toArabicDigits(p.sourcePage)} — ${escapeHtml(p.title)}</option>`
              )
              .join("");
            return `<optgroup label="${escapeHtml(vol.shortTitle)}">${opts}</optgroup>`;
          })
          .join("");
      };

      const presetOpts = [
        ...presets.map(
          (c) =>
            `<option value="${c.id}" ${c.id === this.activePresetId ? "selected" : ""}>${
              isSwipeCapable(c) ? "⇔ " : ""
            }${escapeHtml(c.title)}</option>`
        ),
        `<option value="custom" ${this.activePresetId === "custom" ? "selected" : ""}>اختيار حرّ بين أي خريطتين في الأطالس السبعة…</option>`,
      ].join("");

      const syncWarn =
        curPreset && !curPreset.syncAllowed
          ? `<span class="badge badge-warn">مقياسا الرسم مختلفان — المزامنة التلقائية معطّلة افتراضيًا لمنع الإيهام بتكافؤ القياس</span>`
          : canSwipe
          ? `<span class="badge badge-verified">تطابق إطاري موثّق — يدعم شريط السحب المتطابق</span>`
          : `<span class="badge badge-verified">مقارنة جغرافية موثقة بالمصادر</span>`;

      this.container.innerHTML = `
        <div class="dual-stage">
          <div class="dual-controls">
            <div class="toolbar-group" style="flex:1;min-width:260px">
              <label for="cmp-preset-sel" style="font-size:12.5px;font-weight:700">المقارنة المقترحة:</label>
              <select id="cmp-preset-sel" style="padding:5px 10px;border-radius:6px;border:1px solid var(--border-subtle);background:var(--bg-elevated);max-width:460px">
                ${presetOpts}
              </select>
              ${syncWarn}
            </div>
            <div class="toolbar-group">
              ${
                canSwipe
                  ? `<button type="button" class="btn ${this.swipeMode ? "is-on" : ""}" id="cmp-toggle-swipe">⇔ شريط السحب المتطابق</button>`
                  : ""
              }
              <label style="font-size:12.5px;display:inline-flex;align-items:center;gap:6px;cursor:pointer">
                <input type="checkbox" id="cmp-sync-chk" ${this.syncZoom ? "checked" : ""} />
                مزامنة التكبير والتحريك
              </label>
              <button type="button" class="btn" id="cmp-fit-both">ملاءمة الكل</button>
            </div>
          </div>

          <div style="padding:6px 16px;background:var(--bg-muted);border-block-end:1px solid var(--border-subtle);font-size:12px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
            <span>${curPreset ? escapeHtml(curPreset.note) : "قارن بين أي خريطتين من الأطالس السبعة جنبًا إلى جنب."}</span>
            ${
              canSwipe && this.swipeMode
                ? `<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                     <span>موضع الستارة:</span>
                     <input type="range" id="cmp-swipe-range" min="5" max="95" value="${this.swipePct}" style="width:180px" aria-label="شريط المقارنة بالتمرير" />
                     <bdi id="cmp-swipe-pct-label">${toArabicDigits(this.swipePct)}%</bdi>
                     <button type="button" class="btn" id="cmp-open-left" style="padding:2px 8px;font-size:11.5px">فتح الأولى بالمستكشف</button>
                     <button type="button" class="btn" id="cmp-open-right" style="padding:2px 8px;font-size:11.5px">فتح الثانية بالمستكشف</button>
                   </div>`
                : ""
            }
          </div>

          ${
            canSwipe && this.swipeMode
              ? `<div class="swipe-stage" id="cmp-swipe-stage">
                   <div class="map-viewport" id="cmp-vp-base" style="width:100%;height:100%">
                     <div class="panzoom-world" id="cmp-world-base"></div>
                   </div>
                   <div class="swipe-layer-top" id="cmp-swipe-top" style="background:var(--bg-canvas)">
                     <div class="map-viewport" id="cmp-vp-top" style="width:100%;height:100%;pointer-events:none;background:var(--bg-canvas)">
                       <div class="panzoom-world" id="cmp-world-top"></div>
                     </div>
                   </div>
                   <div class="swipe-slider-bar" id="cmp-slider-bar" role="slider" aria-label="اسحب للمقارنة بين الخريطتين" aria-valuemin="5" aria-valuemax="95" aria-valuenow="${this.swipePct}" tabindex="0"></div>
                   <div class="swipe-corner-pill swipe-pill-left">${pageLeft ? escapeHtml(pageLeft.title) : ""}</div>
                   <div class="swipe-corner-pill swipe-pill-right">${pageRight ? escapeHtml(pageRight.title) : ""}</div>
                 </div>`
              : `<div class="dual-panes">
                   <div class="dual-pane">
                     <div class="dual-pane-head">
                       <select id="cmp-left-sel" aria-label="الخريطة اليمنى" style="flex:1;padding:4px 8px;border-radius:6px;border:1px solid var(--border-subtle);background:var(--bg-surface)">
                         ${buildOptions(this.leftId)}
                       </select>
                       <button type="button" class="btn" id="cmp-open-left">فتح بالمستكشف</button>
                     </div>
                     <div class="map-viewport" id="cmp-vp-left">
                       <div class="panzoom-world" id="cmp-world-left"></div>
                     </div>
                   </div>
                   <div class="dual-pane">
                     <div class="dual-pane-head">
                       <select id="cmp-right-sel" aria-label="الخريطة اليسرى" style="flex:1;padding:4px 8px;border-radius:6px;border:1px solid var(--border-subtle);background:var(--bg-surface)">
                         ${buildOptions(this.rightId)}
                       </select>
                       <button type="button" class="btn" id="cmp-open-right">فتح بالمستكشف</button>
                     </div>
                     <div class="map-viewport" id="cmp-vp-right">
                       <div class="panzoom-world" id="cmp-world-right"></div>
                     </div>
                   </div>
                 </div>`
          }
        </div>
      `;

      this._bindControls(canSwipe);
      if (canSwipe && this.swipeMode) {
        this._mountSwipeRegistered(curPreset);
      } else {
        this._mountSideBySide();
      }
    }

    _bindControls() {
      const presetSel = this.container.querySelector("#cmp-preset-sel");
      presetSel.addEventListener("change", () => {
        this.activePresetId = presetSel.value;
        const p = (this.manifest.comparisons || []).find((c) => c.id === this.activePresetId);
        if (p) {
          this.leftId = p.leftId;
          this.rightId = p.rightId;
          this.syncZoom = Boolean(p.syncAllowed);
          this.swipeMode = isSwipeCapable(p);
        } else {
          this.swipeMode = false;
        }
        this.render();
      });

      const syncChk = this.container.querySelector("#cmp-sync-chk");
      if (syncChk) {
        syncChk.addEventListener("change", () => {
          this.syncZoom = syncChk.checked;
        });
      }

      const swipeBtn = this.container.querySelector("#cmp-toggle-swipe");
      if (swipeBtn) {
        swipeBtn.addEventListener("click", () => {
          this.swipeMode = !this.swipeMode;
          this.render();
        });
      }

      const fitBtn = this.container.querySelector("#cmp-fit-both");
      if (fitBtn) {
        fitBtn.addEventListener("click", () => {
          if (this.pzLeft) this.pzLeft.fit();
          if (this.pzRight && !this.swipeMode) this.pzRight.fit();
        });
      }

      const leftSel = this.container.querySelector("#cmp-left-sel");
      const rightSel = this.container.querySelector("#cmp-right-sel");
      if (leftSel) {
        leftSel.addEventListener("change", () => {
          this.leftId = leftSel.value;
          this.activePresetId = "custom";
          this.render();
        });
      }
      if (rightSel) {
        rightSel.addEventListener("change", () => {
          this.rightId = rightSel.value;
          this.activePresetId = "custom";
          this.render();
        });
      }

      const openL = this.container.querySelector("#cmp-open-left");
      const openR = this.container.querySelector("#cmp-open-right");
      if (openL) openL.addEventListener("click", () => this.onOpenInExplorer(this.leftId));
      if (openR) openR.addEventListener("click", () => this.onOpenInExplorer(this.rightId));
    }

    async _mountSwipeRegistered(preset) {
      const stage = this.container.querySelector("#cmp-swipe-stage");
      const vpBase = this.container.querySelector("#cmp-vp-base");
      const worldBase = this.container.querySelector("#cmp-world-base");
      const vpTop = this.container.querySelector("#cmp-vp-top");
      const worldTop = this.container.querySelector("#cmp-world-top");
      const topWrap = this.container.querySelector("#cmp-swipe-top");
      const bar = this.container.querySelector("#cmp-slider-bar");
      const range = this.container.querySelector("#cmp-swipe-range");
      const pctLabel = this.container.querySelector("#cmp-swipe-pct-label");

      const updateClip = (rawPct) => {
        const pct = Math.max(5, Math.min(95, Math.round(rawPct)));
        this.swipePct = pct;
        topWrap.style.clipPath = `inset(0 0 0 ${pct}%)`;
        bar.style.left = `${pct}%`;
        bar.setAttribute("aria-valuenow", String(pct));
        if (range && Number(range.value) !== pct) range.value = String(pct);
        if (pctLabel) pctLabel.textContent = `${toArabicDigits(pct)}%`;
      };
      updateClip(this.swipePct);

      if (range) {
        range.addEventListener("input", () => {
          updateClip(Number(range.value));
        });
      }

      // Direct pointer + keyboard dragging on the vertical curtain bar
      if (bar && stage) {
        let draggingBar = false;
        bar.addEventListener("pointerdown", (ev) => {
          ev.stopPropagation();
          ev.preventDefault();
          draggingBar = true;
          bar.setPointerCapture(ev.pointerId);
        });
        bar.addEventListener("pointermove", (ev) => {
          if (!draggingBar) return;
          const rect = stage.getBoundingClientRect();
          if (rect.width > 0) {
            updateClip(((ev.clientX - rect.left) / rect.width) * 100);
          }
        });
        const stopDrag = (ev) => {
          if (!draggingBar) return;
          draggingBar = false;
          try {
            bar.releasePointerCapture(ev.pointerId);
          } catch (_) {}
        };
        bar.addEventListener("pointerup", stopDrag);
        bar.addEventListener("pointercancel", stopDrag);
        bar.addEventListener("keydown", (ev) => {
          if (ev.key === "ArrowLeft") {
            ev.preventDefault();
            updateClip(this.swipePct - 4);
          } else if (ev.key === "ArrowRight") {
            ev.preventDefault();
            updateClip(this.swipePct + 4);
          }
        });
      }

      if (preset.mode === "vector-registered") {
        const maps8Vol = this.volById.get("maps8");
        const figLeft = maps8Vol.figures.find((f) => f.id === preset.leftFigure);
        const figRight = maps8Vol.figures.find((f) => f.id === preset.rightFigure);

        this.pzRight = new PanZoomController(vpTop, worldTop, {});
        this.pzLeft = new PanZoomController(vpBase, worldBase, {
          onChange: (st) => {
            this.pzRight.setState(st, true);
          },
        });

        await Promise.all([
          renderMaps8Spread({
            worldEl: worldBase,
            panzoom: this.pzLeft,
            maps8Vol,
            figure: figLeft,
            hiddenLayers: [],
            showHotspots: false,
          }),
          renderMaps8Spread({
            worldEl: worldTop,
            panzoom: this.pzRight,
            maps8Vol,
            figure: figRight,
            hiddenLayers: [],
            showHotspots: false,
          }),
        ]);
        this.pzRight.setState(this.pzLeft.getState(), true);
        return;
      }

      // Raster-registered historical scanned map pair
      const pageLeft = this.pageById.get(preset.leftId);
      const pageRight = this.pageById.get(preset.rightId);
      if (!pageLeft || !pageRight) return;

      const rotLeft = pageLeft.rotated || 0;
      const rotRight = pageRight.rotated || 0;
      const effWidthLeft = Math.abs(rotLeft) === 90 ? pageLeft.height : pageLeft.width;
      const effWidthRight = Math.abs(rotRight) === 90 ? pageRight.height : pageRight.width;
      const widthRatio = effWidthLeft && effWidthRight ? effWidthLeft / effWidthRight : 1;

      const syncTopToBase = (st) => {
        if (!this.pzRight || !st) return;
        this.pzRight.setState(
          {
            tx: st.tx,
            ty: st.ty,
            scale: st.scale * widthRatio,
            rotation: rotRight,
          },
          true
        );
      };

      this.pzRight = new PanZoomController(vpTop, worldTop, {});
      this.pzLeft = new PanZoomController(vpBase, worldBase, {
        onChange: syncTopToBase,
      });

      renderScannedPage({
        worldEl: worldBase,
        panzoom: this.pzLeft,
        page: pageLeft,
        ocrWords: [],
        showHotspots: false,
        showOcrLayer: false,
        initialRotation: rotLeft,
      });

      renderScannedPage({
        worldEl: worldTop,
        panzoom: this.pzRight,
        page: pageRight,
        ocrWords: [],
        showHotspots: false,
        showOcrLayer: false,
        initialRotation: rotRight,
      });

      syncTopToBase(this.pzLeft.getState());
    }

    async _mountSideBySide() {
      const vpL = this.container.querySelector("#cmp-vp-left");
      const wL = this.container.querySelector("#cmp-world-left");
      const vpR = this.container.querySelector("#cmp-vp-right");
      const wR = this.container.querySelector("#cmp-world-right");

      this.pzLeft = new PanZoomController(vpL, wL, {
        onChange: (st) => {
          if (!this.syncZoom || this._syncing || !this.pzRight) return;
          this._syncing = true;
          this.pzRight.setState(st, true);
          this._syncing = false;
        },
      });

      this.pzRight = new PanZoomController(vpR, wR, {
        onChange: (st) => {
          if (!this.syncZoom || this._syncing || !this.pzLeft) return;
          this._syncing = true;
          this.pzLeft.setState(st, true);
          this._syncing = false;
        },
      });

      await Promise.all([
        this._renderPanePage(this.leftId, wL, this.pzLeft),
        this._renderPanePage(this.rightId, wR, this.pzRight),
      ]);
    }

    async _renderPanePage(pageId, worldEl, pz) {
      const page = this.pageById.get(pageId);
      if (!page) return;
      if (page.volumeId === "maps8" && page.figureId) {
        const maps8Vol = this.volById.get("maps8");
        const fig = maps8Vol.figures.find((f) => f.id === page.figureId);
        await renderMaps8Spread({
          worldEl,
          panzoom: pz,
          maps8Vol,
          figure: fig,
          hiddenLayers: [],
          showHotspots: false,
        });
      } else {
        renderScannedPage({
          worldEl,
          panzoom: pz,
          page,
          ocrWords: [],
          showHotspots: true,
          showOcrLayer: false,
          initialRotation: page.rotated || 0,
        });
      }
    }
  }

  window.AtlasCompare = { ComparisonController };
})();
