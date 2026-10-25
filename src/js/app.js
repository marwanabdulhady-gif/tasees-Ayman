/* ===== app.js — atlas data model, routing and UI modules ===== */
"use strict";

/* ------------------------------------------------------------------ */
/*  Data model                                                         */
/* ------------------------------------------------------------------ */
const Atlas = {
  init(d) {
    this.d = d;
    this.figures = d.figures;
    this.pages = d.pages;
    this.features = d.features;
    this.composites = d.composites || [];
    this.byId = new Map(this.features.map((f) => [f.id, f]));
    this.figById = new Map(this.figures.map((f) => [f.id, f]));
    this.kinds = d.kinds;
    this.conf = d.confidence;
  },
  figure(id) { return this.figById.get(id); },
  page(n) { return this.pages[n - 1]; },
  featuresOf(figId) { return this.features.filter((f) => f.figure === figId); },
  featuresOnPage(n) { return this.features.filter((f) => f.page === n); },
  spreadBBox(f) { const r = f.spreadRects; return [Math.min(...r.map((x) => x[0])), Math.min(...r.map((x) => x[1])), Math.max(...r.map((x) => x[2])), Math.max(...r.map((x) => x[3]))]; },
  figLabel(fig) { return fig.number ? `شكل ${fig.number}` : fig.id; },
  figTitle(fig) { return fig.title || fig.caption || ""; },
  halfLabel(f) { return f.half === "east" ? "النصف الشرقي" : "النصف الغربي"; },
  isMapFeature(f) { return f.kind !== "caption"; },
};

/* ------------------------------------------------------------------ */
/*  App state                                                          */
/* ------------------------------------------------------------------ */
const State = {
  route: null,
  fig: null,
  view: null,          // MapView result for explorer
  pz: null,            // PanZoom for explorer
  selected: null,
  hiddenLayers: new Set(Store.get("hiddenLayers", [])),
  showHs: Store.get("showHotspots", false),
  kindFilter: null,
  tocMode: Store.get("tocMode", "list"),
  settings: Object.assign({ referenceOnly: false }, Store.get("settings", {})),
  page: { n: 1, mode: "raster", hs: false, panes: [] },
  compare: { a: "fig-1-1", b: "fig-1-4", mode: "side", sync: true, panes: [] },
  buildToken: 0,
};

/* ------------------------------------------------------------------ */
/*  Bookmarks / recent                                                 */
/* ------------------------------------------------------------------ */
const Saved = {
  list() { return Store.get("bookmarks", []); },
  has(type, id) { return this.list().some((b) => b.type === type && b.id === id); },
  toggle(type, id) {
    let l = this.list();
    if (this.has(type, id)) l = l.filter((b) => !(b.type === type && b.id === id)); else l.unshift({ type, id });
    Store.set("bookmarks", l.slice(0, 60)); renderSavedLists(); return this.has(type, id);
  },
  recent() { return Store.get("recent", []); },
  pushRecent(type, id) {
    const l = this.recent().filter((b) => !(b.type === type && b.id === id));
    l.unshift({ type, id }); Store.set("recent", l.slice(0, 10)); renderSavedLists();
  },
};
function savedLink(b) {
  if (b.type === "fig") { const f = Atlas.figure(b.id); if (!f) return null; return h("a", { href: `#/fig/${f.id}` }, Atlas.figLabel(f)); }
  if (b.type === "feature") { const f = Atlas.byId.get(b.id); if (!f) return null; return h("a", { href: `#/fig/${f.figure}/${f.id}`, title: `${f.kindLabel} — ص ${toArabicDigits(f.page)}` }, f.text); }
  if (b.type === "page") return h("a", { href: `#/page/${b.id}` }, `ص ${toArabicDigits(b.id)}`);
  return null;
}
function renderSavedLists() {
  const fill = (ul, items, empty) => {
    ul.replaceChildren();
    const links = items.map(savedLink).filter(Boolean);
    if (!links.length) appendKids(ul, h("li", { class: "muted" }, empty));
    for (const a of links) appendKids(ul, h("li", {}, a));
  };
  fill($("#bookmark-list"), Saved.list(), "لا توجد عناصر محفوظة بعد. استخدم زر «حفظ» في بطاقة المعلم أو الشكل.");
  fill($("#recent-list"), Saved.recent(), "—");
}

