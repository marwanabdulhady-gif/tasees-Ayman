/* ==========================================================================
   learn.js — Module H: Verified Geographic & Historical Knowledge Discovery
   Questions & blind-map challenges are generated strictly from verified source
   data across all 7 volumes (NEVER unreviewed raw OCR), with full filtering by
   Atlas Volume and by Tasees Course Unit / Week / Lecture Series.
   ========================================================================== */
(function () {
  "use strict";

  const { escapeHtml, toArabicDigits, loadState, saveState } = window.AtlasUtils;
  const { PanZoomController } = window.AtlasPanZoom;
  const { renderMaps8Spread } = window.AtlasViewer;

  class LearningController {
    constructor(containerEl, manifest, onJumpToSource) {
      this.container = containerEl;
      this.manifest = manifest;
      this.onJumpToSource = onJumpToSource;
      this.volById = new Map(manifest.volumes.map((v) => [v.id, v]));
      this.pageById = new Map(manifest.pages.map((p) => [p.id, p]));

      const st = loadState();
      this.progress = st.quizProgress || { answered: 0, correct: 0 };
      this.reviewDeck = st.reviewDeck || [];
      this.mode = "mcq"; // mcq | map-find | flashcards | review
      this.volFilter = "all";
      this.courseFilter = "all";
      this.courseFilterLabel = "";
      this.mapChallengeKind = "all"; // all | raster-loc | vector-loc
      this.cardFlipped = false;
      this.cardIdx = 0;

      this.questionPool = this._buildVerifiedPool();
      this.currentQuestion = null;
    }

    applyCourseFilter(filterKey, customLabel, preferredMode) {
      this.courseFilter = filterKey || "all";
      this.courseFilterLabel = customLabel || "";
      this.volFilter = "all";
      if (preferredMode) this.mode = preferredMode;
      this.currentQuestion = null;
      this.cardIdx = 0;
      this.render();
    }

    _buildVerifiedPool() {
      const pool = [];
      const maps8Vol = this.volById.get("maps8");

      // 1. Verified curated map hotspot facts + blind-map location challenges across Vols. 2–7
      for (const p of this.manifest.pages) {
        if (p.volumeId === "maps8") continue;
        const vol = this.volById.get(p.volumeId);
        const highHotspots = (p.hotspots || []).filter((hs) => hs.conf === "high");

        for (const hs of highHotspots) {
          if (hs.fact) {
            pool.push({
              id: `q-hs-${hs.id}`,
              kind: "hotspot-fact",
              volumeId: p.volumeId,
              prompt: `في خريطة «${p.title}»، ما الدلالة الجغرافية أو التاريخية لمعلم «${hs.name}»؟`,
              answer: hs.fact,
              shortTitle: hs.name,
              hotspotId: hs.id,
              pageId: p.id,
              sourceCitation: `${vol.shortTitle} — ص ${toArabicDigits(p.sourcePage)} (${p.title})`,
              distractorGroup: "fact",
            });
          }
        }

        // Scanned blind-map location challenges on maps with >= 3 distinct hotspots
        if (highHotspots.length >= 3) {
          for (const hs of highHotspots) {
            pool.push({
              id: `q-rloc-${p.id}-${hs.id}`,
              kind: "raster-loc",
              volumeId: p.volumeId,
              prompt: `على خريطة «${p.title}»، حدّد الموضع المرقّم لـ: «${hs.name}»`,
              answer: `${hs.name} — ${hs.fact || p.title}`,
              shortTitle: hs.name,
              fact: hs.fact || "",
              hotspotId: hs.id,
              pageId: p.id,
              sourceCitation: `${vol.shortTitle} — ص ${toArabicDigits(p.sourcePage)} (${p.title})`,
              distractorGroup: "raster-loc",
            });
          }
        }
      }

      // 2. Verified map-to-chapter / volume attribution questions from printed indexes
      const verifiedMaps = this.manifest.pages.filter(
        (p) => p.category === "map" && p.titleSource === "verified-index"
      );
      for (const mp of verifiedMaps) {
        const vol = this.volById.get(mp.volumeId);
        pool.push({
          id: `q-mapsec-${mp.id}`,
          kind: "map-section",
          volumeId: mp.volumeId,
          prompt: `في أي باب أو فصل ترد خريطة «${mp.title}»؟`,
          answer: `${mp.sectionTitle} (${vol.shortTitle})`,
          shortTitle: mp.title,
          pageId: mp.id,
          sourceCitation: `${vol.shortTitle} — ص ${toArabicDigits(mp.sourcePage)}`,
          distractorGroup: "section",
        });
      }

      // 3. Verified vector labels on maps8 figures
      if (maps8Vol && Array.isArray(maps8Vol.features)) {
        const highFeats = maps8Vol.features.filter(
          (f) =>
            f.conf === "high" &&
            ["place", "polity", "water", "river", "region"].includes(f.kind) &&
            f.text.length >= 3
        );
        for (const ft of highFeats) {
          const fig = maps8Vol.figures.find((g) => g.id === ft.figure);
          pool.push({
            id: `q-vec-${ft.id}`,
            kind: "vector-loc",
            volumeId: "maps8",
            prompt: `حدّد موضع «${ft.text}» (${ft.kindLabel}) بالنقر المباشر على «${fig.caption}»`,
            answer: `${ft.text} — ${ft.kindLabel} في ${fig.caption}`,
            shortTitle: ft.text,
            featureId: ft.id,
            figureId: ft.figure,
            pageId: `maps8-${String(ft.page).padStart(3, "0")}`,
            sourceCitation: `خرائط التاريخ الإسلامي — ${fig.caption} (ص ${toArabicDigits(ft.page)})`,
            distractorGroup: "vector",
          });
        }
      }

      return pool;
    }

    _getFilteredPool() {
      let items = this.questionPool;
      if (this.volFilter !== "all") {
        items = items.filter((q) => q.volumeId === this.volFilter);
      }
      if (this.courseFilter !== "all" && window.AtlasCourses) {
        const allowedPages = window.AtlasCourses.getMapPageIdsForFilter(this.courseFilter);
        if (allowedPages && allowedPages.size > 0) {
          items = items.filter((q) => {
            if (allowedPages.has(q.pageId)) return true;
            // For maps8 spread halves, match sibling half in the same spread figure
            if (q.figureId && q.volumeId === "maps8") {
              const pMatch = this.manifest.pages.some(
                (mp) => mp.volumeId === "maps8" && mp.figureId === q.figureId && allowedPages.has(mp.id)
              );
              if (pMatch) return true;
            }
            return false;
          });
        }
      }
      return items;
    }

    _pickMcq() {
      const filtered = this._getFilteredPool();
      const mcqItems = filtered.filter((q) => q.kind === "hotspot-fact" || q.kind === "map-section");
      if (!mcqItems.length) return null;
      const item = mcqItems[Math.floor(Math.random() * mcqItems.length)];
      // Draw distractors from full pool of same distractorGroup so options always stay 4 rich choices
      const sameGroup = this.questionPool.filter(
        (q) => q.distractorGroup === item.distractorGroup && q.answer !== item.answer
      );
      const shuffled = sameGroup
        .slice()
        .sort(() => Math.random() - 0.5)
        .slice(0, 3)
        .map((q) => q.answer);
      const options = [item.answer, ...shuffled].sort(() => Math.random() - 0.5);
      return { ...item, options, answered: false };
    }

    _pickMapChallenge() {
      const filtered = this._getFilteredPool();
      let locItems = filtered.filter((q) => q.kind === "vector-loc" || q.kind === "raster-loc");
      if (this.mapChallengeKind === "raster-loc") {
        const rOnly = locItems.filter((q) => q.kind === "raster-loc");
        if (rOnly.length) locItems = rOnly;
      } else if (this.mapChallengeKind === "vector-loc") {
        const vOnly = locItems.filter((q) => q.kind === "vector-loc");
        if (vOnly.length) locItems = vOnly;
      }
      if (!locItems.length) return null;
      return { ...locItems[Math.floor(Math.random() * locItems.length)], solved: false };
    }

    toggleReviewItem(itemId) {
      const idx = this.reviewDeck.indexOf(itemId);
      if (idx >= 0) this.reviewDeck.splice(idx, 1);
      else this.reviewDeck.push(itemId);
      saveState({ reviewDeck: this.reviewDeck });
    }

    render() {
      const acc = this.progress.answered
        ? Math.round((this.progress.correct / this.progress.answered) * 100)
        : 0;
      const activePool = this._getFilteredPool();

      const volOptions = [
        `<option value="all" ${this.volFilter === "all" ? "selected" : ""}>جميع الأطالس السبعة</option>`,
        ...this.manifest.volumes.map(
          (v) =>
            `<option value="${v.id}" ${this.volFilter === v.id ? "selected" : ""}>${escapeHtml(v.shortTitle)}</option>`
        ),
      ].join("");

      const presetCourseFilters = [
        ["all", "كل موضوعات المنصة"],
        ["u2", "دورة تأسيس — الوحدة ٢: سفر المعرفة"],
        ["u4", "دورة تأسيس — الوحدة ٤: السيرة النبوية"],
        ["u5", "دورة تأسيس — الوحدة ٥: الراشدون والفتنة"],
        ["u6", "دورة تأسيس — الوحدة ٦: الدول والحضارة"],
        ["u7", "دورة تأسيس — الوحدة ٧: العثمانيون والحدود"],
        ["tr-100q", "سلسلة ١٠٠ سؤال في التاريخ"],
        ["tr-seerah-makkah", "دورة السيرة — العهد المكي"],
        ["tr-umayyad-abbasid", "دورة الأمويين والعباسيين"],
        ["tr-muslim-awareness", "دورة وعي المسلم المعاصر"],
      ];
      if (
        this.courseFilter !== "all" &&
        !presetCourseFilters.some(([k]) => k === this.courseFilter)
      ) {
        presetCourseFilters.splice(1, 0, [
          this.courseFilter,
          this.courseFilterLabel || `تصفية مخصصة (${this.courseFilter})`,
        ]);
      }
      const courseOptions = presetCourseFilters
        .map(
          ([k, lbl]) =>
            `<option value="${escapeHtml(k)}" ${this.courseFilter === k ? "selected" : ""}>${escapeHtml(lbl)}</option>`
        )
        .join("");

      this.container.innerHTML = `
        <div class="content-container">
          <div class="section-header-bar">
            <div>
              <h2 style="margin:0;font-size:18px">بيئة التعلّم وتحدّيات الخريطة الصمّاء</h2>
              <p style="margin:4px 0 0 0;font-size:12.5px;color:var(--ink-secondary)">
                جميع الأسئلة وتحديات الخريطة الصمّاء والبطاقات مولّدة حصريًا من البيانات المحققة في الأطالس السبعة مع توثيق الصفحة المصدر (لا يُستخدم نص OCR غير المراجع في توليد الأسئلة).
              </p>
            </div>
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
              <span class="badge badge-verified">الإجابات الصحيحة: ${toArabicDigits(this.progress.correct)} / ${toArabicDigits(this.progress.answered)} (${toArabicDigits(acc)}%)</span>
              <span class="badge badge-warn">قائمة المراجعة: ${toArabicDigits(this.reviewDeck.length)}</span>
            </div>
          </div>

          <div class="learn-filter-bar" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:10px 14px;margin-bottom:14px;border-radius:10px;background:var(--bg-elevated);border:1px solid var(--border-subtle)">
            <label style="font-size:12.5px;font-weight:700">مسار الدورة / المحاضرات:</label>
            <select id="learn-course-sel" style="padding:5px 10px;border-radius:6px;border:1px solid var(--border-subtle);background:var(--bg-surface);font-size:12.5px">
              ${courseOptions}
            </select>
            <label style="font-size:12.5px;font-weight:700">المجلد:</label>
            <select id="learn-vol-sel" style="padding:5px 10px;border-radius:6px;border:1px solid var(--border-subtle);background:var(--bg-surface);font-size:12.5px">
              ${volOptions}
            </select>
            <span class="badge badge-ocr">بنك الأسئلة النشط: ${toArabicDigits(activePool.length)} عنصر موثّق</span>
            ${
              this.courseFilter !== "all" || this.volFilter !== "all"
                ? `<button type="button" class="btn" id="learn-clear-filters" style="padding:3px 10px;font-size:12px">إلغاء التصفية ✕</button>`
                : ""
            }
          </div>

          <div class="learn-grid">
            <aside style="display:flex;flex-direction:column;gap:8px">
              <button type="button" class="btn ${this.mode === "mcq" ? "btn-primary" : ""}" data-lmode="mcq" style="justify-content:flex-start;padding:10px 14px">
                ١. اختبارات الخرائط والمعالم الموثقة
              </button>
              <button type="button" class="btn ${this.mode === "map-find" ? "btn-primary" : ""}" data-lmode="map-find" style="justify-content:flex-start;padding:10px 14px">
                ٢. تحدي الخريطة الصمّاء (متجهي + ممسوح)
              </button>
              <button type="button" class="btn ${this.mode === "flashcards" ? "btn-primary" : ""}" data-lmode="flashcards" style="justify-content:flex-start;padding:10px 14px">
                ٣. البطاقات التعليمية الذكية (${toArabicDigits(activePool.length)})
              </button>
              <button type="button" class="btn ${this.mode === "review" ? "btn-primary" : ""}" data-lmode="review" style="justify-content:flex-start;padding:10px 14px">
                ٤. قائمة المراجعة المحفوظة (${toArabicDigits(this.reviewDeck.length)})
              </button>
              <hr style="border:none;border-top:1px solid var(--border-subtle);width:100%;margin:8px 0" />
              <button type="button" class="btn" id="learn-reset-prog" style="justify-content:center">
                تصفير عداد التقدم
              </button>
            </aside>

            <section id="learn-stage-body"></section>
          </div>
        </div>
      `;

      this.container.querySelector("#learn-course-sel").addEventListener("change", (ev) => {
        this.courseFilter = ev.target.value;
        this.courseFilterLabel = "";
        this.currentQuestion = null;
        this.cardIdx = 0;
        this.render();
      });

      this.container.querySelector("#learn-vol-sel").addEventListener("change", (ev) => {
        this.volFilter = ev.target.value;
        this.currentQuestion = null;
        this.cardIdx = 0;
        this.render();
      });

      const clrBtn = this.container.querySelector("#learn-clear-filters");
      if (clrBtn) {
        clrBtn.addEventListener("click", () => {
          this.courseFilter = "all";
          this.courseFilterLabel = "";
          this.volFilter = "all";
          this.currentQuestion = null;
          this.render();
        });
      }

      this.container.querySelectorAll("[data-lmode]").forEach((btn) => {
        btn.addEventListener("click", () => {
          this.mode = btn.getAttribute("data-lmode");
          this.currentQuestion = null;
          this.render();
        });
      });

      const rst = this.container.querySelector("#learn-reset-prog");
      if (rst) {
        rst.addEventListener("click", () => {
          this.progress = { answered: 0, correct: 0 };
          saveState({ quizProgress: this.progress });
          this.render();
        });
      }

      const stage = this.container.querySelector("#learn-stage-body");
      if (this.mode === "mcq") this._renderMcq(stage);
      else if (this.mode === "map-find") this._renderMapFind(stage);
      else if (this.mode === "flashcards") this._renderFlashcards(stage);
      else this._renderReviewList(stage);
    }

    _renderMcq(stage) {
      if (
        !this.currentQuestion ||
        (this.currentQuestion.kind !== "hotspot-fact" && this.currentQuestion.kind !== "map-section")
      ) {
        this.currentQuestion = this._pickMcq();
      }
      const q = this.currentQuestion;
      if (!q) {
        stage.innerHTML = `<div class="quiz-card"><p style="margin:0">لا توجد أسئلة اختيار من متعدد ضمن هذه التصفية حاليًا — جرّب «تحدي الخريطة الصمّاء» أو وسّع التصفية.</p></div>`;
        return;
      }
      const inRev = this.reviewDeck.includes(q.id);

      stage.innerHTML = `
        <div class="quiz-card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px">
            <span class="badge badge-verified">سؤال مصدري موثق</span>
            <button type="button" class="btn ${inRev ? "is-on" : ""}" id="q-bookmark-btn">
              ${inRev ? "محفوظ في المراجعة ★" : "أضف للمراجعة ☆"}
            </button>
          </div>
          <h3 style="margin:0;font-size:17px;line-height:1.5">${escapeHtml(q.prompt)}</h3>
          <div class="quiz-options">
            ${q.options
              .map(
                (opt, i) => `
              <button type="button" class="quiz-opt" data-optidx="${i}">
                ${escapeHtml(opt)}
              </button>`
              )
              .join("")}
          </div>
          <div id="q-feedback" style="margin-top:16px" hidden></div>
        </div>
      `;

      stage.querySelector("#q-bookmark-btn").addEventListener("click", () => {
        this.toggleReviewItem(q.id);
        this._renderMcq(stage);
      });

      const fb = stage.querySelector("#q-feedback");
      stage.querySelectorAll(".quiz-opt").forEach((btn) => {
        btn.addEventListener("click", () => {
          if (q.answered) return;
          q.answered = true;
          const chosen = q.options[Number(btn.getAttribute("data-optidx"))];
          const ok = chosen === q.answer;
          this.progress.answered++;
          if (ok) this.progress.correct++;
          saveState({ quizProgress: this.progress });

          stage.querySelectorAll(".quiz-opt").forEach((b) => {
            b.disabled = true;
            const txt = q.options[Number(b.getAttribute("data-optidx"))];
            if (txt === q.answer) b.classList.add("is-correct");
            else if (b === btn && !ok) b.classList.add("is-wrong");
          });

          fb.hidden = false;
          fb.innerHTML = `
            <div style="padding:12px 14px;border-radius:8px;background:var(--bg-muted);border:1px solid var(--border-subtle);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
              <div>
                <strong>${ok ? "✓ إجابة صحيحة!" : "الإجابة الصحيحة موثقة في المصدر:"}</strong>
                <div style="font-size:12.5px;color:var(--ink-secondary);margin-top:3px">المصدر: ${escapeHtml(q.sourceCitation)}</div>
              </div>
              <div style="display:flex;gap:8px">
                <button type="button" class="btn" id="q-open-src">افتح الصفحة المصدر للتحقق</button>
                <button type="button" class="btn btn-primary" id="q-next-btn">السؤال التالي ←</button>
              </div>
            </div>
          `;
          fb.querySelector("#q-open-src").addEventListener("click", () =>
            this.onJumpToSource(q.pageId, q.hotspotId || null)
          );
          fb.querySelector("#q-next-btn").addEventListener("click", () => {
            this.currentQuestion = this._pickMcq();
            this.render();
          });
        });
      });
    }

    async _renderMapFind(stage) {
      if (
        !this.currentQuestion ||
        (this.currentQuestion.kind !== "vector-loc" && this.currentQuestion.kind !== "raster-loc")
      ) {
        this.currentQuestion = this._pickMapChallenge();
      }
      const q = this.currentQuestion;
      if (!q) {
        stage.innerHTML = `<div class="quiz-card"><p style="margin:0">لا توجد تحديات خريطة صمّاء ضمن هذه التصفية — وسّع نطاق المجلد أو المسار لعرض التحديات.</p></div>`;
        return;
      }

      stage.innerHTML = `
        <div class="quiz-card">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px">
            <div>
              <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
                <span class="badge badge-verified">${
                  q.kind === "raster-loc"
                    ? "تحدي الخريطة الصمّاء المرقّمة (خرائط السيرة والراشدين)"
                    : "تحدي الخريطة الصمّاء المتجهي"
                }</span>
                <select id="mf-kind-sel" style="padding:3px 8px;border-radius:6px;border:1px solid var(--border-subtle);background:var(--bg-elevated);font-size:12px">
                  <option value="all" ${this.mapChallengeKind === "all" ? "selected" : ""}>متجهي + خرائط تاريخية ممسوحة</option>
                  <option value="raster-loc" ${this.mapChallengeKind === "raster-loc" ? "selected" : ""}>خرائط السيرة والراشدين والدول فقط</option>
                  <option value="vector-loc" ${this.mapChallengeKind === "vector-loc" ? "selected" : ""}>الخرائط المتجهية فقط</option>
                </select>
              </div>
              <h3 style="margin:8px 0 0 0;font-size:16px">${escapeHtml(q.prompt)}</h3>
            </div>
            <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
              <label style="font-size:12px;display:inline-flex;align-items:center;gap:5px;cursor:pointer">
                <input type="checkbox" id="mf-hide-lbl" checked /> حجب الأسماء (خريطة صمّاء)
              </label>
              <button type="button" class="btn" id="mf-reveal">إظهار الحل</button>
              <button type="button" class="btn" id="mf-open-src">افتح بالمستكشف</button>
              <button type="button" class="btn btn-primary" id="mf-next">تحدٍّ جديد ←</button>
            </div>
          </div>
          <div id="mf-status" style="font-size:13px;margin-bottom:8px;color:var(--ink-secondary)">
            ${
              q.kind === "raster-loc"
                ? "انقر على البطاقة المرقّمة (؟) التي تغطّي الموضع الصحيح على الخريطة (يمكنك التكبير والتحريك بحرية)."
                : "انقر على الموقع الصحيح فوق الخريطة (يمكنك التكبير والتحريك بحرية)."
            }
          </div>
          <div class="map-viewport" id="mf-vp" style="height:480px;border-radius:10px;border:1px solid var(--border-strong)">
            <div class="panzoom-world" id="mf-world"></div>
          </div>
        </div>
      `;

      stage.querySelector("#mf-kind-sel").addEventListener("change", (ev) => {
        this.mapChallengeKind = ev.target.value;
        this.currentQuestion = this._pickMapChallenge();
        this.render();
      });

      stage.querySelector("#mf-open-src").addEventListener("click", () => {
        this.onJumpToSource(q.pageId, q.hotspotId || null);
      });

      stage.querySelector("#mf-next").addEventListener("click", () => {
        this.currentQuestion = this._pickMapChallenge();
        this.render();
      });

      const vp = stage.querySelector("#mf-vp");
      const world = stage.querySelector("#mf-world");
      const statusEl = stage.querySelector("#mf-status");
      const hideChk = stage.querySelector("#mf-hide-lbl");

      if (q.kind === "raster-loc") {
        this._mountRasterBlindChallenge(q, vp, world, statusEl, hideChk, stage);
        return;
      }

      const maps8Vol = this.volById.get("maps8");
      const fig = maps8Vol.figures.find((f) => f.id === q.figureId);
      const pz = new PanZoomController(vp, world, {});

      const ctrl = await renderMaps8Spread({
        worldEl: world,
        panzoom: pz,
        maps8Vol,
        figure: fig,
        hiddenLayers: [],
        showHotspots: true,
        quizHideLabels: hideChk.checked,
        onSelectFeature: (ft) => {
          const isMatch = ft.text === q.shortTitle || ft.id === q.featureId;
          this.progress.answered++;
          if (isMatch) this.progress.correct++;
          saveState({ quizProgress: this.progress });

          if (isMatch) {
            if (ctrl.svgEl) ctrl.svgEl.classList.remove("hide-label");
            ctrl.focusFeature(ft.id);
            statusEl.innerHTML = `<strong style="color:var(--accent)">✓ أحسنت! هذا موضع «${escapeHtml(ft.text)}» (${escapeHtml(q.sourceCitation)}).</strong>`;
          } else {
            statusEl.innerHTML = `<span style="color:var(--danger)">نقرت على «${escapeHtml(ft.text)}» — جرّب مرة أخرى أو اضغط «إظهار الحل».</span>`;
          }
        },
      });

      hideChk.addEventListener("change", () => {
        if (ctrl.svgEl) ctrl.svgEl.classList.toggle("hide-label", hideChk.checked);
      });

      stage.querySelector("#mf-reveal").addEventListener("click", () => {
        if (ctrl.svgEl) ctrl.svgEl.classList.remove("hide-label");
        if (ctrl.focusFeature) ctrl.focusFeature(q.featureId);
        statusEl.innerHTML = `<strong>الموقع الصحيح: «${escapeHtml(q.shortTitle)}» — ${escapeHtml(q.sourceCitation)}</strong>`;
      });
    }

    _mountRasterBlindChallenge(q, vp, world, statusEl, hideChk, stage) {
      const page = this.pageById.get(q.pageId);
      if (!page) return;
      const { resolveAsset, isAssetAvailable } = window.AtlasUtils;
      if (!isAssetAvailable(page.pageAsset)) {
        statusEl.innerHTML = `<span style="color:var(--ink-secondary)">هذه الخريطة متاحة بصورتها الكاملة في الحزمة الكاملة غير المتصلة بالإنترنت — اضغط «تحدٍّ جديد ←» للانتقال إلى خريطة مضمّنة.</span>`;
        return;
      }

      const pz = new PanZoomController(vp, world, {});
      const w = page.width || 816;
      const h = page.height || 1146;

      const wrap = document.createElement("div");
      wrap.className = "page-frame blind-map-masked";
      wrap.style.width = `${w}px`;
      wrap.style.height = `${h}px`;

      const img = document.createElement("img");
      img.className = "page-raster";
      img.src = resolveAsset(page.pageAsset);
      img.alt = page.title;
      img.width = w;
      img.height = h;
      img.draggable = false;
      wrap.appendChild(img);

      const overlay = document.createElement("div");
      overlay.className = "overlay-layer";

      const hotspots = (page.hotspots || []).filter((hs) => hs.conf === "high");
      hotspots.forEach((hs, idx) => {
        const pin = document.createElement("button");
        pin.type = "button";
        pin.className = "blind-raster-pin";
        pin.dataset.hsid = hs.id;
        pin.style.left = `${hs.x}%`;
        pin.style.top = `${hs.y}%`;
        pin.style.width = `${Math.max(hs.w, 6)}%`;
        pin.style.height = `${Math.max(hs.h, 3.8)}%`;
        pin.setAttribute("aria-label", `الموضع المرقّم ${toArabicDigits(idx + 1)}`);
        pin.innerHTML = `<span class="blind-pin-mask">؟ ${toArabicDigits(idx + 1)}</span><span class="blind-pin-ans">${escapeHtml(hs.name)}</span>`;

        pin.addEventListener("click", (ev) => {
          ev.stopPropagation();
          if (q.solved) return;
          const isMatch = hs.id === q.hotspotId;
          this.progress.answered++;
          if (isMatch) {
            this.progress.correct++;
            q.solved = true;
            pin.classList.add("is-correct", "is-revealed");
            pz.focusRect((hs.x / 100) * w, (hs.y / 100) * h, (hs.w / 100) * w, (hs.h / 100) * h);
            statusEl.innerHTML = `<strong style="color:var(--accent)">✓ أحسنت! الموضع ${toArabicDigits(idx + 1)} هو «${escapeHtml(hs.name)}» — ${escapeHtml(hs.fact || q.sourceCitation)}</strong>`;
          } else {
            pin.classList.add("is-wrong");
            statusEl.innerHTML = `<span style="color:var(--danger)">الموضع ${toArabicDigits(idx + 1)} ليس «${escapeHtml(q.shortTitle)}» — حاول في موضع آخر أو اضغط «إظهار الحل».</span>`;
          }
          saveState({ quizProgress: this.progress });
        });
        overlay.appendChild(pin);
      });

      wrap.appendChild(overlay);
      world.innerHTML = "";
      world.appendChild(wrap);
      pz.setContentSize(w, h, page.rotated || 0);

      hideChk.addEventListener("change", () => {
        wrap.classList.toggle("blind-map-masked", hideChk.checked);
      });

      stage.querySelector("#mf-reveal").addEventListener("click", () => {
        q.solved = true;
        wrap.classList.remove("blind-map-masked");
        const targetHs = hotspots.find((x) => x.id === q.hotspotId);
        overlay.querySelectorAll(".blind-raster-pin").forEach((elPin) => {
          if (elPin.dataset.hsid === q.hotspotId) {
            elPin.classList.add("is-correct", "is-revealed");
          }
        });
        if (targetHs) {
          pz.focusRect((targetHs.x / 100) * w, (targetHs.y / 100) * h, (targetHs.w / 100) * w, (targetHs.h / 100) * h);
        }
        statusEl.innerHTML = `<strong>الموقع الصحيح: «${escapeHtml(q.shortTitle)}» — ${escapeHtml(q.fact || q.sourceCitation)}</strong>`;
      });
    }

    _renderFlashcards(stage) {
      const pool = this._getFilteredPool();
      const total = pool.length;
      if (!total) {
        stage.innerHTML = `<div class="quiz-card"><p style="margin:0">لا توجد بطاقات ضمن هذه التصفية.</p></div>`;
        return;
      }
      this.cardIdx = ((this.cardIdx % total) + total) % total;
      const card = pool[this.cardIdx];
      const inRev = this.reviewDeck.includes(card.id);

      stage.innerHTML = `
        <div class="quiz-card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <span class="badge badge-ocr">بطاقة ${toArabicDigits(this.cardIdx + 1)} من ${toArabicDigits(total)}</span>
            <button type="button" class="btn ${inRev ? "is-on" : ""}" id="fc-rev-btn">
              ${inRev ? "في قائمة المراجعة ★" : "حفظ للمراجعة ☆"}
            </button>
          </div>
          <div class="flashcard-box" id="fc-box" tabindex="0" role="button" aria-label="اقلب البطاقة">
            ${
              !this.cardFlipped
                ? `<div style="font-size:12px;color:var(--ink-muted);margin-bottom:8px">السؤال (انقر لقلب البطاقة وإظهار التوثيق)</div>
                   <div style="font-size:18px;font-weight:700;max-width:600px">${escapeHtml(card.prompt)}</div>`
                : `<div style="font-size:12px;color:var(--accent);font-weight:700;margin-bottom:8px">الإجابة الموثقة من الأطلس</div>
                   <div style="font-size:17px;font-weight:700;max-width:620px;margin-bottom:10px">${escapeHtml(card.answer)}</div>
                   <div style="font-size:12.5px;color:var(--ink-secondary)">المصدر: ${escapeHtml(card.sourceCitation)}</div>`
            }
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:14px;flex-wrap:wrap;gap:8px">
            <div style="display:flex;gap:8px">
              <button type="button" class="btn" id="fc-prev">→ السابقة</button>
              <button type="button" class="btn" id="fc-flip">قلب البطاقة</button>
              <button type="button" class="btn btn-primary" id="fc-next">التالية ←</button>
            </div>
            <button type="button" class="btn" id="fc-src">افتح الصفحة المصدر</button>
          </div>
        </div>
      `;

      const flip = () => {
        this.cardFlipped = !this.cardFlipped;
        this._renderFlashcards(stage);
      };
      stage.querySelector("#fc-box").addEventListener("click", flip);
      stage.querySelector("#fc-flip").addEventListener("click", flip);
      stage.querySelector("#fc-prev").addEventListener("click", () => {
        this.cardIdx--;
        this.cardFlipped = false;
        this._renderFlashcards(stage);
      });
      stage.querySelector("#fc-next").addEventListener("click", () => {
        this.cardIdx++;
        this.cardFlipped = false;
        this._renderFlashcards(stage);
      });
      stage.querySelector("#fc-rev-btn").addEventListener("click", () => {
        this.toggleReviewItem(card.id);
        this._renderFlashcards(stage);
      });
      stage.querySelector("#fc-src").addEventListener("click", () =>
        this.onJumpToSource(card.pageId, card.hotspotId || null)
      );
    }

    _renderReviewList(stage) {
      const items = this.questionPool.filter((q) => this.reviewDeck.includes(q.id));
      if (!items.length) {
        stage.innerHTML = `
          <div class="quiz-card" style="text-align:center;padding:36px">
            <h3 style="margin:0 0 8px 0">قائمة المراجعة فارغة حاليًا</h3>
            <p style="margin:0;color:var(--ink-secondary)">يمكنك إضافة أي سؤال أو بطاقة تعليمية إلى قائمة المراجعة بالضغط على «أضف للمراجعة ☆».</p>
          </div>`;
        return;
      }

      stage.innerHTML = `
        <div class="quiz-card">
          <h3 style="margin:0 0 12px 0">عناصر المراجعة المحفوظة (${toArabicDigits(items.length)})</h3>
          <div style="display:flex;flex-direction:column;gap:10px">
            ${items
              .map(
                (it) => `
              <div style="padding:12px;border:1px solid var(--border-subtle);border-radius:8px;background:var(--bg-elevated)">
                <div style="font-weight:700;margin-bottom:4px">${escapeHtml(it.prompt)}</div>
                <div style="color:var(--accent);font-size:13.5px;margin-bottom:4px">${escapeHtml(it.answer)}</div>
                <div style="display:flex;justify-content:space-between;align-items:center;font-size:12px;color:var(--ink-muted)">
                  <span>${escapeHtml(it.sourceCitation)}</span>
                  <div style="display:flex;gap:6px">
                    <button type="button" class="btn" data-jump="${it.pageId}">افتح المصدر</button>
                    <button type="button" class="btn" data-rm="${it.id}">إزالة</button>
                  </div>
                </div>
              </div>`
              )
              .join("")}
          </div>
        </div>
      `;

      stage.querySelectorAll("[data-jump]").forEach((b) =>
        b.addEventListener("click", () => this.onJumpToSource(b.getAttribute("data-jump")))
      );
      stage.querySelectorAll("[data-rm]").forEach((b) =>
        b.addEventListener("click", () => {
          this.toggleReviewItem(b.getAttribute("data-rm"));
          this.render();
        })
      );
    }
  }

  window.AtlasLearn = { LearningController };
})();
