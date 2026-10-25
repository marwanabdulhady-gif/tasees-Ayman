/* ===== learn.js — quizzes & flashcards generated ONLY from transcribed labels ===== */
"use strict";
const Learn = (() => {
  const POOL_KINDS = new Set(["place", "polity", "country", "region", "water", "river", "people"]);
  const MODES = {
    locate: { title: "أين تقع التسمية؟", desc: "يُعرض اسم من الخريطة، وعليك النقر على موضعه. يمكن إخفاء طبقة التسميات لزيادة الصعوبة (تبقى علامات المدن والسواحل ظاهرة)." },
    name: { title: "ما اسم هذا الموضع؟", desc: "تُبرز منطقة على الخريطة بعد إخفاء كل الكتابة، وتختار اسمها الصحيح من أربعة أسماء من الخريطة نفسها." },
    figure: { title: "في أي خريطة؟", desc: "يُعرض اسم ورد في خريطة واحدة فقط من خرائط الملف، وتختار الشكل الذي يتضمنه." },
    cards: { title: "بطاقات المراجعة", desc: "بطاقة تُبرز موضعًا على خريطة بلا كتابة؛ فكّر في الاسم ثم اكشفه، وقيّم نفسك. البطاقات التي تخطئ فيها تُضاف إلى قائمة المراجعة." },
  };
  let S = null;   // session
  let pz = null, view = null, viewFig = null;

  const progress = () => Store.get("learn", { stats: {}, review: [], answered: 0, correct: 0 });
  const saveProgress = (p) => Store.set("learn", p);
  function record(f, ok) {
    const p = progress();
    const st = p.stats[f.id] || { c: 0, w: 0 };
    ok ? st.c++ : st.w++;
    p.stats[f.id] = st; p.answered++; if (ok) p.correct++;
    p.review = p.review.filter((id) => id !== f.id);
    if (!ok || st.w > st.c) p.review.unshift(f.id);
    p.review = p.review.slice(0, 80);
    saveProgress(p);
  }

  function pool(scope) {
    return Atlas.features.filter((f) => POOL_KINDS.has(f.kind) && f.conf === "high" && (!scope || f.figure === scope));
  }
  const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
  function shuffle(a) { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }

  function init() {}
  function stop() { if (pz) { pz.destroy(); pz = null; } view = null; viewFig = null; S = null; }

  function show(r) {
    const mode = r.sub && MODES[r.sub] ? r.sub : null;
    if (!mode) { stop(); renderHome(); return; }
    S = { mode, scope: r.q.scope || "", hideLabels: r.q.hide === "1" || mode === "name" || mode === "cards", n: 0, score: 0, current: null, answered: false, onlyReview: r.q.review === "1" };
    renderStage();
    next();
  }

  /* ---------- home ---------- */
  function renderHome() {
    const body = $("#learn-body"); body.replaceChildren();
    const p = progress();
    const pct = p.answered ? Math.round((p.correct / p.answered) * 100) : 0;
    const scopeSel = h("select", { class: "input", style: "max-width:360px", "aria-label": "نطاق الأسئلة" }, h("option", { value: "" }, "كل الخرائط"), Atlas.figures.map((f) => h("option", { value: f.id }, `${Atlas.figLabel(f)}: ${Atlas.figTitle(f)}`)));
    const hide = h("label", { class: "check" }, h("input", { type: "checkbox", id: "learn-hide" }), "إخفاء طبقة التسميات في سؤال «أين تقع؟»");
    const url = (m, extra = "") => `#/learn/${m}?scope=${scopeSel.value}${m === "locate" && $("#learn-hide", body) && $("#learn-hide", body).checked ? "&hide=1" : ""}${extra}`;
    const cards = h("div", { class: "learn-grid" });
    for (const [k, m] of Object.entries(MODES)) {
      appendKids(cards, h("div", { class: "learn-card" }, h("h3", {}, m.title), h("p", {}, m.desc), h("button", { class: "btn primary", onclick: () => go(url(k)) }, "ابدأ")));
    }
    const reviewList = h("ul", { class: "chip-list" });
    for (const id of p.review.slice(0, 40)) { const f = Atlas.byId.get(id); if (f) appendKids(reviewList, h("li", {}, h("a", { href: `#/fig/${f.figure}/${f.id}` }, f.text))); }
    appendKids(body, 
      h("h1", {}, "التعلّم والمراجعة"),
      h("p", { class: "lead" }, "أنشطة تعليمية اختيارية مبنية حصرًا على التسميات المنسوخة من خرائط الملف (عالية الثقة فقط). لا تُضاف أي معلومات تاريخية أو جغرافية من خارج الأطلس، والتصحيح يعتمد على موضع التسمية المطبوعة في الخريطة."),
      h("div", { class: "info-block" }, h("div", { style: "display:flex;flex-wrap:wrap;gap:12px;align-items:center" }, scopeSel, hide)),
      cards,
      h("h2", {}, "التقدّم"),
      h("p", {}, `أجبت عن ${toArabicDigits(p.answered)} سؤالًا، الصحيح منها ${toArabicDigits(p.correct)} (${toArabicDigits(pct)}٪).`),
      h("div", { class: "progress", "aria-hidden": "true" }, h("i", { style: `width:${pct}%` })),
      h("h3", {}, `قائمة المراجعة (${toArabicDigits(p.review.length)})`),
      p.review.length ? reviewList : h("p", { class: "muted" }, "فارغة — تُضاف هنا الأسماء التي تخطئ فيها."),
      p.review.length ? h("div", { class: "btn-row" }, h("button", { class: "btn", onclick: () => go(`#/learn/locate?review=1`) }, "تدرّب على قائمة المراجعة")) : null,
      h("div", { class: "btn-row" },
        h("button", { class: "btn", onclick: () => { saveProgress({ stats: {}, review: [], answered: 0, correct: 0 }); renderHome(); toast("أعيد ضبط التقدّم"); } }, "إعادة ضبط التقدّم"),
        h("a", { class: "btn", href: "#/about" }, "تعطيل قسم التعلّم (وضع المرجع)")),
    );
  }

  /* ---------- stage ---------- */
  function renderStage() {
    const body = $("#learn-body"); body.replaceChildren();
    const m = MODES[S.mode];
    appendKids(body, 
      h("div", { style: "display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap" },
        h("h1", { style: "font-size:var(--fs-xl)" }, m.title),
        h("div", { class: "btn-row", style: "margin:0" }, h("span", { class: "badge", id: "learn-score" }, ""), h("a", { class: "btn", href: "#/learn" }, "إنهاء"))),
      h("div", { class: "quiz-stage" },
        h("div", { class: "quiz-map" }, h("div", { class: "pane-host", id: "learn-map", tabindex: "0", "aria-label": "خريطة السؤال" }), h("div", { class: "map-loading", id: "learn-loading", hidden: true }, h("span", { class: "spinner" }))),
        h("div", { class: "quiz-side", id: "learn-side", "aria-live": "polite" })),
      h("p", { class: "editorial", style: "margin-top:8px" }, "الأسئلة مولّدة آليًا من التسميات المنسوخة فقط. «الموضع الصحيح» هو موضع التسمية المطبوعة (أو علامتها النقطية) في الخريطة الأصلية."),
    );
    if (S.mode === "figure") $(".quiz-map", body).hidden = true, $(".quiz-stage", body).style.gridTemplateColumns = "1fr";
  }
  function scoreLine() { const el = $("#learn-score"); if (el) el.textContent = `السؤال ${toArabicDigits(S.n)} · الصحيح ${toArabicDigits(S.score)}`; }

  async function ensureMap(fig, hideLabels) {
    const host = $("#learn-map"); if (!host) return;
    if (!view || viewFig !== fig.id) {
      $("#learn-loading").hidden = false;
      const v = await MapView.spread(fig, { features: [] });
      if (!S) return;
      if (pz) pz.destroy();
      host.replaceChildren(v.svg); view = v; viewFig = fig.id;
      for (const t of v.svg.querySelectorAll("title")) t.remove();
      pz = new PanZoom(host, v.svg, { content: v.content, minWidth: 22, onTap: (t, ux, uy) => onMapTap(ux, uy) });
      $("#learn-loading").hidden = true;
    }
    const hidden = new Set(); if (hideLabels) hidden.add("label");
    MapView.setLayers(view.svg, hidden);
    view.hs.group.replaceChildren(); view.hs.sel.replaceChildren();
  }
  function drawTarget(f, cls) {
    const g = s("g", { class: `hs ${cls}` });
    if (f.spreadPoly) for (const ring of f.spreadPoly) g.appendChild(s("polygon", { class: "hs-shape", points: ring.map((p) => p.join(",")).join(" ") }));
    else for (const r of f.spreadRects) g.appendChild(s("rect", { class: "hs-shape", x: r[0] - 1.5, y: r[1] - 1.5, width: r[2] - r[0] + 3, height: r[3] - r[1] + 3, rx: 1.5 }));
    if (f.spreadMarker) g.appendChild(s("circle", { class: "sel-marker", cx: f.spreadMarker[0], cy: f.spreadMarker[1], r: 4.5 }));
    view.hs.group.appendChild(g);
  }

  function candidates() {
    let p = pool(S.scope);
    if (S.onlyReview) { const rv = new Set(progress().review); const q = p.filter((f) => rv.has(f.id)); if (q.length) p = q; }
    return p;
  }

  async function next() {
    if (!S) return;
    S.n++; S.answered = false; scoreLine();
    const side = $("#learn-side"); side.replaceChildren(h("p", { class: "muted" }, "…"));
    const p = candidates();
    if (S.mode === "figure") {
      const byNorm = new Map();
      for (const f of Atlas.features.filter((x) => POOL_KINDS.has(x.kind) && x.conf === "high")) { if (!byNorm.has(f.norm)) byNorm.set(f.norm, new Set()); byNorm.get(f.norm).add(f.figure); }
      const unique = p.filter((f) => byNorm.get(f.norm).size === 1);
      const f = pick(unique); S.current = f;
      side.replaceChildren(
        h("p", { class: "muted" }, "في أي شكل وردت التسمية التالية؟"),
        h("div", { class: "flashcard" }, f.text),
        choiceButtons(shuffle(Atlas.figures).map((fig) => ({ label: `${Atlas.figLabel(fig)}: ${Atlas.figTitle(fig)}`, ok: fig.id === f.figure })), f),
      );
      return;
    }
    const f = pick(p); S.current = f;
    const fig = Atlas.figure(f.figure);
    await ensureMap(fig, S.hideLabels);
    if (!S || S.current !== f) return;
    if (S.mode === "locate") {
      pz.fit(false);
      side.replaceChildren(
        h("p", { class: "muted" }, `${Atlas.figLabel(fig)}: ${Atlas.figTitle(fig)}`),
        h("p", { class: "q" }, "انقر على موضع:"),
        h("div", { class: "flashcard" }, f.text),
        h("p", { class: "muted" }, `النوع (تحريري): ${f.kindLabel}${S.hideLabels ? " — التسميات مخفية" : ""}`),
        h("div", { class: "btn-row" }, h("button", { class: "btn", onclick: () => reveal(false) }, "لا أعرف — أظهر الإجابة")),
      );
    } else if (S.mode === "name") {
      drawTarget(f, "quiz-target");
      pz.zoomToRect(Atlas.spreadBBox(f), { pad: 4, minW: 160, animate: false });
      const same = Atlas.featuresOf(f.figure).filter((x) => POOL_KINDS.has(x.kind) && x.norm !== f.norm && x.conf === "high");
      const pref = shuffle(same.filter((x) => x.kind === f.kind)), rest = shuffle(same.filter((x) => x.kind !== f.kind));
      const names = []; for (const x of [...pref, ...rest]) { if (!names.some((n) => n.norm === x.norm)) names.push(x); if (names.length === 3) break; }
      side.replaceChildren(
        h("p", { class: "muted" }, `${Atlas.figLabel(fig)}: ${Atlas.figTitle(fig)}`),
        h("p", { class: "q" }, "ما اسم الموضع المُبرَز (كما كُتب على الخريطة)؟"),
        choiceButtons(shuffle([{ label: f.text, ok: true }, ...names.map((x) => ({ label: x.text, ok: false }))]), f),
      );
    } else if (S.mode === "cards") {
      drawTarget(f, "quiz-target");
      pz.zoomToRect(Atlas.spreadBBox(f), { pad: 4, minW: 160, animate: false });
      const card = h("div", { class: "flashcard" }, "؟");
      const after = h("div", { class: "btn-row", hidden: true },
        h("button", { class: "btn primary", onclick: () => { record(f, true); S.score++; next(); } }, "عرفتها"),
        h("button", { class: "btn", onclick: () => { record(f, false); next(); } }, "أضفها للمراجعة"));
      side.replaceChildren(
        h("p", { class: "muted" }, `${Atlas.figLabel(fig)}: ${Atlas.figTitle(fig)}`),
        h("p", { class: "q" }, "ما الاسم المكتوب في هذا الموضع على الخريطة الأصلية؟"), card,
        h("div", { class: "btn-row" }, h("button", { class: "btn", onclick: (e) => { card.textContent = f.text; e.currentTarget.hidden = true; after.hidden = false; const hd = new Set(); MapView.setLayers(view.svg, hd); sourceLine(side, f); } }, "اكشف الاسم")), after);
    }
  }

  function choiceButtons(opts, f) {
    const wrap = h("div", { class: "choices" });
    for (const o of opts) {
      appendKids(wrap, h("button", { type: "button", onclick: (e) => {
        if (S.answered) return; S.answered = true;
        for (const b of wrap.children) { const ok = opts[[...wrap.children].indexOf(b)].ok; if (ok) b.classList.add("right"); }
        if (!o.ok) e.currentTarget.classList.add("wrong");
        finish(o.ok, f);
      } }, o.label));
    }
    return wrap;
  }

  function sourceLine(side, f) {
    appendKids(side, h("p", { class: "muted", html: `المصدر: الصفحة <bdi>${toArabicDigits(f.page)}</bdi> — <a href="#/fig/${f.figure}/${f.id}">افتح في المستكشف</a>` }));
  }

  function finish(ok, f, extra) {
    record(f, ok); if (ok) S.score++; scoreLine();
    const side = $("#learn-side");
    appendKids(side, h("p", { class: "feedback " + (ok ? "ok" : "bad") }, ok ? "إجابة صحيحة ✓" : `ليست صحيحة. الإجابة: «${f.text}»`));
    if (extra) appendKids(side, extra);
    sourceLine(side, f);
    if (view && S.mode !== "figure") { MapView.setLayers(view.svg, new Set()); view.hs.group.replaceChildren(); drawTarget(f, "quiz-correct"); }
    appendKids(side, h("div", { class: "btn-row" }, h("button", { class: "btn primary", onclick: next, id: "learn-next" }, "السؤال التالي")));
    const nb = $("#learn-next"); if (nb) nb.focus();
  }

  function reveal() {
    if (!S || S.answered) return; S.answered = true;
    const f = S.current; pz.zoomToRect(Atlas.spreadBBox(f), { pad: 3, minW: 140 });
    finish(false, f);
  }

  function onMapTap(ux, uy) {
    if (!S || S.mode !== "locate" || S.answered || !S.current) return;
    const f = S.current;
    const near = (feat) => feat.spreadRects.some((r) => ux >= r[0] - 5 && ux <= r[2] + 5 && uy >= r[1] - 5 && uy <= r[3] + 5) || (feat.spreadMarker && Math.hypot(ux - feat.spreadMarker[0], uy - feat.spreadMarker[1]) <= 9);
    // a click on another printed label with the same name also counts (e.g. repeated names)
    const ok = near(f) || Atlas.featuresOf(f.figure).some((x) => x.norm === f.norm && near(x));
    S.answered = true;
    view.hs.sel.replaceChildren(s("circle", { class: "quiz-click", cx: ux, cy: uy, r: 3.2 }));
    const bb = Atlas.spreadBBox(f);
    const d = Math.hypot(ux - (bb[0] + bb[2]) / 2, uy - (bb[1] + bb[3]) / 2);
    finish(ok, f, ok ? null : h("p", { class: "muted" }, `بعد نقرتك عن موضع التسمية: نحو ${toArabicDigits(Math.round(d))} نقطة على مقياس الصفحة.`));
    if (!ok) pz.zoomToRect([Math.min(bb[0], ux), Math.min(bb[1], uy), Math.max(bb[2], ux), Math.max(bb[3], uy)], { pad: 0.5, minW: 120 });
  }

  return { init, show, stop };
})();