/* ------------------------------------------------------------------ */
/*  Routing                                                            */
/* ------------------------------------------------------------------ */
function parseRoute() {
  const raw = decodeURIComponent(location.hash.replace(/^#\/?/, ""));
  const [path, query] = raw.split("?");
  const parts = path.split("/").filter(Boolean);
  const q = Object.fromEntries(new URLSearchParams(query || ""));
  if (!parts.length) return { view: "explore", fig: null, q };
  if (parts[0] === "fig") return { view: "explore", fig: parts[1], feature: parts[2] || null, q };
  if (parts[0] === "page") return { view: "page", page: Math.min(8, Math.max(1, parseInt(parts[1], 10) || 1)), feature: parts[2] || null, q };
  if (["compare", "index", "learn", "about"].includes(parts[0])) return { view: parts[0], q, sub: parts[1] };
  return { view: "explore", fig: null, q };
}
function go(hash) { if (location.hash === hash) onRoute(); else location.hash = hash; }

async function onRoute() {
  const r = parseRoute(); State.route = r;
  document.body.dataset.view = r.view;
  if (r.view === "learn" && State.settings.referenceOnly) { go("#/about"); return; }
  for (const v of $$(".view")) v.hidden = v.dataset.view !== r.view;
  for (const a of $$("[data-nav]")) {
    const on = a.dataset.nav === r.view;
    if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  }
  closePanels();
  hideTooltip();
  if (r.view !== "learn" && window.Learn) Learn.stop();
  if (r.view === "explore") await showExplore(r);
  else if (r.view === "page") await showPage(r);
  else if (r.view === "compare") await showCompare(r);
  else if (r.view === "index") showIndex(r);
  else if (r.view === "learn") Learn.show(r);
  else if (r.view === "about") showAbout();
  if (r.view !== "explore" && r.view !== "page") renderInfoGeneric(r.view);
}

/* ------------------------------------------------------------------ */
/*  Explorer                                                           */
/* ------------------------------------------------------------------ */
async function showExplore(r) {
  const figId = r.fig && Atlas.figure(r.fig) ? r.fig : (State.fig ? State.fig.id : Store.get("lastFig", Atlas.figures[0].id));
  const fig = Atlas.figure(figId) || Atlas.figures[0];
  if (!State.fig || State.fig.id !== fig.id || !State.view) await loadFigure(fig);
  renderFigInfo();
  const f = r.feature ? Atlas.byId.get(r.feature) : null;
  if (f && f.figure === fig.id) selectFeature(f, { zoom: true, push: false });
  else if (!r.feature) selectFeature(null, { push: false });
}

async function loadFigure(fig) {
  const token = ++State.buildToken;
  State.fig = fig; State.selected = null; State.kindFilter = null;
  Store.set("lastFig", fig.id);
  Saved.pushRecent("fig", fig.id);
  $("#fig-badge").textContent = Atlas.figLabel(fig);
  $("#fig-title").textContent = Atlas.figTitle(fig);
  $("#fig-sub").innerHTML = `خريطة مركّبة من صفحتين متقابلتين في ملف PDF: الصفحة <bdi>${toArabicDigits(fig.westPage)}</bdi> (النصف الغربي) والصفحة <bdi>${toArabicDigits(fig.eastPage)}</bdi> (النصف الشرقي) — وُصِلتا بإزاحة مقيسة من الرسومات المتجهية نفسها.`;
  renderFigStrip(); renderToc();
  const host = $("#viewer-host");
  $("#map-loading").hidden = false;
  const view = await MapView.spread(fig);
  if (token !== State.buildToken) return;
  if (State.pz) State.pz.destroy();
  host.replaceChildren(view.svg);
  State.view = view;
  MapView.setLayers(view.svg, State.hiddenLayers);
  view.svg.classList.toggle("show-hs", State.showHs);
  State.pz = new PanZoom(host, view.svg, {
    content: view.content, minWidth: 22, readout: $("#zoom-readout"),
    onTap: (target) => {
      const g = target && target.closest && target.closest(".hs");
      if (g) selectFeature(Atlas.byId.get(g.dataset.id), { zoom: false });
    },
    onHover: (e) => hoverTooltip(e, $("#viewer-host")),
  });
  $("#map-loading").hidden = true;
  if (!view.vector) toast("تعذّر تحميل الرسومات المتجهية؛ تُعرض الصور النقطية الأصلية بدلًا منها (الطبقات غير متاحة).", 5000);
  renderLayersPop();
}

function selectFeature(f, { zoom = true, push = true } = {}) {
  State.selected = f || null;
  if (State.view) MapView.select(State.view, f);
  renderFeatureCard(f);
  if (f) {
    Saved.pushRecent("feature", f.id);
    if (zoom && State.pz) State.pz.zoomToRect(Atlas.spreadBBox(f), { pad: 1.6, minW: 90 });
    if (push) history.replaceState(null, "", `#/fig/${f.figure}/${f.id}`);
    if (window.innerWidth <= 820) openPanel("panel-info", true);
    for (const b of $$("#feature-list button")) b.setAttribute("aria-current", b.dataset.id === f.id ? "true" : "false");
  } else if (push && State.fig) history.replaceState(null, "", `#/fig/${State.fig.id}`);
}

function renderFigStrip() {
  const strip = $("#fig-strip"); strip.replaceChildren();
  for (const fig of Atlas.figures) {
    appendKids(strip, h("button", {
      class: "strip-btn", role: "tab", "aria-selected": String(State.fig && State.fig.id === fig.id),
      onclick: () => go(`#/fig/${fig.id}`), title: fig.caption,
    }, h("img", { src: Assets.thumb(fig.id), alt: "" }), h("span", {}, `${Atlas.figLabel(fig)}: ${Atlas.figTitle(fig)}`)));
  }
}

function kindCounts(feats) {
  const c = {};
  for (const f of feats) if (Atlas.isMapFeature(f) && f.kind !== "legend") c[f.kind] = (c[f.kind] || 0) + 1;
  return Object.entries(c).sort((a, b) => b[1] - a[1]);
}

function applyKindFilter() {
  const svg = State.view && State.view.svg; if (!svg) return;
  svg.classList.toggle("filtering", !!State.kindFilter);
  for (const g of svg.querySelectorAll(".hs")) {
    const f = Atlas.byId.get(g.dataset.id);
    g.classList.toggle("match", !!State.kindFilter && f && f.kind === State.kindFilter);
  }
  for (const b of $$(".kind-bar")) b.setAttribute("aria-pressed", String(b.dataset.kind === State.kindFilter));
}

function renderFigInfo() {
  const fig = State.fig; if (!fig) return;
  $("#info-heading").textContent = "معلومات الخريطة";
  const feats = Atlas.featuresOf(fig.id);
  const mapFeats = feats.filter((f) => Atlas.isMapFeature(f) && f.kind !== "legend");
  const counts = kindCounts(feats); const max = Math.max(1, ...counts.map((c) => c[1]));
  const low = feats.filter((f) => f.conf === "low" || f.kind === "unreadable");
  const med = feats.filter((f) => f.conf === "medium");
  const body = $("#info-body"); body.replaceChildren();
  const saved = Saved.has("fig", fig.id);

  appendKids(body, h("section", { class: "info-block" },
    h("h3", {}, "تعليق الشكل كما ورد في الملف"),
    h("p", { class: "caption-quote" }, fig.caption || "—"),
    h("p", { class: "source-line", html: `التعليق مطبوع أسفل الصفحة <bdi>${toArabicDigits(fig.captionPage)}</bdi>. الشكل يمتد على الصفحتين <bdi>${toArabicDigits(fig.westPage)}</bdi> و<bdi>${toArabicDigits(fig.eastPage)}</bdi>.` }),
    h("div", { class: "btn-row" },
      h("a", { class: "btn", href: `#/page/${fig.westPage}` }, `الصفحة ${toArabicDigits(fig.westPage)} الأصلية`),
      h("a", { class: "btn", href: `#/page/${fig.eastPage}` }, `الصفحة ${toArabicDigits(fig.eastPage)} الأصلية`),
      h("button", { class: "btn", "aria-pressed": String(saved), onclick: (e) => { const on = Saved.toggle("fig", fig.id); e.currentTarget.setAttribute("aria-pressed", String(on)); e.currentTarget.textContent = on ? "محفوظ ✓" : "حفظ الشكل"; } }, saved ? "محفوظ ✓" : "حفظ الشكل"),
    ),
  ));

  const legendBlock = h("section", { class: "info-block" }, h("h3", {}, "مفتاح الخريطة والرموز"));
  if (fig.legend && fig.legend.length) {
    for (const lg of fig.legend) appendKids(legendBlock, h("div", { class: "legend-item" }, h("span", { class: "legend-swatch", "aria-hidden": "true" }), h("div", {}, h("strong", {}, lg.text), h("div", { class: "muted" }, "رمز مطبوع في مفتاح الخريطة (مربع منقط). يقابله على الخريطة كل المساحات المنقطة، ويمكن إظهارها أو إخفاؤها من طبقة «المنطقة الفاصلة»."))));
  } else {
    appendKids(legendBlock, h("p", { class: "muted" }, "لا يتضمن هذا الشكل مفتاحًا للرموز في الملف الأصلي."));
  }
  if (fig.layers.extent) appendKids(legendBlock, h("p", { class: "note" }, "يظهر في الخريطة خط أسود عريض (طبقة «خط الامتداد»). لا يشرح الملف معنى هذا الخط، لذلك لا يقدّم الأطلس تفسيرًا له."));
  if (fig.layers.border && !fig.legend.length) appendKids(legendBlock, h("p", { class: "muted" }, "الخطوط الرمادية الرفيعة تمثل الحدود المرسومة على الخريطة."));
  appendKids(body, legendBlock);

  const bars = h("div", { class: "kind-bars", role: "group", "aria-label": "تصفية المعالم حسب النوع" });
  for (const [k, n] of counts) {
    appendKids(bars, h("button", { class: "kind-bar", "data-kind": k, "aria-pressed": "false", onclick: () => { State.kindFilter = State.kindFilter === k ? null : k; applyKindFilter(); } },
      h("span", {}, Atlas.kinds[k]), h("span", { class: "bar" }, h("i", { style: `width:${(n / max) * 100}%` })), h("span", { class: "num" }, toArabicDigits(n))));
  }
  appendKids(body, h("section", { class: "info-block" },
    h("h3", {}, `التسميات المنسوخة (${toArabicDigits(mapFeats.length)})`),
    bars,
    h("p", { class: "editorial" }, "التصنيف تحريري مبني على صياغة التسمية ورمزها (خط عريض، علامة نقطية)، وليس جزءًا من الملف. انقر نوعًا لتمييزه على الخريطة."),
  ));

  const list = h("ul", { class: "feature-list", id: "feature-list", "aria-label": "قائمة المعالم في هذا الشكل" });
  const filterInput = h("input", { class: "input", type: "search", placeholder: "تصفية القائمة…", "aria-label": "تصفية قائمة المعالم", style: "margin-bottom:6px" });
  const fillList = () => {
    const q = normalize(filterInput.value);
    list.replaceChildren();
    const items = mapFeats.filter((f) => !q || f.norm.includes(q)).sort((a, b) => a.text.localeCompare(b.text, "ar"));
    for (const f of items) appendKids(list, h("li", {}, h("button", { "data-id": f.id, onclick: () => selectFeature(f) }, h("span", { html: highlight(f.text, q) }), h("small", {}, `${f.kindLabel} · ص ${toArabicDigits(f.page)}`))));
    if (!items.length) appendKids(list, h("li", { class: "empty" }, "لا توجد نتائج."));
  };
  filterInput.addEventListener("input", debounce(fillList, 100));
  fillList();
  appendKids(body, h("section", { class: "info-block" }, h("h3", {}, "قائمة المعالم (بديل نصي للخريطة)"), filterInput, list));

  const ver = h("section", { class: "info-block" }, h("h3", {}, "التحقق والدقة"),
    h("p", { class: "muted" }, `لا يحتوي الملف على طبقة نصية؛ نُسخت التسميات بصريًا وربطت كل تسمية بحدود حروفها المتجهية في الصفحة. ثقة متوسطة: ${toArabicDigits(med.length)} — منخفضة/غير مقروءة: ${toArabicDigits(low.length)}.`));
  if (low.length) {
    const ul = h("ul", { class: "chip-list" });
    for (const f of low) appendKids(ul, h("li", {}, h("button", { class: "chip", onclick: () => selectFeature(f) }, f.text)));
    appendKids(ver, h("p", { class: "muted" }, "عناصر تحتاج إلى مراجعة يدوية:"), ul);
  }
  appendKids(ver, h("a", { class: "btn", href: "#/about" }, "تقرير التدقيق الكامل"));
  appendKids(body, ver);
  applyKindFilter();
}

function cropPreview(f) {
  const r = f.bbox; const pad = 10;
  const x = r[0] - pad, y = r[1] - pad, w = r[2] - r[0] + 2 * pad, hh = r[3] - r[1] + 2 * pad;
  const svg = s("svg", { viewBox: `${x} ${y} ${w} ${hh}`, preserveAspectRatio: "xMidYMid meet", role: "img", "aria-label": `مقتطف من الصفحة الأصلية ${f.page}` });
  svg.appendChild(s("image", { href: Assets.pageImage(f.page), x: 0, y: 0, width: 595, height: 842, preserveAspectRatio: "none" }));
  const rects = f.poly ? null : f.rects;
  if (rects) for (const q of rects) svg.appendChild(s("rect", { x: q[0] - 0.8, y: q[1] - 0.8, width: q[2] - q[0] + 1.6, height: q[3] - q[1] + 1.6, fill: "none", stroke: "#c2410c", "stroke-width": 0.6 }));
  else for (const ring of f.poly) svg.appendChild(s("polygon", { points: ring.map((p) => p.join(",")).join(" "), fill: "none", stroke: "#c2410c", "stroke-width": 0.6 }));
  return h("div", { class: "crop" }, svg);
}

function geometryLabel(src) {
  return { "glyph-clusters": "حدود الحروف المتجهية للتسمية (مستخرجة آليًا)", "snapped-approx": "حدود الحروف المتجهية (بعد مطابقة يدوية للموضع)", "manual-polygon": "منطقة مرسومة يدويًا لتداخل التسميات" }[src] || src;
}

function renderFeatureCard(f, container = $("#feature-card")) {
  if (!f) { container.hidden = true; container.replaceChildren(); return; }
  container.hidden = false; container.replaceChildren();
  const fig = Atlas.figure(f.figure);
  const saved = Saved.has("feature", f.id);
  const occ = (f.sameName || []).map((id) => Atlas.byId.get(id)).filter(Boolean);
  const comp = Atlas.composites.find((c) => c.parts.includes(f.id));
  appendKids(container, 
    h("div", { class: "fc-top" },
      h("div", {}, h("div", { class: "muted" }, "المعلم المحدد"), h("h3", {}, f.text)),
      h("button", { class: "icon-btn", "aria-label": "إلغاء التحديد", onclick: () => selectFeature(null) }, "×")),
    h("div", { class: "fc-kind" },
      h("span", { class: "badge", title: "تصنيف تحريري" }, f.kindLabel),
      h("span", { class: `badge conf-${f.conf}` }, `ثقة النسخ: ${Atlas.conf[f.conf]}`),
      f.bold ? h("span", { class: "badge" }, "خط عريض في الأصل") : null,
      f.marker ? h("span", { class: "badge" }, "مقرون بعلامة نقطية") : null),
    h("dl", { class: "kv" },
      h("dt", {}, "الشكل"), h("dd", {}, `${Atlas.figLabel(fig)}: ${Atlas.figTitle(fig)}`),
      h("dt", {}, "المصدر"), h("dd", { html: `ملف PDF، الصفحة <bdi>${toArabicDigits(f.page)}</bdi> (${Atlas.halfLabel(f)})` }),
      h("dt", {}, "منطقة التفاعل"), h("dd", {}, geometryLabel(f.geometrySource)),
      h("dt", {}, "المعرّف"), h("dd", {}, h("bdi", { class: "ltr" }, f.id))),
    f.note ? h("p", { class: "note" }, f.note) : null,
    f.crossPage ? h("p", { class: "note" }, f.crossPage) : null,
    comp ? h("p", { class: "note" }, `${comp.note}: «${comp.text}».`) : null,
    h("div", { class: "muted", style: "margin-top:8px" }, "المقتطف من الصورة الأصلية للصفحة:"),
    cropPreview(f),
  );
  if (occ.length) {
    const ul = h("ul", { class: "occ" });
    for (const o of occ) {
      const of = Atlas.figure(o.figure);
      appendKids(ul, h("li", {}, h("button", { onclick: () => go(`#/fig/${o.figure}/${o.id}`) }, `«${o.text}» — ${Atlas.figLabel(of)}: ${Atlas.figTitle(of)} · ص ${toArabicDigits(o.page)}`)));
    }
    appendKids(container, h("div", { class: "muted", style: "margin-top:10px" }, `ورد الاسم نفسه (بعد التطبيع) في ${toArabicDigits(occ.length)} موضع آخر:`), ul);
  }
  appendKids(container, h("div", { class: "btn-row" },
    h("button", { class: "btn primary", onclick: () => { if (State.route.view !== "explore") go(`#/fig/${f.figure}/${f.id}`); else State.pz.zoomToRect(Atlas.spreadBBox(f), { pad: 1.6, minW: 90 }); } }, "تكبير إلى المعلم"),
    h("a", { class: "btn", href: `#/page/${f.page}/${f.id}` }, "في الصفحة الأصلية"),
    h("button", { class: "btn", "aria-pressed": String(saved), onclick: (e) => { const on = Saved.toggle("feature", f.id); e.currentTarget.setAttribute("aria-pressed", String(on)); e.currentTarget.textContent = on ? "محفوظ ✓" : "حفظ"; } }, saved ? "محفوظ ✓" : "حفظ"),
    h("button", { class: "btn", onclick: () => { (navigator.clipboard ? navigator.clipboard.writeText(f.text) : Promise.reject()).then(() => toast("نُسخ الاسم")).catch(() => toast("تعذّر النسخ")); } }, "نسخ الاسم"),
  ));
}

/* tooltip */
function hoverTooltip(e, host) {
  const tip = $("#tooltip");
  if (!e) { hideTooltip(); return; }
  const g = e.target && e.target.closest && e.target.closest(".hs");
  for (const x of host.querySelectorAll(".hs.hover")) if (x !== g) x.classList.remove("hover");
  if (!g) { tip.hidden = true; return; }
  g.classList.add("hover");
  const f = Atlas.byId.get(g.dataset.id); if (!f) return;
  const wrap = host.parentElement.getBoundingClientRect();
  tip.innerHTML = `${esc(f.text)}<small>${esc(f.kindLabel)} · ص ${toArabicDigits(f.page)}${f.conf !== "high" ? " · ثقة " + esc(Atlas.conf[f.conf]) : ""}</small>`;
  tip.hidden = false;
  let x = e.clientX - wrap.left + 14, y = e.clientY - wrap.top + 16;
  const tw = tip.offsetWidth, th = tip.offsetHeight;
  if (x + tw > wrap.width - 6) x = e.clientX - wrap.left - tw - 14;
  if (y + th > wrap.height - 6) y = e.clientY - wrap.top - th - 12;
  tip.style.left = Math.max(4, x) + "px"; tip.style.top = Math.max(4, y) + "px";
}
function hideTooltip() { const t = $("#tooltip"); if (t) t.hidden = true; }

/* layers popover */
function renderLayersPop() {
  const pop = $("#layers-pop"); const fig = State.fig; if (!fig) return;
  pop.replaceChildren(h("h3", {}, "طبقات الخريطة"),
    h("p", {}, "طبقات مفصولة فعليًا من رسومات ملف PDF المتجهية حسب خصائص الرسم (لون التعبئة، سماكة الخط، الشكل). تظهر فقط الطبقات الموجودة في هذا الشكل."));
  const L = Atlas.d.layers;
  const sw = { base: "linear-gradient(90deg,#cfd0d3 50%,#fff 50%)", border: "linear-gradient(transparent 45%,#6d6e71 45% 60%,transparent 60%)", buffer: "radial-gradient(#4b4c4d 1px,transparent 1.3px) 0 0/5px 5px", extent: "linear-gradient(transparent 38%,#222 38% 66%,transparent 66%)", marker: "radial-gradient(#222 3px,transparent 3.5px)", label: "none" };
  const counts = fig.layers;
  for (const k of ["label", "marker", "border", "buffer", "extent", "base"]) {
    const n = (counts[k] || 0) + (k === "buffer" ? (counts.buffer_images || 0) : 0);
    if (!n) continue;
    const id = "layer-" + k;
    const cb = h("input", { type: "checkbox", id, checked: !State.hiddenLayers.has(k) });
    cb.addEventListener("change", () => {
      if (cb.checked) State.hiddenLayers.delete(k); else State.hiddenLayers.add(k);
      Store.set("hiddenLayers", [...State.hiddenLayers]);
      if (State.view) MapView.setLayers(State.view.svg, State.hiddenLayers);
    });
    pop.append(h("div", { class: "layer-row" }, cb,
      h("label", { for: id }, L[k], h("small", {}, `${toArabicDigits(n)} عنصرًا مرسومًا`)),
      h("span", { class: "layer-swatch", style: `background:${sw[k]};${k === "label" ? "display:grid;place-items:center;font-weight:700;font-size:11px" : ""}` }, k === "label" ? "أب" : "")));
  }
  pop.append(h("p", { style: "margin-top:8px" }, "إخفاء طبقة التسميات يُظهر الخريطة دون كتابة، مع بقاء مناطق التفاعل قابلة للنقر."));
}

/* ------------------------------------------------------------------ */
/*  Original page viewer                                               */
/* ------------------------------------------------------------------ */
async function showPage(r) {
  State.page.n = r.page;
  Saved.pushRecent("page", r.page);
  const pg = Atlas.page(r.page); const fig = Atlas.figure(pg.figure);
  $("#page-badge").textContent = `الصفحة ${toArabicDigits(r.page)} من ${toArabicDigits(8)}`;
  $("#page-title").textContent = `${Atlas.figLabel(fig)} — ${pg.halfLabel}`;
  for (const b of $$("[data-pagemode]")) b.setAttribute("aria-pressed", String(b.dataset.pagemode === State.page.mode));
  $("#page-hotspots").checked = State.page.hs || !!r.feature;
  State.page.hs = $("#page-hotspots").checked;
  renderPageStrip();
  await buildPagePanes();
  renderPageInfo(pg, fig);
  if (r.feature) {
    const f = Atlas.byId.get(r.feature);
    if (f && f.page === r.page) {
      for (const p of State.page.panes) { MapView.select(p.view, f); p.pz.zoomToRect(f.bbox, { pad: 2, minW: 80 }); }
      renderFeatureCard(f);
    }
  } else renderFeatureCard(null);
}

async function buildPagePanes() {
  const token = ++State.buildToken;
  const host = $("#page-panes");
  for (const p of State.page.panes) p.pz.destroy();
  State.page.panes = [];
  const modes = State.page.mode === "side" ? ["raster", "vector"] : [State.page.mode];
  host.classList.toggle("two", modes.length === 2);
  host.replaceChildren();
  const built = await Promise.all(modes.map((m) => MapView.page(State.page.n, { mode: m, hotspots: State.page.hs })));
  if (token !== State.buildToken) return;
  built.forEach((view, i) => {
    const pane = h("div", { class: "pane" });
    const ph = h("div", { class: "pane-host", tabindex: "0", "aria-label": view.svg.getAttribute("aria-label") });
    appendKids(pane, ph, h("div", { class: "pane-label" }, modes[i] === "raster" ? "صورة الصفحة الأصلية (مستخرجة من PDF)" : (view.vector ? "الرسومات المتجهية للصفحة" : "صورة (المتجهي غير متاح)")));
    appendKids(host, pane); ph.append(view.svg);
    view.svg.classList.add("show-hs");
    const pz = new PanZoom(ph, view.svg, {
      content: view.content, minWidth: 18,
      onTap: (target) => { const g = target && target.closest && target.closest(".hs"); if (g) { const f = Atlas.byId.get(g.dataset.id); for (const p of State.page.panes) MapView.select(p.view, f); renderFeatureCard(f); if (window.innerWidth <= 820) openPanel("panel-info", true); } },
      onHover: (e) => hoverTooltip(e, ph),
      onChange: (v) => { if (State.page.panes.length === 2) for (const o of State.page.panes) if (o.pz !== pz) o.pz.setView(v, { silent: true }); },
    });
    State.page.panes.push({ view, pz });
  });
}

function renderPageStrip() {
  const strip = $("#page-strip"); strip.replaceChildren();
  for (const pg of Atlas.pages) {
    const fig = Atlas.figure(pg.figure);
    appendKids(strip, h("button", { class: "strip-btn", role: "tab", "aria-selected": String(pg.page === State.page.n), onclick: () => go(`#/page/${pg.page}`), title: `${Atlas.figLabel(fig)} — ${pg.halfLabel}` },
      h("img", { src: Assets.thumb(`page-${String(pg.page).padStart(3, "0")}`), alt: "" }), h("span", {}, `ص ${toArabicDigits(pg.page)} · ${Atlas.figLabel(fig)}`)));
  }
}

function renderPageInfo(pg, fig) {
  $("#info-heading").textContent = "معلومات الصفحة";
  const body = $("#info-body"); body.replaceChildren();
  const st = pg.stats;
  const feats = Atlas.featuresOnPage(pg.page).filter((f) => f.kind !== "caption");
  appendKids(body, h("section", { class: "info-block" },
    h("h3", {}, "الصفحة في الملف الأصلي"),
    h("dl", { class: "kv" },
      h("dt", {}, "رقم الصفحة"), h("dd", {}, `${toArabicDigits(pg.page)} من ${toArabicDigits(8)}`),
      h("dt", {}, "الشكل"), h("dd", {}, `${Atlas.figLabel(fig)}: ${Atlas.figTitle(fig)}`),
      h("dt", {}, "الموقع في الشكل"), h("dd", {}, pg.halfLabel),
      h("dt", {}, "تعليق الشكل"), h("dd", {}, pg.hasCaption ? "مطبوع في هذه الصفحة" : `في الصفحة ${toArabicDigits(fig.captionPage)}`),
      h("dt", {}, "المقاس"), h("dd", { html: "<bdi>595 × 842</bdi> نقطة (A4 عمودي)" }),
      h("dt", {}, "طبقة نصية"), h("dd", {}, "لا توجد — الكتابة مرسومة كأشكال متجهية"),
      h("dt", {}, "عناصر متجهية"), h("dd", {}, toArabicDigits(pg.vectorDrawings)),
      h("dt", {}, "صور نقطية مضمّنة"), h("dd", {}, pg.rasterImages ? `${toArabicDigits(pg.rasterImages)} (رقع التنقيط)` : "لا يوجد"),
      h("dt", {}, "تسميات منسوخة"), h("dd", {}, toArabicDigits(pg.transcribedFeatures)),
      h("dt", {}, "حروف مرتبطة بنسخ"), h("dd", {}, `${toArabicDigits(st.glyphPathsLinkedToTranscription)} من ${toArabicDigits(st.labelGlyphPaths)}`),
    ),
    h("div", { class: "btn-row" }, h("a", { class: "btn primary", href: `#/fig/${fig.id}` }, "فتح الخريطة الكاملة في المستكشف")),
  ));
  if (st.glyphPathsNotLinked) appendKids(body, h("p", { class: "note" }, pg.page === 4
    ? `${toArabicDigits(st.glyphPathsNotLinked)} شكلًا داكنًا غير مرتبط بنسخ؛ معظمها أجزاء الأسهم المتقطعة ورؤوسها ونقاط مدن صغيرة.`
    : `${toArabicDigits(st.glyphPathsNotLinked)} شكلًا كتابيًا صغيرًا غير منسوخ (تسميات دقيقة متداخلة لم تُقرأ بثقة). تبقى ظاهرة في الصورة الأصلية والمتجهية.`));
  const list = h("ul", { class: "feature-list" });
  for (const f of feats.sort((a, b) => a.text.localeCompare(b.text, "ar"))) appendKids(list, h("li", {}, h("button", { onclick: () => go(`#/page/${pg.page}/${f.id}`) }, h("span", {}, f.text), h("small", {}, `${f.kindLabel}${f.conf !== "high" ? " · " + Atlas.conf[f.conf] : ""}`))));
  appendKids(body, h("section", { class: "info-block" }, h("h3", {}, `التسميات في هذه الصفحة (${toArabicDigits(feats.length)})`), list));
}

/* ------------------------------------------------------------------ */
/*  Compare                                                            */
/* ------------------------------------------------------------------ */
function sourceOptions() {
  const o = [];
  for (const f of Atlas.figures) o.push({ v: f.id, t: `${Atlas.figLabel(f)}: ${Atlas.figTitle(f)}` });
  for (const p of Atlas.pages) o.push({ v: "page-" + p.page, t: `الصفحة ${toArabicDigits(p.page)} (${Atlas.figLabel(Atlas.figure(p.figure))}، ${p.halfLabel})` });
  return o;
}
const REG_PAIRS = { "fig-1-1|fig-1-4": "fig", "fig-1-4|fig-1-1": "fig", "page-3|page-7": "east", "page-7|page-3": "east", "page-4|page-8": "west", "page-8|page-4": "west" };
function compareKind(a, b) {
  if (a === b) return "same";
  if (REG_PAIRS[`${a}|${b}`]) return "registered";
  if (a.startsWith("page-") && b.startsWith("page-")) return "pages";
  return "different";
}
async function showCompare(r) {
  const C = State.compare;
  if (r.q.a) C.a = r.q.a; if (r.q.b) C.b = r.q.b; if (r.q.mode) C.mode = r.q.mode;
  const ctl = $("#compare-controls"); ctl.replaceChildren();
  const mk = (val, key, label) => {
    const sel = h("select", { class: "input", "aria-label": label });
    for (const o of sourceOptions()) sel.append(h("option", { value: o.v, selected: o.v === val }, o.t));
    sel.addEventListener("change", () => { C[key] = sel.value; if (compareKind(C.a, C.b) !== "registered") C.mode = "side"; buildCompare(); });
    return sel;
  };
  const modeSeg = h("div", { class: "seg", role: "group", "aria-label": "نمط المقارنة" },
    h("button", { type: "button", "data-cmode": "side" }, "جنبًا إلى جنب"),
    h("button", { type: "button", "data-cmode": "swipe" }, "تمرير فوق بعض"));
  modeSeg.addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b || b.disabled) return; C.mode = b.dataset.cmode; buildCompare(); });
  const sync = h("label", { class: "check" }, h("input", { type: "checkbox", id: "cmp-sync" }), "مزامنة التكبير والتحريك");
  sync.querySelector("input").addEventListener("change", (e) => { C.sync = e.target.checked; });
  appendKids(ctl, h("span", { class: "muted" }, "اليمين:"), mk(C.a, "a", "الخريطة الأولى"), h("span", { class: "muted" }, "اليسار:"), mk(C.b, "b", "الخريطة الثانية"), modeSeg, sync,
    h("button", { class: "btn", onclick: () => { C.a = "fig-1-1"; C.b = "fig-1-4"; C.mode = "swipe"; showCompare({ q: {} }); } }, "مثال: ١-١ مقابل ١-٤"));
  await buildCompare();
}
async function buildSource(key, opts = {}) {
  if (key.startsWith("page-")) return MapView.page(parseInt(key.slice(5), 10), { mode: "vector", hotspots: true });
  return MapView.spread(Atlas.figure(key), opts);
}
async function buildCompare() {
  const C = State.compare; const token = ++State.buildToken;
  const kind = compareKind(C.a, C.b);
  if (C.mode === "swipe" && kind !== "registered") C.mode = "side";
  for (const b of $$("[data-cmode]")) { b.setAttribute("aria-pressed", String(b.dataset.cmode === C.mode)); if (b.dataset.cmode === "swipe") { b.disabled = kind !== "registered"; b.title = b.disabled ? "متاح فقط لخريطتين مرسومتين على الأساس نفسه (الشكل ١-١ والشكل ١-٤)" : ""; } }
  const syncBox = $("#cmp-sync");
  syncBox.disabled = !(kind === "same" || kind === "registered");
  if (syncBox.disabled) C.sync = false; else if (C.mode === "side" && !syncBox.dataset.touched) C.sync = true;
  syncBox.checked = C.sync;
  syncBox.onchange = (e) => { C.sync = e.target.checked; syncBox.dataset.touched = "1"; };
  const notes = {
    same: "المصدر نفسه في الجهتين.",
    registered: "الشكلان ١-١ و١-٤ مرسومان على الخريطة الأساسية نفسها (تحقّقنا من ذلك بمطابقة خطوط السواحل المتجهية). طُبّقت إزاحة تسجيل مقيسة (٠٫٥–١ نقطة) لمحاذاتهما. المقارنة تعرض ما رسمه كل شكل فقط، دون استنتاجات إضافية.",
    pages: "صفحتان مختلفتان: المزامنة معطّلة لأن الخريطتين لا تشتركان في الأساس أو المقياس.",
    different: "خريطتان بامتداد ومقياس مختلفين؛ تُعرضان جنبًا إلى جنب دون مزامنة لأن المحاذاة الجغرافية بينهما غير مضمونة.",
  };
  $("#compare-note").textContent = notes[kind];
  const host = $("#compare-panes");
  for (const p of C.panes) p.pz.destroy();
  C.panes = [];
  host.replaceChildren(h("div", { class: "map-loading" }, h("span", { class: "spinner" }), h("span", {}, "جارٍ التجهيز…")));
  history.replaceState(null, "", `#/compare?a=${C.a}&b=${C.b}&mode=${C.mode}`);

  if (C.mode === "swipe") {
    // one SVG: base = figure B, overlay = figure A (registered) clipped by the swipe line
    const reg = Atlas.d.registration["fig-1-1->fig-1-4"];
    const isFig = C.a.startsWith("fig-");
    const keyA = C.a, keyB = C.b;
    let translateA = null;
    if (isFig) translateA = keyA === "fig-1-1" ? { east: reg.east, west: reg.west } : { east: reg.east.map((v) => -v), west: reg.west.map((v) => -v) };
    const [vb, va] = await Promise.all([buildSource(keyB, { hotspots: true }), buildSource(keyA, { hotspots: false, translate: translateA })]);
    if (token !== State.buildToken) return;
    if (!isFig) { // page pair: apply registration translation to page A content
      const half = REG_PAIRS[`${keyA}|${keyB}`]; const t = reg[half]; const sign = keyA === "page-3" || keyA === "page-4" ? 1 : -1;
      const inner = va.svg.lastChild; void inner;
      for (const n of Array.from(va.svg.childNodes)) if (n.tagName === "svg") n.setAttribute("transform", `translate(${t[0] * sign} ${t[1] * sign})`);
    }
    const svg = vb.svg;
    const clipId = "swipe" + token;
    const cp = s("clipPath", { id: clipId }); const cr = s("rect", { x: -2000, y: -2000, width: 2000, height: 6000 }); cp.appendChild(cr);
    svg.querySelector("defs").appendChild(cp);
    for (const d of Array.from(va.svg.querySelectorAll(":scope > defs > *"))) svg.querySelector("defs").appendChild(d);
    const overlay = s("g", { "clip-path": `url(#${clipId})` });
    for (const n of Array.from(va.svg.childNodes)) if (n.tagName !== "defs" && !(n.classList && (n.classList.contains("hotspots") || n.classList.contains("selection")))) overlay.appendChild(n);
    const hsLayer = svg.querySelector(".hotspots");
    svg.insertBefore(overlay, hsLayer);
    const pane = h("div", { class: "pane" }); const ph = h("div", { class: "pane-host", tabindex: "0", "aria-label": "مقارنة بالتمرير" });
    const labA = sourceOptions().find((o) => o.v === keyA).t, labB = sourceOptions().find((o) => o.v === keyB).t;
    appendKids(pane, ph, h("div", { class: "pane-label" }, `يمين الخط: ${labA} — يسار الخط: ${labB}`));
    host.replaceChildren(pane); host.classList.remove("two"); ph.append(svg);
    let frac = 0.5;
    const handle = h("div", { class: "swipe-handle" }, h("button", { type: "button", "aria-label": "موضع خط المقارنة. استخدم السهمين لتحريكه" }, "⇆"));
    appendKids(pane, handle);
    let pz;
    const place = () => {
      if (!pz) return;
      const W = ph.clientWidth; const px = W * frac;
      handle.style.left = px + "px";
      const [ux] = pz.screenToUser(px, 0);
      // overlay (A) is shown on the right side of the line (RTL reading start)
      cr.setAttribute("x", ux); cr.setAttribute("width", 5000);
    };
    pz = new PanZoom(ph, svg, { content: vb.content, minWidth: 22, onChange: place, onCommit: place,
      onTap: (t) => { const g = t && t.closest && t.closest(".hs"); if (g) { const f = Atlas.byId.get(g.dataset.id); MapView.select(vb, f); renderFeatureCard(f); } },
      onHover: (e) => hoverTooltip(e, ph) });
    place();
    const btn = handle.querySelector("button");
    let dragging = false;
    btn.addEventListener("pointerdown", (e) => { dragging = true; btn.setPointerCapture(e.pointerId); e.stopPropagation(); });
    btn.addEventListener("pointermove", (e) => { if (!dragging) return; const r = ph.getBoundingClientRect(); frac = Math.min(0.98, Math.max(0.02, (e.clientX - r.left) / r.width)); place(); e.stopPropagation(); });
    btn.addEventListener("pointerup", (e) => { dragging = false; e.stopPropagation(); });
    btn.addEventListener("keydown", (e) => { if (e.key === "ArrowLeft") frac = Math.max(0.02, frac - 0.04); else if (e.key === "ArrowRight") frac = Math.min(0.98, frac + 0.04); else return; e.preventDefault(); place(); });
    C.panes.push({ view: vb, pz });
    return;
  }

  const views = await Promise.all([buildSource(C.a, kind === "registered" && C.a.startsWith("fig-") ? {} : {}), buildSource(C.b)]);
  if (token !== State.buildToken) return;
  host.replaceChildren(); host.classList.add("two");
  const labels = [C.a, C.b].map((k) => sourceOptions().find((o) => o.v === k).t);
  views.forEach((view, i) => {
    const pane = h("div", { class: "pane" }); const ph = h("div", { class: "pane-host", tabindex: "0", "aria-label": labels[i] });
    appendKids(pane, ph, h("div", { class: "pane-label" }, labels[i])); appendKids(host, pane); ph.append(view.svg);
    MapView.setLayers(view.svg, State.hiddenLayers);
    const pz = new PanZoom(ph, view.svg, { content: view.content, minWidth: 22,
      onTap: (t) => { const g = t && t.closest && t.closest(".hs"); if (g) { const f = Atlas.byId.get(g.dataset.id); MapView.select(view, f); renderFeatureCard(f); if (window.innerWidth <= 820) openPanel("panel-info", true); } },
      onHover: (e) => hoverTooltip(e, ph),
      onChange: (v) => { if (C.sync) for (const o of C.panes) if (o.pz !== pz) o.pz.setView(v, { silent: true }); } });
    C.panes.push({ view, pz });
  });
}

