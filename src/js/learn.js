/* ==========================================================================
   learn.js — Module H: Verified Geographic & Historical Knowledge Discovery
   Questions are generated strictly from verified source data (NEVER raw OCR).
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

      const st = loadState();
      this.progress = st.quizProgress || { answered: 0, correct: 0 };
      this.reviewDeck = st.reviewDeck || []; // array of item ids
      this.mode = "mcq"; // mcq | map-find | flashcards | review
      this.cardFlipped = false;
      this.cardIdx = 0;

      this.questionPool = this._buildVerifiedPool();
      this.currentQuestion = null;
    }

    _buildVerifiedPool() {
      const pool = [];
      const maps8Vol = this.volById.get("maps8");

      // 1. Verified curated map hotspot facts from Seerah & Abu Bakr Atlases
      for (const p of this.manifest.pages) {
        const vol = this.volById.get(p.volumeId);
        for (const hs of p.hotspots || []) {
          if (hs.conf === "high" && hs.fact) {
            pool.push({
              id: `q-hs-${hs.id}`,
              kind: "hotspot-fact",
              prompt: `في خريطة «${p.title}»، ما الدلالة الجغرافية أو التاريخية لمعلم «${hs.name}»؟`,
              answer: hs.fact,
              shortTitle: hs.name,
              pageId: p.id,
              sourceCitation: `${vol.shortTitle} — ص ${toArabicDigits(p.sourcePage)} (${p.title})`,
              distractorGroup: "fact",
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

    _pickMcq() {
      const mcqItems = this.questionPool.filter((q) => q.kind === "hotspot-fact" || q.kind === "map-section");
      if (!mcqItems.length) return null;
      const item = mcqItems[Math.floor(Math.random() * mcqItems.length)];
      const sameGroup = mcqItems.filter((q) => q.distractorGroup === item.distractorGroup && q.answer !== item.answer);
      const shuffled = sameGroup.sort(() => Math.random() - 0.5).slice(0, 3).map((q) => q.answer);
      const options = [item.answer, ...shuffled].sort(() => Math.random() - 0.5);
      return { ...item, options, answered: false };
    }

    _pickMapChallenge() {
      const vecItems = this.questionPool.filter((q) => q.kind === "vector-loc");
      if (!vecItems.length) return null;
      return { ...vecItems[Math.floor(Math.random() * vecItems.length)], solved: false };
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

      this.container.innerHTML = `
        <div class="content-container">
          <div class="section-header-bar">
            <div>
              <h2 style="margin:0;font-size:18px">بيئة التعلّم واكتشاف المعرفة الجغرافية والتاريخية</h2>
              <p style="margin:4px 0 0 0;font-size:12.5px;color:var(--ink-secondary)">
                جميع الأسئلة والتحديات والبطاقات مولّدة حصريًا من البيانات المحققة في الأطالس الثلاثة مع توثيق الصفحة المصدر (لا يُستخدم نص OCR غير المراجع في توليد الأسئلة).
              </p>
            </div>
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
              <span class="badge badge-verified">الإجابات الصحيحة: ${toArabicDigits(this.progress.correct)} / ${toArabicDigits(this.progress.answered)} (${toArabicDigits(acc)}%)</span>
              <span class="badge badge-warn">قائمة المراجعة: ${toArabicDigits(this.reviewDeck.length)}</span>
            </div>
          </div>

          <div class="learn-grid">
            <aside style="display:flex;flex-direction:column;gap:8px">
              <button type="button" class="btn ${this.mode === "mcq" ? "btn-primary" : ""}" data-lmode="mcq" style="justify-content:flex-start;padding:10px 14px">
                ١. اختبارات الخرائط والمعالم الموثقة
              </button>
              <button type="button" class="btn ${this.mode === "map-find" ? "btn-primary" : ""}" data-lmode="map-find" style="justify-content:flex-start;padding:10px 14px">
                ٢. تحدي تحديد الموقع على الخريطة الصماء
              </button>
              <button type="button" class="btn ${this.mode === "flashcards" ? "btn-primary" : ""}" data-lmode="flashcards" style="justify-content:flex-start;padding:10px 14px">
                ٣. البطاقات التعليمية الذكية (${toArabicDigits(this.questionPool.length)})
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
      if (!this.currentQuestion || this.currentQuestion.kind === "vector-loc") {
        this.currentQuestion = this._pickMcq();
      }
      const q = this.currentQuestion;
      if (!q) return;
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
                <strong>${ok ? "إجابة صحيحة!" : "الإجابة الصحيحة موثقة في المصدر:"}</strong>
                <div style="font-size:12.5px;color:var(--ink-secondary);margin-top:3px">المصدر: ${escapeHtml(q.sourceCitation)}</div>
              </div>
              <div style="display:flex;gap:8px">
                <button type="button" class="btn" id="q-open-src">افتح الصفحة المصدر للتحقق</button>
                <button type="button" class="btn btn-primary" id="q-next-btn">السؤال التالي ←</button>
              </div>
            </div>
          `;
          fb.querySelector("#q-open-src").addEventListener("click", () => this.onJumpToSource(q.pageId));
          fb.querySelector("#q-next-btn").addEventListener("click", () => {
            this.currentQuestion = this._pickMcq();
            this.render();
          });
        });
      });
    }

    async _renderMapFind(stage) {
      if (!this.currentQuestion || this.currentQuestion.kind !== "vector-loc") {
        this.currentQuestion = this._pickMapChallenge();
      }
      const q = this.currentQuestion;
      if (!q) return;

      stage.innerHTML = `
        <div class="quiz-card">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px">
            <div>
              <span class="badge badge-verified">تحدي الخريطة التفاعلي</span>
              <h3 style="margin:6px 0 0 0;font-size:16px">${escapeHtml(q.prompt)}</h3>
            </div>
            <div style="display:flex;gap:6px">
              <label style="font-size:12px;display:inline-flex;align-items:center;gap:5px">
                <input type="checkbox" id="mf-hide-lbl" checked /> إخفاء طبقة التسميات (خريطة صمّاء)
              </label>
              <button type="button" class="btn" id="mf-reveal">إظهار الحل</button>
              <button type="button" class="btn btn-primary" id="mf-next">تحدٍّ جديد ←</button>
            </div>
          </div>
          <div id="mf-status" style="font-size:13px;margin-bottom:8px;color:var(--ink-secondary)">
            انقر على الموقع الصحيح فوق الخريطة (يمكنك التكبير والتحريك بحرية).
          </div>
          <div class="map-viewport" id="mf-vp" style="height:460px;border-radius:10px;border:1px solid var(--border-strong)">
            <div class="panzoom-world" id="mf-world"></div>
          </div>
        </div>
      `;

      const vp = stage.querySelector("#mf-vp");
      const world = stage.querySelector("#mf-world");
      const statusEl = stage.querySelector("#mf-status");
      const hideChk = stage.querySelector("#mf-hide-lbl");

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
            statusEl.innerHTML = `<strong style="color:var(--accent)">أحسنت! هذا موضع «${escapeHtml(ft.text)}» (${escapeHtml(q.sourceCitation)}).</strong>`;
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

      stage.querySelector("#mf-next").addEventListener("click", () => {
        this.currentQuestion = this._pickMapChallenge();
        this.render();
      });
    }

    _renderFlashcards(stage) {
      const total = this.questionPool.length;
      if (!total) return;
      this.cardIdx = ((this.cardIdx % total) + total) % total;
      const card = this.questionPool[this.cardIdx];
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
      stage.querySelector("#fc-src").addEventListener("click", () => this.onJumpToSource(card.pageId));
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