/* ------------------------------------------------------------------ */
/*  Gazetteer / index                                                  */
/* ------------------------------------------------------------------ */
function initIndexControls() {
  const kindSel = $("#index-kind"); kindSel.replaceChildren(h("option", { value: "" }, "كل الأنواع"));
  const kinds = [...new Set(Atlas.features.filter(Atlas.isMapFeature).map((f) => f.kind))];
  for (const k of kinds) kindSel.append(h("option", { value: k }, Atlas.kinds[k]));
  const figSel = $("#index-fig"); figSel.replaceChildren(h("option", { value: "" }, "كل الأشكال"));
  for (const f of Atlas.figures) figSel.append(h("option", { value: f.id }, `${Atlas.figLabel(f)}: ${Atlas.figTitle(f)}`));
  const rerender = debounce(() => showIndex(), 120);
  $("#index-filter").addEventListener("input", rerender); kindSel.addEventListener("change", rerender); figSel.addEventListener("change", rerender);
}
function letterOf(t) { const n = normalize(t).replace(/^ال(?=..)/, ""); return /^[0-9]/.test(n) ? "الأرقام والسنوات" : (n[0] || "#"); }
function showIndex() {
  const q = normalize($("#index-filter").value), kind = $("#index-kind").value, fig = $("#index-fig").value;
  const groups = new Map();
  for (const f of Atlas.features) {
    if (!Atlas.isMapFeature(f) || f.kind === "legend") continue;
    if (kind && f.kind !== kind) continue;
    if (fig && f.figure !== fig) continue;
    if (q && !f.norm.includes(q)) continue;
    const key = f.norm;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(f);
  }
  const entries = [...groups.values()].sort((a, b) => normalize(a[0].text).replace(/^ال(?=..)/, "").localeCompare(normalize(b[0].text).replace(/^ال(?=..)/, ""), "ar"));
  const byLetter = new Map();
  for (const e of entries) { const L = letterOf(e[0].text); if (!byLetter.has(L)) byLetter.set(L, []); byLetter.get(L).push(e); }
  // numbers (dates on conquest arrows) go last
  if (byLetter.has("الأرقام والسنوات")) { const v = byLetter.get("الأرقام والسنوات"); byLetter.delete("الأرقام والسنوات"); byLetter.set("الأرقام والسنوات", v); }
  const nav = $("#index-letters"); nav.replaceChildren();
  const body = $("#index-body"); body.replaceChildren();
  appendKids(body, h("p", { class: "muted" }, `${toArabicDigits(entries.length)} اسمًا فريدًا (بعد التطبيع) — ${toArabicDigits(entries.reduce((n, e) => n + e.length, 0))} موضعًا. يُتجاهل «ال» التعريف في الترتيب.`));
  let li = 0;
  for (const [L, list] of byLetter) {
    const id = "idx-" + (li++);
    appendKids(nav, h("a", { href: "#", title: L, style: L.length > 2 ? "width:auto;padding:0 8px" : null, onclick: (ev) => { ev.preventDefault(); document.getElementById(id).scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth" }); } }, L.length > 2 ? "٠–٩" : L));
    appendKids(body, h("h2", { class: "idx-letter", id }, L));
    const grid = h("div", { class: "idx-grid" });
    for (const occ of list) {
      const names = [...new Set(occ.map((o) => o.text))];
      appendKids(grid, h("div", { class: "idx-item" },
        h("div", { class: "nm", html: highlight(names.join(" / "), q) }),
        h("div", { class: "muted" }, [...new Set(occ.map((o) => o.kindLabel))].join("، ")),
        h("div", { class: "oc" }, occ.map((o) => h("a", { href: `#/fig/${o.figure}/${o.id}`, title: `الصفحة ${o.page}${o.conf !== "high" ? " — ثقة " + Atlas.conf[o.conf] : ""}` }, `${Atlas.figLabel(Atlas.figure(o.figure))} · ص ${toArabicDigits(o.page)}${o.conf === "low" ? " ⚠" : ""}`)))));
    }
    appendKids(body, grid);
  }
  if (!entries.length) appendKids(body, h("p", { class: "empty" }, "لا توجد أسماء مطابقة."));
}

/* ------------------------------------------------------------------ */
/*  Search                                                             */
/* ------------------------------------------------------------------ */
const Search = {
  index: [], kind: "", active: -1, results: [],
  build() {
    const idx = [];
    for (const f of Atlas.features) {
      if (f.kind === "caption") continue;
      idx.push({ type: "feature", id: f.id, text: f.text, norm: f.norm, kind: f.kind, f });
    }
    for (const c of Atlas.composites) idx.push({ type: "composite", id: c.id, text: c.text, norm: c.norm, kind: c.kind, c });
    for (const fig of Atlas.figures) idx.push({ type: "figure", id: fig.id, text: fig.caption, norm: normalize(fig.caption), kind: "caption", fig });
    this.index = idx;
  },
  query(qRaw) {
    const q = normalize(qRaw);
    if (!q) return [];
    const out = [];
    const pm = q.match(/^(?:ص|صفحه|page|p)\s*(\d{1,2})$/i) || (/^\d$/.test(q) ? [q, q] : null);
    if (pm) { const n = parseInt(pm[1], 10); if (n >= 1 && n <= 8) out.push({ type: "page", page: n, score: 120 }); }
    for (const e of this.index) {
      if (this.kind && e.kind !== this.kind) continue;
      let sc = 0;
      if (e.norm === q) sc = 100;
      else if (e.norm.startsWith(q)) sc = 80;
      else if ((" " + e.norm).includes(" " + q)) sc = 65;
      else if (e.norm.replace(/^ال/, "").startsWith(q)) sc = 70;
      else if (e.norm.includes(q)) sc = 40;
      if (!sc) continue;
      if (e.type === "figure") sc += 5;
      if (e.f && e.f.conf === "low") sc -= 8;
      out.push(Object.assign({ score: sc }, e));
    }
    out.sort((a, b) => b.score - a.score || (a.text || "").localeCompare(b.text || "", "ar"));
    return out;
  },
};

function initSearch() {
  Search.build();
  const input = $("#search-input"), panel = $("#search-panel"), list = $("#search-results"), clear = $("#search-clear");
  const filters = $("#search-filters");
  const kinds = ["", ...new Set(Atlas.features.filter((f) => f.kind !== "caption" && f.kind !== "legend").map((f) => f.kind))];
  for (const k of kinds) {
    appendKids(filters, h("button", { type: "button", "aria-pressed": String(k === ""), "data-k": k, onclick: (e) => { Search.kind = k; for (const b of $$("button", filters)) b.setAttribute("aria-pressed", String(b.dataset.k === k)); run(); input.focus(); } }, k ? Atlas.kinds[k] : "الكل"));
  }
  const open = (on) => { panel.hidden = !on; input.setAttribute("aria-expanded", String(on)); };
  const run = () => {
    const raw = input.value.trim(); clear.hidden = !raw;
    if (!raw) { open(false); return; }
    const q = normalize(raw);
    const res = Search.query(raw); Search.results = res.slice(0, 60); Search.active = res.length ? 0 : -1;
    list.replaceChildren();
    if (!res.length) {
      appendKids(list, h("li", { class: "empty" }, `لا نتائج لـ «${raw}». جرّب حذف «ال» أو كتابة جزء من الاسم.`));
    }
    let lastGroup = null;
    Search.results.forEach((r, i) => {
      const group = r.type === "feature" || r.type === "composite" ? "المعالم والتسميات" : "الأشكال والصفحات";
      if (group !== lastGroup) { appendKids(list, h("li", { class: "group", role: "presentation" }, group)); lastGroup = group; }
      let thumb = "", title = "", sub = "", meta = "";
      if (r.type === "feature") {
        const f = r.f, fig = Atlas.figure(f.figure);
        thumb = Assets.thumb(fig.id); title = highlight(f.text, q);
        sub = `${esc(f.kindLabel)} · ${esc(Atlas.figLabel(fig))}: ${esc(Atlas.figTitle(fig))}${f.note ? " · " + esc(f.note.slice(0, 60)) + (f.note.length > 60 ? "…" : "") : ""}`;
        meta = `ص ${toArabicDigits(f.page)}${f.conf !== "high" ? "<br>ثقة " + esc(Atlas.conf[f.conf]) : ""}`;
      } else if (r.type === "composite") {
        const fig = Atlas.figure(r.c.figure); thumb = Assets.thumb(fig.id); title = highlight(r.c.text, q); sub = esc(r.c.note); meta = "ص ١–٢";
      } else if (r.type === "figure") {
        thumb = Assets.thumb(r.fig.id); title = highlight(r.fig.caption, q); sub = `صفحتان: ${toArabicDigits(r.fig.westPage)} و${toArabicDigits(r.fig.eastPage)} · ${toArabicDigits(r.fig.featureCount)} تسمية`; meta = "شكل";
      } else if (r.type === "page") {
        const pg = Atlas.page(r.page), fig = Atlas.figure(pg.figure);
        thumb = Assets.thumb(`page-${String(r.page).padStart(3, "0")}`); title = `الصفحة ${toArabicDigits(r.page)}`; sub = `${esc(Atlas.figLabel(fig))} — ${esc(pg.halfLabel)}`; meta = "صفحة";
      }
      appendKids(list, h("li", { class: "result", role: "option", id: "sr-" + i, "aria-selected": String(i === Search.active), onmousedown: (e) => { e.preventDefault(); choose(i); } },
        h("img", { src: thumb, alt: "" }), h("div", {}, h("div", { class: "r-title", html: title }), h("div", { class: "r-sub", html: sub })), h("div", { class: "r-meta", html: meta })));
    });
    const names = new Set(res.filter((r) => r.type === "feature").map((r) => r.norm));
    $("#search-foot").textContent = res.length ? `${toArabicDigits(res.length)} نتيجة${names.size && res.length > names.size ? ` (الاسم الواحد قد يرد في أكثر من خريطة؛ تُعرض كل المواضع)` : ""} · ↑↓ للتنقل، Enter للفتح، Esc للإغلاق` : "البحث يتجاهل الهمزات والتشكيل والتطويل، ويوحّد ى/ي و ة/ه والأرقام العربية/الهندية.";
    input.setAttribute("aria-activedescendant", Search.active >= 0 ? "sr-" + Search.active : "");
    open(true);
  };
  const choose = (i) => {
    const r = Search.results[i]; if (!r) return;
    open(false); input.blur();
    if (r.type === "feature") go(`#/fig/${r.f.figure}/${r.f.id}`);
    else if (r.type === "composite") go(`#/fig/${r.c.figure}/${r.c.parts[0]}`);
    else if (r.type === "figure") go(`#/fig/${r.fig.id}`);
    else if (r.type === "page") go(`#/page/${r.page}`);
  };
  input.addEventListener("input", debounce(run, 110));
  input.addEventListener("focus", () => { if (input.value.trim()) run(); });
  input.addEventListener("blur", () => setTimeout(() => open(false), 120));
  input.addEventListener("keydown", (e) => {
    const n = Search.results.length;
    if (e.key === "ArrowDown" && n) { Search.active = (Search.active + 1) % n; e.preventDefault(); }
    else if (e.key === "ArrowUp" && n) { Search.active = (Search.active - 1 + n) % n; e.preventDefault(); }
    else if (e.key === "Enter") { if (Search.active >= 0) choose(Search.active); e.preventDefault(); return; }
    else if (e.key === "Escape") { open(false); input.blur(); return; }
    else return;
    for (const li of $$(".result", list)) li.setAttribute("aria-selected", String(li.id === "sr-" + Search.active));
    const act = document.getElementById("sr-" + Search.active); if (act) { act.scrollIntoView({ block: "nearest" }); input.setAttribute("aria-activedescendant", act.id); }
  });
  clear.addEventListener("click", () => { input.value = ""; run(); input.focus(); });
}

/* ------------------------------------------------------------------ */
/*  TOC                                                                */
/* ------------------------------------------------------------------ */
function renderToc() {
  const list = $("#toc-list"); const q = normalize($("#toc-filter").value);
  list.className = "toc-list" + (State.tocMode === "gallery" ? " gallery" : "");
  list.replaceChildren();
  for (const b of $$("[data-tocmode]")) b.setAttribute("aria-pressed", String(b.dataset.tocmode === State.tocMode));
  let shown = 0;
  for (const fig of Atlas.figures) {
    const hay = normalize(`${fig.caption} ${fig.westPage} ${fig.eastPage} صفحه ${fig.westPage} صفحه ${fig.eastPage}`);
    if (q && !hay.includes(q)) continue;
    shown++;
    const cur = State.fig && State.fig.id === fig.id && State.route && State.route.view === "explore";
    appendKids(list, h("div", { class: "toc-fig", "aria-current": String(!!cur) },
      h("button", { class: "toc-fig-btn", onclick: () => { go(`#/fig/${fig.id}`); closePanels(); } },
        h("img", { src: Assets.thumb(fig.id), alt: "" }),
        h("span", {}, h("span", { class: "t1" }, `${Atlas.figLabel(fig)}: ${Atlas.figTitle(fig)}`), h("span", { class: "t2" }, `${toArabicDigits(fig.featureCount)} تسمية منسوخة · صفحتان`))),
      h("div", { class: "toc-pages" }, [fig.westPage, fig.eastPage].map((p) =>
        h("a", { href: `#/page/${p}`, onclick: () => closePanels(), title: `الصفحة الأصلية ${p}` }, h("img", { src: Assets.thumb(`page-${String(p).padStart(3, "0")}`), alt: "" }), `ص ${toArabicDigits(p)} · ${Atlas.page(p).half === "east" ? "شرق" : "غرب"}`)))));
  }
  if (!shown) appendKids(list, h("p", { class: "empty" }, "لا توجد أشكال مطابقة."));
  appendKids(list, h("p", { class: "muted", style: "margin:4px 2px 0" }, "الترتيب كما في ملف PDF. لا يتضمن الملف «شكل ١-٢»؛ لم يُضف إلى المحتويات."));
}

/* ------------------------------------------------------------------ */
/*  About / audit                                                      */
/* ------------------------------------------------------------------ */
function showAbout() {
  const T = Atlas.d.totals, src = Atlas.d.source;
  const body = $("#about-body"); body.replaceChildren();
  const stat = (n, t) => h("div", { class: "stat" }, h("b", { class: "num" }, toArabicDigits(n)), h("span", {}, t));
  appendKids(body, 
    h("h1", {}, "عن الأطلس وتقرير التدقيق"),
    h("p", { class: "lead" }, "هذه نسخة تفاعلية مبنية مباشرة على ملف PDF «خرائط التاريخ الإسلامي». كل تسمية قابلة للبحث أو النقر مرتبطة بصفحتها الأصلية وبحدود حروفها المرسومة في الملف، ويمكن دائمًا مقارنتها بالصورة الأصلية للصفحة."),
    h("h2", {}, "أرقام التدقيق (مقيسة فعليًا)"),
    h("div", { class: "cards" },
      stat(T.pdfPages, "صفحات ملف PDF"), stat(T.pagesProcessed, "صفحات عولجت"), stat(T.figures, "أشكال (خرائط) — كل شكل صفحتان"),
      stat(T.pagesWithTextLayer, "صفحات بطبقة نصية قابلة للاستخراج"), stat(T.pagesRequiringVisualTranscription, "صفحات احتاجت نسخًا بصريًا"),
      stat(T.transcribedFeatures, "تسمية منسوخة (مع التعليقات)"), stat(T.searchableEntries, "مدخلًا قابلًا للبحث"), stat(T.interactiveHotspots, "منطقة تفاعل على الخرائط"),
      stat(T.uniqueNames, "اسمًا فريدًا بعد التطبيع"), stat(T.namesOnMultipleFigures, "اسمًا يرد في أكثر من شكل"),
      stat(T.markersLinked, `علامة نقطية رُبطت بتسميتها من ${toArabicDigits(T.markersDetected)}`),
      stat(T.labelGlyphPathsLinked, `شكلًا كتابيًا مرتبطًا بنسخ من ${toArabicDigits(T.labelGlyphPaths)}`),
      stat(T.mediumConfidence, "تسمية بثقة متوسطة"), stat(T.lowConfidence, "تسمية بثقة منخفضة / غير مقروءة")),
    h("h2", {}, "جرد الصفحات"),
  );
  const tbl = h("table", {}, h("thead", {}, h("tr", {}, ["الصفحة", "الشكل", "الموقع", "تعليق", "عناصر متجهية", "تسميات منسوخة", "حروف مرتبطة", "متوسطة/منخفضة", "الحالة"].map((t) => h("th", {}, t)))));
  const tb = h("tbody");
  for (const p of Atlas.pages) {
    const fig = Atlas.figure(p.figure);
    appendKids(tb, h("tr", {},
      h("td", {}, h("a", { href: `#/page/${p.page}` }, toArabicDigits(p.page))), h("td", {}, Atlas.figLabel(fig)), h("td", {}, p.halfLabel),
      h("td", {}, p.hasCaption ? "نعم" : "—"), h("td", { class: "num" }, toArabicDigits(p.vectorDrawings)), h("td", { class: "num" }, toArabicDigits(p.transcribedFeatures)),
      h("td", { class: "num" }, `${toArabicDigits(p.stats.glyphPathsLinkedToTranscription)}/${toArabicDigits(p.stats.labelGlyphPaths)}`),
      h("td", { class: "num" }, `${toArabicDigits(p.mediumConfidence)}/${toArabicDigits(p.lowConfidence)}`),
      h("td", { title: p.completenessNote || "" }, p.verificationStatus === "transcribed-visually" ? "منسوخة بالكامل تقريبًا" : "منسوخة جزئيًا")));
  }
  appendKids(tbl, tb); appendKids(body, tbl);
  const review = Atlas.features.filter((f) => f.conf === "low" || f.kind === "unreadable");
  appendKids(body, h("h2", {}, "عناصر تحتاج إلى مراجعة يدوية"));
  const ul = h("ul");
  for (const f of review) appendKids(ul, h("li", {}, h("a", { href: `#/fig/${f.figure}/${f.id}` }, `«${f.text}»`), ` — ص ${toArabicDigits(f.page)}: ${f.note || ""}`));
  appendKids(body, ul);
  appendKids(body, 
    h("h2", {}, "المنهجية"),
    h("ol", {},
      h("li", {}, "فحص الملف: ٨ صفحات A4 عمودية، بلا طبقة نصية ولا خطوط مضمّنة؛ كل الكتابة العربية مرسومة كأشكال متجهية مملوءة، وتوجد ٨ صور نقطية صغيرة فقط (رقع التنقيط في الصفحتين ١ و٢)."),
      h("li", {}, "اكتشاف البنية: الصفحات الثماني تشكّل أربع خرائط مزدوجة؛ كل شكل نصفه الشرقي في صفحة فردية (وعليها التعليق) ونصفه الغربي في الصفحة التالية. حُسبت إزاحة الوصل (٤٤٥٫٩ نقطة) من هندسة متكررة في الصفحتين وتحققنا منها بصريًا."),
      h("li", {}, "فصل الطبقات: صُنّف كل عنصر متجهي حسب خصائص رسمه (تعبئة داكنة = كتابة، دوائر داكنة = علامات مواقع، خط رمادي ٠٫٨٤ = حدود، خط أسود ١٫٦٨ = خط امتداد، نقاط رمادية = تنقيط)."),
      h("li", {}, "النسخ: جُمعت أشكال الحروف آليًا في كتل كلمات، ثم قُرئت كل تسمية بصريًا على تكبير ٣–١٤ ضعفًا وسُجّلت مع رقم الكتلة أو مربع تقريبي يُلتقط آليًا إلى حدود الحروف الفعلية. لم يُخمَّن أي اسم غير مقروء."),
      h("li", {}, "التحقق: مقارنة الرسم المتجهي في المتصفح بصورة الصفحة المستخرجة (فرق ≤ ٠٫١٪ من البكسلات)، وتراكب مناطق التفاعل على الصفحات للتأكد من محاذاتها، وإبراز الحروف غير المرتبطة بنسخ."),
    ),
    h("h2", {}, "حدود معروفة"),
    h("ul", {},
      h("li", {}, "الصفحة ٢ (أكثف الصفحات): ٧٣ شكلًا كتابيًا صغيرًا جدًا (تسميات مدن مدوّرة في إسكندنافيا والبلطيق وبحر إيجة وغيرها) لم تُنسخ لعدم إمكان قراءتها بثقة؛ تبقى ظاهرة في الخريطة والصورة الأصلية."),
      h("li", {}, "الخرائط ليست بيانات جغرافية (GIS): لا توجد إحداثيات طول وعرض في الملف، ومناطق التفاعل مرتبطة بمواضع التسميات المطبوعة لا بحدود الدول أو الأقاليم. لم تُرسم حدود تفاعلية مزيفة."),
      h("li", {}, "تصنيف أنواع التسميات (مدينة، كيان سياسي…) تحريري مبني على صياغة التسمية ورمزها، وليس واردًا في الملف."),
      h("li", {}, "الأسهم المتقطعة في الشكل ١-١ والخطوط السوداء العريضة في الأشكال ١-٣ و١-٤ غير مشروحة في الملف؛ عُرضت كما هي دون تفسير. الأرقام على الأسهم منسوخة كما هي ولم يُذكر التقويم المستخدم."),
      h("li", {}, "لا يتضمن الملف «شكل ١-٢»، والتسلسل يبدأ بـ«شكل ٢» ثم «شكل ١-١»؛ حُفظ ترتيب الملف."),
      h("li", {}, "لم يكن محرك OCR عربي متاحًا في بيئة البناء؛ لذلك اعتمد النسخ على القراءة البصرية الموثّقة بالإحداثيات بدلًا من OCR."),
    ),
    h("h2", {}, "طريقة الاستخدام"),
    h("ul", {},
      h("li", {}, "المستكشف: اسحب لتحريك الخريطة، واستخدم العجلة أو إيماءة القرص أو الأزرار للتكبير، وانقر نقرًا مزدوجًا للتكبير على نقطة. انقر أي تسمية لعرض بطاقتها ومقتطفها من الصفحة الأصلية."),
      h("li", {}, "البحث: اكتب أي جزء من الاسم؛ يتجاهل البحث الهمزات والتشكيل ويوحّد ى/ي وة/ه، ويعرض كل المواضع إذا ورد الاسم في أكثر من خريطة. اكتب «ص ٣» للانتقال إلى صفحة."),
      h("li", {}, "الصفحات الأصلية: صورة كل صفحة مستخرجة مباشرة من الملف، مع عرض متجهي ومقارنة جنبًا إلى جنب بتكبير متزامن."),
      h("li", {}, "المقارنة: اعرض خريطتين جنبًا إلى جنب، أو مرّر خطًا فوق الشكلين ١-١ و١-٤ المرسومين على الأساس نفسه."),
    ),
    h("h3", {}, "اختصارات لوحة المفاتيح"),
    h("p", { html: `<span class="kbd">/</span> البحث · <span class="kbd">+</span> <span class="kbd">−</span> تكبير/تصغير · <span class="kbd">0</span> ملاءمة · الأسهم للتحريك · <span class="kbd">F</span> ملء الشاشة · <span class="kbd">H</span> إظهار مناطق التفاعل · <span class="kbd">L</span> الطبقات · <span class="kbd">Esc</span> إغلاق` }),
    h("h2", {}, "الإعدادات والبيانات المحلية"),
  );
  const ref = h("label", { class: "check" }, h("input", { type: "checkbox", id: "set-ref", checked: State.settings.referenceOnly }), "وضع المرجع فقط (إخفاء قسم التعلّم والاختبارات)");
  ref.querySelector("input").addEventListener("change", (e) => { State.settings.referenceOnly = e.target.checked; Store.set("settings", State.settings); applySettings(); });
  appendKids(body, ref,
    h("p", { class: "muted" }, Store.ok ? "يحفظ الأطلس المحفوظات وآخر ما شوهد وتفضيلات العرض وتقدّم التعلّم في التخزين المحلي للمتصفح فقط، ولا يرسل أي بيانات إلى أي خادم." : "التخزين المحلي غير متاح في هذا المتصفح؛ لن تُحفظ التفضيلات بين الجلسات."),
    h("button", { class: "btn", onclick: () => { const n = Store.clearAll(); State.hiddenLayers.clear(); toast(`حُذفت ${toArabicDigits(n)} عناصر من البيانات المحلية`); renderSavedLists(); } }, "مسح البيانات المحلية"),
    h("h2", {}, "المصدر"),
    h("dl", { class: "kv" },
      h("dt", {}, "الملف"), h("dd", {}, src.originalName),
      h("dt", {}, "بصمة MD5"), h("dd", {}, h("bdi", { class: "ltr" }, src.md5)),
      h("dt", {}, "الحجم"), h("dd", {}, `${toArabicDigits((src.bytes / 1048576).toFixed(2))} ميغابايت`),
      h("dt", {}, "عنوان البيانات الوصفية"), h("dd", {}, src.pdfTitleMetadata),
      h("dt", {}, "أداة الإنتاج"), h("dd", {}, h("bdi", { class: "ltr" }, `${src.producer} — ${src.created}`))),
    h("p", { class: "muted" }, "الخط: IBM Plex Sans Arabic (رخصة SIL Open Font License 1.1) مضمّن في الملف ليعمل دون إنترنت. لا يستخدم الأطلس أي مكتبات خارجية أو اتصالات شبكية."),
  );
}

function renderInfoGeneric(view) {
  $("#info-heading").textContent = "معلومات";
  const body = $("#info-body"); body.replaceChildren();
  if (view === "compare") {
    appendKids(body, h("section", { class: "info-block" }, h("h3", {}, "المقارنة"), h("p", { class: "muted" }, "انقر أي تسمية في إحدى الخريطتين لعرض بطاقتها هنا. تُفعَّل المزامنة فقط عندما تشترك الخريطتان في الأساس نفسه.")));
  } else if (view === "index") {
    appendKids(body, h("section", { class: "info-block" }, h("h3", {}, "فهرس الأسماء"), h("p", { class: "muted" }, "كل اسم مرتبط بمواضعه في الأشكال. الأسماء المتطابقة بعد التطبيع تُجمع في بطاقة واحدة مع إبقاء كل موضع منفصلًا — لم تُدمج أماكن مختلفة.")));
    renderFeatureCard(null);
  } else {
    renderFeatureCard(null);
    appendKids(body, h("section", { class: "info-block" }, h("h3", {}, "المحتوى"), h("p", { class: "muted" }, `${toArabicDigits(Atlas.figures.length)} أشكال في ${toArabicDigits(8)} صفحات، و${toArabicDigits(Atlas.d.totals.interactiveHotspots)} تسمية قابلة للنقر والبحث.`)));
  }
}

/* ------------------------------------------------------------------ */
/*  Panels, theme, shortcuts                                           */
/* ------------------------------------------------------------------ */
function openPanel(id, peek = false) {
  const p = document.getElementById(id); p.classList.add("open"); p.classList.toggle("peek", peek);
  $("#scrim").hidden = window.innerWidth > 1100 && id === "panel-toc" ? true : false;
  const btn = id === "panel-toc" ? $("#btn-toc") : $("#btn-info"); if (btn) btn.setAttribute("aria-expanded", "true");
}
function closePanels() {
  for (const p of $$(".panel")) p.classList.remove("open", "peek");
  $("#scrim").hidden = true;
  for (const b of [$("#btn-toc"), $("#btn-info")]) if (b) b.setAttribute("aria-expanded", "false");
}
function applyTheme(t) { document.documentElement.dataset.theme = t; Store.set("theme", t); }
function applySettings() { $("#nav-learn").hidden = !!State.settings.referenceOnly; }

function initChrome() {
  $("#btn-toc").addEventListener("click", () => ($("#panel-toc").classList.contains("open") ? closePanels() : openPanel("panel-toc")));
  $("#btn-info").addEventListener("click", () => ($("#panel-info").classList.contains("open") ? closePanels() : openPanel("panel-info")));
  $("#scrim").addEventListener("click", closePanels);
  for (const b of $$("[data-close]")) b.addEventListener("click", closePanels);
  $("#btn-theme").addEventListener("click", () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
  $("#toc-filter").addEventListener("input", debounce(renderToc, 100));
  for (const b of $$("[data-tocmode]")) b.addEventListener("click", () => { State.tocMode = b.dataset.tocmode; Store.set("tocMode", State.tocMode); renderToc(); });

  const wrap = $("#view-explore .viewer-wrap");
  $("#view-explore .toolbar").addEventListener("click", (e) => {
    const b = e.target.closest("[data-act]"); if (!b || !State.pz) return;
    const a = b.dataset.act;
    if (a === "zoom-in") State.pz.zoomBy(1.5, undefined, undefined, true);
    else if (a === "zoom-out") State.pz.zoomBy(1 / 1.5, undefined, undefined, true);
    else if (a === "fit") State.pz.fit();
    else if (a === "reset") { State.pz.fit(); selectFeature(null); State.kindFilter = null; applyKindFilter(); }
    else if (a === "fullscreen") toggleFullscreen(wrap);
    else if (a === "layers") { const pop = $("#layers-pop"); pop.hidden = !pop.hidden; b.setAttribute("aria-expanded", String(!pop.hidden)); }
    else if (a === "hotspots") { State.showHs = !State.showHs; Store.set("showHotspots", State.showHs); b.setAttribute("aria-pressed", String(State.showHs)); State.view.svg.classList.toggle("show-hs", State.showHs); }
    else if (a === "original") { const f = State.selected; go(f ? `#/page/${f.page}/${f.id}` : `#/page/${State.fig.eastPage}`); }
  });
  $('[data-act="hotspots"]').setAttribute("aria-pressed", String(State.showHs));

  const pwrap = $("#view-page .viewer-wrap");
  $("#view-page .toolbar").addEventListener("click", (e) => {
    const b = e.target.closest("[data-pact]"); if (!b) return;
    const a = b.dataset.pact; const n = State.page.n;
    if (a === "prev" && n > 1) go(`#/page/${n - 1}`);
    else if (a === "next" && n < 8) go(`#/page/${n + 1}`);
    else if (a === "zoom-in") State.page.panes.forEach((p, i) => i === 0 && p.pz.zoomBy(1.5, undefined, undefined, true));
    else if (a === "zoom-out") State.page.panes.forEach((p, i) => i === 0 && p.pz.zoomBy(1 / 1.5, undefined, undefined, true));
    else if (a === "fit") State.page.panes.forEach((p) => p.pz.fit());
    else if (a === "fullscreen") toggleFullscreen(pwrap);
    else if (a === "explore") go(`#/fig/${Atlas.page(n).figure}`);
  });
  for (const b of $$("[data-pagemode]")) b.addEventListener("click", async () => { State.page.mode = b.dataset.pagemode; for (const x of $$("[data-pagemode]")) x.setAttribute("aria-pressed", String(x === b)); await buildPagePanes(); });
  $("#page-hotspots").addEventListener("change", async (e) => { State.page.hs = e.target.checked; await buildPagePanes(); });

  document.addEventListener("keydown", (e) => {
    const tag = (e.target.tagName || "").toLowerCase();
    const typing = tag === "input" || tag === "select" || tag === "textarea";
    if (e.key === "Escape") { closePanels(); $("#layers-pop").hidden = true; hideTooltip(); return; }
    if (typing || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === "/") { e.preventDefault(); $("#search-input").focus(); }
    else if (State.route && State.route.view === "explore") {
      if (e.key === "f" || e.key === "F" || e.key === "ب") toggleFullscreen(wrap);
      else if (e.key === "h" || e.key === "H" || e.key === "ا") $('[data-act="hotspots"]').click();
      else if (e.key === "l" || e.key === "L" || e.key === "م") $('[data-act="layers"]').click();
    }
  });
  document.addEventListener("click", (e) => {
    const pop = $("#layers-pop");
    if (!pop.hidden && !pop.contains(e.target) && !e.target.closest('[data-act="layers"]')) { pop.hidden = true; $('[data-act="layers"]').setAttribute("aria-expanded", "false"); }
  });
}
function toggleFullscreen(el) {
  try {
    if (document.fullscreenElement) document.exitFullscreen();
    else if (el.requestFullscreen) el.requestFullscreen().catch(() => toast("ملء الشاشة غير متاح في هذا المتصفح"));
    else toast("ملء الشاشة غير متاح في هذا المتصفح");
  } catch (err) { toast("ملء الشاشة غير متاح"); }
}

/* ------------------------------------------------------------------ */
/*  Boot                                                               */
/* ------------------------------------------------------------------ */
function boot() {
  try {
    const d = Assets.load();
    Atlas.init(d);
  } catch (err) {
    document.body.innerHTML = `<div class="err-box"><strong>تعذّر تحميل بيانات الأطلس.</strong><br>${esc(err.message)}</div>`;
    return;
  }
  const theme = Store.get("theme", null);
  applyTheme(theme || "light");
  applySettings();
  // mobile nav (duplicated main nav, shown under the viewer head on narrow screens)
  const mnav = h("nav", { class: "mobile-nav", "aria-label": "الأقسام" }, $$(".mainnav a").map((a) => { const c = a.cloneNode(true); return c; }));
  $("#panel-toc").prepend(mnav);
  initChrome(); initSearch(); initIndexControls(); renderSavedLists(); renderToc();
  if (window.Learn) Learn.init();
  window.addEventListener("hashchange", () => onRoute());
  onRoute().catch((err) => { console.error(err); toast("حدث خطأ أثناء عرض الخريطة: " + err.message, 6000); });
}
document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", boot) : boot();
