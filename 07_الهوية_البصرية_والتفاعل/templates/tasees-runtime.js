/* تأسيس — runtime for the 18 interaction patterns (P01–P18) · v1.0
   Usage:  Tasees.render(boxElement, "P01", data)
   Data shapes: see 04_تعليمات_وكلاء_الذكاء_الاصطناعي.md §B and week-template.html.
   No libraries. All learner input stays in localStorage (wrapped in try/catch). */
(function () {
  "use strict";
  var RUNTIME_SRC = (document.currentScript && document.currentScript.src) || "";
  var DOC_WEEK = (document.documentElement && document.documentElement.getAttribute ? (document.documentElement.getAttribute("data-week") || "") : "");
  // storage namespace per week: <html data-week="w01">
  var NS = "tasees-" + (DOC_WEEK || "tpl") + "-";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var AR = function (n) { return String(n).replace(/\d/g, function (d) { return "٠١٢٣٤٥٦٧٨٩"[d]; }); };
  var el = function (tag, attrs, html) { var e = document.createElement(tag); for (var k in (attrs || {})) e.setAttribute(k, attrs[k]); if (html != null) e.innerHTML = html; return e; };
  var store = { get: function (k) { try { return localStorage.getItem(NS + k); } catch (e) { return null; } },
                set: function (k, v) { try { localStorage.setItem(NS + k, v); } catch (e) {} } };
  var shuffle = function (a, seed) { a = a.slice(); var s = seed || 7; for (var i = a.length - 1; i > 0; i--) { s = (s * 9301 + 49297) % 233280; var j = Math.floor(s / 233280 * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; };
  var fb = function (box, ok, title, text) { box.className = "t-feedback " + (ok ? "t-feedback--ok" : "t-feedback--bad"); box.innerHTML = "<strong>" + (ok ? "✓ " : "✗ ") + title + "</strong>" + (text || ""); box.hidden = false; };

  /* ---------- pattern renderers ---------- */
  var R = {};

  R.P01 = function (box, d) {               // ordering by swap
    var list = shuffle(d.items, 5), sel = null, wrap = el("div", { class: "order" }), msg = el("p", { class: "t-feedback" }); msg.hidden = true;
    function draw() { wrap.innerHTML = ""; list.forEach(function (t, i) { var b = el("button", { class: "t-choice", type: "button", "aria-pressed": sel === i }, "<b>" + AR(i + 1) + "</b><span>" + t + "</span>"); b.onclick = function () { if (sel === null) { sel = i; } else { var x = list[sel]; list[sel] = list[i]; list[i] = x; sel = null; } msg.hidden = true; draw(); }; wrap.appendChild(b); }); }
    var chk = el("button", { class: "t-btn", type: "button" }, "تحقق");
    chk.onclick = function () { var bad = 0; $$(".t-choice", wrap).forEach(function (b, i) { var ok = list[i] === d.items[i]; b.classList.toggle("is-right", ok); b.classList.toggle("is-wrong", !ok); if (!ok) bad++; }); fb(msg, !bad, bad ? "فيه " + AR(bad) + " كروت مش في مكانها" : "الكروت في ترتيبها", bad ? "" : d.done); };
    draw(); box.append(wrap, el("div", { class: "row" }), msg); box.children[1].appendChild(chk);
  };

  R.P02 = function (box, d) {               // sort into bins
    var pool = el("div", { class: "pool" }), bins = el("div", { class: "bins" }), msg = el("p", { class: "t-feedback" }), sel = null; msg.hidden = true;
    d.items.forEach(function (it, i) { var c = el("button", { class: "t-chip", type: "button", "aria-pressed": "false", "data-i": i }, it[0]); c.onclick = function () { sel = (sel === c) ? null : c; $$(".t-chip", pool).forEach(function (x) { x.setAttribute("aria-pressed", x === sel); }); }; pool.appendChild(c); });
    d.bins.forEach(function (name, bi) { var b = el("button", { class: "bin", type: "button" }, "<strong>" + name + "</strong>"); b.onclick = function () { if (!sel) return; var it = d.items[+sel.dataset.i], s = el("span", { class: "item " + (it[1] === bi ? "is-right" : "is-wrong") }, (it[1] === bi ? "✓ " : "✗ ") + it[0]); b.appendChild(s); sel.remove(); sel = null; if (!pool.children.length) { var bad = $$(".item.is-wrong", bins).length; fb(msg, !bad, bad ? "راجع " + AR(bad) : "الفرز سليم", d.done); } }; bins.appendChild(b); });
    box.append(pool, bins, msg);
  };

  R.P03 = function (box, d) {               // match pairs
    var wrap = el("div", { class: "pair" }), a = el("div"), b = el("div"), sel = null, n = 0, msg = el("p", { class: "t-feedback" }); msg.hidden = true;
    var right = shuffle(d.pairs.map(function (p, i) { return [p[1], i]; }), 3);
    d.pairs.forEach(function (p, i) { var x = el("button", { class: "t-choice", type: "button", "aria-pressed": "false", "data-i": i }, p[0]); x.onclick = function () { if (x.dataset.pairnum) return; sel = x; $$(".t-choice", a).forEach(function (y) { y.setAttribute("aria-pressed", y === x); }); }; a.appendChild(x); });
    right.forEach(function (p) { var y = el("button", { class: "t-choice", type: "button" }, p[0]); y.onclick = function () { if (!sel || y.dataset.pairnum) return; if (+sel.dataset.i === p[1]) { n++; sel.dataset.pairnum = y.dataset.pairnum = AR(n); sel.classList.add("is-right"); y.classList.add("is-right"); sel.setAttribute("aria-pressed", "false"); sel = null; msg.hidden = true; if (n === d.pairs.length) fb(msg, true, "كل علم في مكانه", d.done); } else { fb(msg, false, "مش ده", d.hint); } }; b.appendChild(y); });
    wrap.append(a, b); box.append(wrap, msg);
  };

  R.P04 = function (box, d) {               // hotspots on an authored SVG
    var NS = '<svg class="post" viewBox="' + (d.viewBox || "0 0 380 250") + '" role="img" aria-label="' + (d.label || "") + '">' + d.art +
      d.spots.map(function (s, i) { return '<rect class="hs" data-i="' + i + '" tabindex="0" role="button" aria-label="' + s.label + '" x="' + s.x + '" y="' + s.y + '" width="' + s.w + '" height="' + s.h + '" rx="6"/>'; }).join("") + "</svg>";
    box.insertAdjacentHTML("beforeend", NS);
    var found = 0, msg = el("p", { class: "t-feedback" }); msg.hidden = true; box.appendChild(msg);
    $$(".hs", box).forEach(function (h) { var hit = function () { if (h.classList.contains("found")) return; h.classList.add("found"); found++; var s = d.spots[+h.dataset.i]; fb(msg, true, "مصيدة " + AR(found) + " من " + AR(d.spots.length) + ": " + s.label, s.why); }; h.addEventListener("click", hit); h.addEventListener("keydown", function (e) { if (e.key === "Enter") hit(); }); });
  };

  R.P05 = function (box, d) {               // branching dialogue
    var chat = el("div", { class: "chat" }), opts = el("div", { class: "demo" });
    chat.appendChild(el("p", { class: "bubble them" }, d.open));
    d.replies.forEach(function (r) { var b = el("button", { class: "t-choice", type: "button" }, r.say); b.onclick = function () { chat.appendChild(el("p", { class: "bubble me" }, r.say)); chat.appendChild(el("p", { class: "bubble them" }, r.then)); var f = el("p", { class: "t-feedback" }); fb(f, r.good, r.good ? "حوار" : "مناظرة", r.note); chat.appendChild(f); opts.remove(); }; opts.appendChild(b); });
    box.append(chat, opts);
  };

  R.P06 = function (box, d) {               // card builder: the four pillars
    var saved = {}; try { saved = JSON.parse(store.get(d.key || "card") || "{}"); } catch (e) {}
    var form = el("div", { class: "builder" }), por = el("div", { class: "portico", "aria-live": "polite" });
    d.fields.forEach(function (f) {
      var lab = el("label", {}, f.label), inp;
      if (f.options) { inp = el("select", { id: "pf-" + f.key }); f.options.forEach(function (o) { inp.appendChild(el("option", {}, o)); }); }
      else { inp = el("input", { id: "pf-" + f.key, type: "text", placeholder: f.ph }); }
      inp.value = saved[f.key] || f.example || (f.options ? f.options[0] : ""); lab.appendChild(inp); form.appendChild(lab);
      var col = el("div"); col.dataset.k = f.key; por.appendChild(col);
      var paint = function () { col.innerHTML = "<small>" + f.label + "</small>" + (inp.value || "…"); saved[f.key] = inp.value; store.set(d.key || "card", JSON.stringify(saved)); };
      inp.addEventListener("input", paint); inp.addEventListener("change", paint); paint();
    });
    var copy = el("button", { class: "t-btn t-btn--ghost", type: "button" }, "انسخ خريطتي"), m = el("span", { class: "t-small" });
    copy.onclick = function () { var t = d.fields.map(function (f) { return f.label + ": " + (saved[f.key] || ""); }).join("\n"); var done = function () { m.textContent = "اتنسخت"; }; if (navigator.clipboard) navigator.clipboard.writeText(t).then(done, function () { m.textContent = "النسخ مش متاح هنا"; }); };
    var row = el("div", { class: "row" }); row.append(copy, m);
    box.append(form, por, row, el("p", { class: "t-small" }, d.note || "ما تكتبه يبقى على جهازك."));
  };

  R.P07 = function (box, d) {               // explore: open every part
    var g = el("div", { class: "explore" }), out = el("p", { class: "t-feedback" }), seen = {};
    out.innerHTML = "<strong>" + d.prompt + "</strong>";
    d.parts.forEach(function (p, i) { var b = el("button", { type: "button", "aria-pressed": "false", style: "--c:" + p.c }, p.name); b.onclick = function () { seen[i] = 1; $$("button", g).forEach(function (x) { x.setAttribute("aria-pressed", x === b); }); out.innerHTML = "<strong>" + p.name + "</strong>" + p.text + (Object.keys(seen).length === d.parts.length ? "<br><b>✓ فتحت الأجزاء كلها.</b>" : ""); }; g.appendChild(b); });
    box.append(g, out);
  };

  R.P08 = function (box, d) {               // simulation: prisoner's dilemma
    var me = null, row = el("div", { class: "sim" }), msg = el("p", { class: "t-feedback" }), round = 0, log = el("p", { class: "t-small" }); msg.hidden = true;
    (d.choices || ["أسكت", "أعترف"]).forEach(function (c, i) { var b = el("button", { class: "t-choice", type: "button" }, c); b.onclick = function () { round++; var other = round === 1 ? (d.first == null ? 1 : d.first) : me; var key = String(i) + other; fb(msg, i === 0 && other === 0, "الجولة " + AR(round) + ": " + d.otherSays[other], d.out[key]); me = i; log.textContent = round > 1 ? (d.repeatNote || "") : ""; }; row.appendChild(b); });
    box.append(el("p", { class: "t-small" }, d.intro), row, msg, log);
  };

  R.P09 = function (box, d) {               // root family
    var r = el("div", { class: "root" }); r.appendChild(el("div", { class: "root__core", "aria-label": "الجذر" }, d.root));
    var shown = 0, more = el("button", { class: "t-btn", type: "button" }, "ولّد كلمة");
    var fam = el("div", { class: "root" });
    more.onclick = function () { if (shown >= d.family.length) return; var f = d.family[shown++]; fam.appendChild(el("div", { class: "t-kart t-kart--blue" }, "<b>" + f[0] + "</b><small>" + f[1] + "</small>")); if (shown === d.family.length) { more.disabled = true; more.textContent = "العائلة كاملة"; } };
    box.append(r, fam, el("div", { class: "row" })); box.lastChild.appendChild(more);
  };

  R.P10 = function (box, d) {               // report card + grade
    var f = el("div", { class: "fields" });
    d.fields.forEach(function (x) { var b = el("button", { type: "button", "aria-pressed": "false" }, "<b>" + x[0] + "</b><br>" + x[1]); b.onclick = function () { b.setAttribute("aria-pressed", b.getAttribute("aria-pressed") !== "true"); }; f.appendChild(b); });
    var gr = el("div", { class: "grade", role: "group", "aria-label": "الدرجة" }), msg = el("p", { class: "t-feedback" }); msg.hidden = true;
    d.grades.forEach(function (g) { var b = el("button", { class: "t-chip", type: "button", "aria-pressed": "false" }, g); b.onclick = function () { $$(".t-chip", gr).forEach(function (x) { x.setAttribute("aria-pressed", x === b); }); fb(msg, g === d.grades[2], "اخترت: " + g, d.note); }; gr.appendChild(b); });
    box.append(el("p", { class: "flag" }, d.flag), f, gr, msg);
  };

  function resolveAtlasUrl(relFromRoot, hashParams, customBase) {
    var base = customBase || (document.documentElement && document.documentElement.getAttribute && document.documentElement.getAttribute("data-atlas-root")) || "";
    var targetPath = relFromRoot || "index.html";
    var resolved = targetPath;
    try {
      if (base) {
        resolved = base.replace(/\/?$/, "/") + targetPath;
      } else if (RUNTIME_SRC) {
        resolved = new URL("../../" + targetPath, RUNTIME_SRC).href;
      } else {
        resolved = "../../" + targetPath;
      }
    } catch (err) {
      resolved = "../../" + targetPath;
    }
    var pairs = [];
    for (var k in (hashParams || {})) {
      if (hashParams[k] != null && hashParams[k] !== "") {
        pairs.push(encodeURIComponent(k) + "=" + encodeURIComponent(hashParams[k]));
      }
    }
    return pairs.length ? (resolved + "#" + pairs.join("&")) : resolved;
  }

  R.P11 = function (box, d) {               // timeline + interactive atlas deep-linking
    var tl = el("div", { class: "tl" }), out = el("div", { class: "t-feedback" });
    var wk = d.week || (DOC_WEEK && /^w\d+/i.test(DOC_WEEK) ? DOC_WEEK : "");
    out.innerHTML = "<strong>" + d.prompt + "</strong>";

    function normEvent(raw) {
      if (Array.isArray(raw)) {
        return { date: raw[0], text: raw[1], meta: raw[2] || null };
      }
      return { date: raw.date || raw[0] || "", text: raw.text || raw[1] || "", meta: raw };
    }

    function renderStation(ev) {
      var m = ev.meta || {};
      var gradeHtml = m.grade ? ' <span class="t-sanad">' + m.grade + "</span>" : "";
      var placeHtml = m.place ? '<div class="t-small" style="margin-top:4px">📍 ' + m.place + "</div>" : "";
      out.innerHTML = "<strong>" + ev.date + gradeHtml + "</strong><div>" + ev.text + "</div>" + placeHtml;

      var bar = el("div", { class: "t-atlas-bar" });
      var hasLinks = false;

      if (m.moduleUrl) {
        var modLink = el("a", { class: "t-atlas-link", href: resolveAtlasUrl(m.moduleUrl, m.moduleHash || {}, d.atlasRoot), target: "_blank", rel: "noopener" }, "🗺️ " + (m.label || "افتح في الأطلس التفاعلي ←"));
        bar.appendChild(modLink);
        hasLinks = true;
      } else if (m.page) {
        var hp = { page: m.page };
        if (m.hs) hp.hs = m.hs;
        if (m.ft) hp.ft = m.ft;
        if (wk) hp.week = wk;
        var mapLink = el("a", { class: "t-atlas-link", href: resolveAtlasUrl("index.html", hp, d.atlasRoot), target: "_blank", rel: "noopener" }, "🗺️ " + (m.label || "افتح الموضع في الأطلس ←"));
        bar.appendChild(mapLink);
        hasLinks = true;
      }

      if (m.cmp) {
        var cmpHp = { tab: "compare", cmp: m.cmp };
        if (wk) cmpHp.week = wk;
        var cmpLink = el("a", { class: "t-atlas-link t-atlas-link--sub", href: resolveAtlasUrl("index.html", cmpHp, d.atlasRoot), target: "_blank", rel: "noopener" }, "⚖️ " + (m.cmpLabel || "قارن الخريطتين ←"));
        bar.appendChild(cmpLink);
        hasLinks = true;
      }

      if (wk || d.unit) {
        var courseHp = { tab: "courses" };
        if (d.unit) courseHp.unit = d.unit;
        if (wk) courseHp.week = wk;
        var cLink = el("a", { class: "t-atlas-link t-atlas-link--sub", href: resolveAtlasUrl("index.html", courseHp, d.atlasRoot), target: "_blank", rel: "noopener" }, "🧭 مسار الدرس في الأطلس");
        bar.appendChild(cLink);
        hasLinks = true;
      }

      if (hasLinks) out.appendChild(bar);
    }

    d.events.forEach(function (rawEv) {
      var ev = normEvent(rawEv);
      var hasPin = ev.meta && (ev.meta.page || ev.meta.moduleUrl || ev.meta.cmp);
      var b = el("button", { type: "button", "aria-pressed": "false" }, ev.date + (hasPin ? " · 🗺️" : ""));
      b.onclick = function () {
        $$("button", tl).forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
        renderStation(ev);
      };
      tl.appendChild(b);
    });
    box.append(tl, out);
  };

  R.P12 = function (box, d) {               // two-pan balance
    var svg = '<svg viewBox="0 0 320 150" aria-hidden="true"><line class="ink" x1="160" y1="40" x2="160" y2="140"/><path class="ink" d="M120 140 h80"/><g class="beam"><line class="ink" x1="40" y1="40" x2="280" y2="40"/><path class="ink" d="M280 40 l-26 50 h52 z"/><path class="ink" d="M40 40 l-26 50 h52 z"/><text x="280" y="110" text-anchor="middle" font-size="12" fill="var(--pen-green)" id="pa">٠</text><text x="40" y="110" text-anchor="middle" font-size="12" fill="var(--pen-red)" id="pb">٠</text></g></svg>';
    var sc = el("div", { class: "scale" }, svg), pool = el("div", { class: "pool" }), a = 0, b = 0, row = el("div", { class: "row" }), sel = null;
    var pans = [el("button", { class: "t-btn t-btn--ghost", type: "button" }, d.pans[0]), el("button", { class: "t-btn t-btn--ghost", type: "button" }, d.pans[1])];
    var msg = el("p", { class: "t-feedback" }); msg.hidden = true;
    d.items.forEach(function (it) { var c = el("button", { class: "t-chip", type: "button", "aria-pressed": "false" }, it[0]); c._side = it[1]; c.onclick = function () { sel = c; $$(".t-chip", pool).forEach(function (x) { x.setAttribute("aria-pressed", x === c); }); }; pool.appendChild(c); });
    pans.forEach(function (p, side) { p.onclick = function () { if (!sel) return; if (sel._side !== side) { fb(msg, false, "الكفة التانية", "النص يضع هذه الواقعة في «" + d.pans[sel._side] + "»."); return; } side ? b++ : a++; sel.remove(); sel = null; msg.hidden = true; $("#pa", sc).textContent = AR(a); $("#pb", sc).textContent = AR(b); $(".beam", sc).style.transform = "rotate(" + Math.max(-12, Math.min(12, (b - a) * 4)) + "deg)"; if (!pool.children.length) fb(msg, true, "الكفتان في سجل واحد", d.done); }; row.appendChild(p); });
    box.append(sc, pool, row, msg);
  };

  R.P13 = function (box, d) {               // diagnose: the breaker
    var house = d.art || '<svg class="house" viewBox="0 0 360 200" aria-hidden="true"><circle class="glow" cx="160" cy="92" r="70"/><path class="ink" d="M40 100 L160 30 L280 100 M60 90 V180 H260 V90"/><line class="ink" x1="160" y1="30" x2="160" y2="70"/><circle class="bulb" cx="160" cy="82" r="12"/><path class="ink" d="M160 94 v6 M154 100 h12"/><path class="ink" d="M172 82 C220 82 230 120 300 120"/><rect class="ink" x="300" y="100" width="40" height="56" rx="3"/><path class="ink" d="M312 116 v20" stroke-width="4"/><rect class="ink" x="80" y="120" width="44" height="60"/></svg>';
    box.insertAdjacentHTML("beforeend", house);
    var svg = $(".house", box), opts = el("div", { class: "demo" }), msg = el("p", { class: "t-feedback" }); msg.hidden = true;
    d.tries.forEach(function (t) { var b = el("button", { class: "t-choice", type: "button" }, t.label); b.onclick = function () { if (t.fix) { svg.classList.add("is-lit"); b.classList.add("is-right"); fb(msg, true, t.label, t.say); } else { svg.classList.remove("is-flicker"); void svg.getBBox(); svg.classList.add("is-flicker"); b.classList.add("is-wrong"); fb(msg, false, "البيت لسه ضلمة", t.say); } }; opts.appendChild(b); });
    box.append(opts, msg);
  };

  R.P14 = function (box, d) {               // predict, replay later
    var g = el("div", { class: "demo" }), m = el("p", { class: "t-small" }, "مفيش إجابة غلط هنا. هنرجع لإجابتك في القفلة.");
    d.options.forEach(function (o) { var b = el("button", { class: "t-choice", type: "button", "aria-pressed": "false" }, o); b.onclick = function () { $$(".t-choice", g).forEach(function (x) { x.setAttribute("aria-pressed", x === b); }); store.set("predict", o); $$("[data-replay]").forEach(function (r) { r.textContent = "«" + o + "»"; }); m.textContent = d.saved || "اتسجلت. هنرجع لها في القفلة."; }; g.appendChild(b); });
    box.append(el("p", { class: "t-matn", style: "font-size:1.1rem" }, d.q), g, m);
    var prev = store.get("predict"); if (prev) $$("[data-replay]").forEach(function (r) { r.textContent = "«" + prev + "»"; });
  };

  R.P15 = function (box, d) {               // journal
    var wrap = el("div", { class: "journal demo" }), ta = el("textarea", { id: "journal-" + Math.random().toString(36).slice(2, 7), rows: "4", "aria-label": d.q });
    ta.value = store.get(d.key || "journal") || ""; var s = el("span", { class: "t-small" }, ta.value ? "محفوظ على جهازك" : "");
    ta.addEventListener("input", function () { store.set(d.key || "journal", ta.value); s.textContent = "محفوظ على جهازك"; });
    wrap.append(el("p", { class: "t-voice" }, d.q), ta, s); box.appendChild(wrap);
  };

  R.P16 = function (box, d) {               // sanad chain reveal
    var ch = el("div", { class: "chain" }), msg = el("p", { class: "t-small" }, "انقر كل حلقة لتكشفها."), n = 0;
    d.links.forEach(function (l, i) { if (i) ch.insertAdjacentHTML("beforeend", '<svg class="t-arrow" viewBox="0 0 48 20" aria-hidden="true"><path d="M44 10 C30 7 18 13 6 10 M12 4 L5 10 L12 16"/></svg>'); var k = el("button", { class: "t-kart t-kart--black", type: "button", "aria-expanded": "false" }, "<small>" + l[0] + "</small><span>" + l[1] + "</span>"); k.onclick = function () { if (k.getAttribute("aria-expanded") === "true") return; k.setAttribute("aria-expanded", "true"); if (++n === d.links.length) { msg.className = "t-feedback t-feedback--ok"; msg.innerHTML = "<strong>✓ السلسلة كاملة</strong>" + d.done; } }; ch.appendChild(k); });
    box.append(ch, msg);
  };

  R.P17 = function (box, d) {               // flip cards
    var g = el("div", { class: "flipgrid" });
    d.cards.forEach(function (c) { var b = el("button", { class: "flip", type: "button", "aria-pressed": "false" }, "<b>" + c[0] + "</b><span>انقر للقلب</span>"); b.onclick = function () { var on = b.getAttribute("aria-pressed") !== "true"; b.setAttribute("aria-pressed", on); b.innerHTML = "<b>" + c[0] + "</b><span>" + (on ? c[1] : "انقر للقلب") + "</span>"; }; g.appendChild(b); });
    box.appendChild(g);
  };

  R.P18 = function (box, d) {               // ladder / slider
    var id = "rng-" + Math.random().toString(36).slice(2, 7), r = el("input", { type: "range", min: "0", max: String(d.steps.length - 1), step: "1", value: "1", id: id, "aria-label": d.q });
    var t = el("div", { class: "ticks" }), out = el("p", { class: "t-feedback" });
    d.steps.forEach(function (s) { t.appendChild(el("span", {}, s[0])); });
    var show = function () { var s = d.steps[+r.value]; out.innerHTML = "<strong>" + s[0] + "</strong>" + s[1]; };
    r.addEventListener("input", show); show();
    box.append(el("p", { class: "t-small" }, d.q), r, t, out);
  };

  /* ---------- the six-atlas platform (repo root index.html) ----------
     Needs atlas-course-bundle.js (window.TaseesAtlas) and <html data-root="…/"> pointing at the repo root.
     Facts come from the atlas's verified hotspots; nothing here is typed by hand. */
  var ROOT = function () { return (document.documentElement.getAttribute("data-root") || ""); };
  var ATLAS = function () { return window.TaseesAtlas || { pages: {}, comparisons: {} }; };
  var atlasHref = function (pid, hid) { return ROOT() + "index.html#" + pid + (hid ? "~" + hid : ""); };
  var esc = function (t) { return String(t == null ? "" : t).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };

  function atlasFigure(p, opts) {             // one atlas page with hotspot boxes in % coordinates
    var fig = el("figure", { class: "atlas" });
    var scroller = el("div", { class: "atlas__scroll" });
    var sheet = el("div", { class: "atlas__sheet", style: "aspect-ratio:" + p.w + " / " + p.h });
    sheet.appendChild(el("img", { src: ROOT() + p.img, alt: p.title, loading: "lazy" }));
    // large boxes first, small ones on top, so a box nested inside another stays clickable; numbers keep atlas order
    (p.hotspots || []).map(function (h, i) { return [h, i]; })
      .sort(function (a, b) { return b[0].w * b[0].h - a[0].w * a[0].h; })
      .forEach(function (hi) {
      var h = hi[0], i = hi[1];
      var b = el("button", { type: "button", class: "atlas__hs" + (opts.hidden ? " is-hidden" : ""), "data-id": h.id,
        style: "left:" + h.x + "%;top:" + h.y + "%;width:" + h.w + "%;height:" + h.h + "%", "aria-label": h.name }, opts.hidden ? "" : "<span>" + AR(i + 1) + "</span>");
      b.onclick = function () { opts.onHit(h, b); };
      sheet.appendChild(b);
    });
    scroller.appendChild(sheet);
    var cap = el("figcaption", {}, esc(p.volume) + " · ص " + AR(p.printed) + " — " + esc(p.title) +
      ' · <a href="' + atlasHref(opts.pid) + '" target="_blank" rel="noopener">افتح في الأطلس الكامل ←</a>');
    var zoom = el("button", { type: "button", class: "t-chip atlas__zoom", "aria-pressed": "false" }, "تكبير");
    zoom.onclick = function () { var on = zoom.getAttribute("aria-pressed") !== "true"; zoom.setAttribute("aria-pressed", on); sheet.style.width = on ? "200%" : ""; };
    fig.append(zoom, scroller, cap);
    return fig;
  }

  R.P19 = function (box, d) {                // atlas page(s): explore every hotspot, or find named ones
    var A = ATLAS(), stations = d.stations || [["", d.page]], cur = 0;
    var bar = el("div", { class: "tl", role: "group", "aria-label": "المحطات" }), stage = el("div"), info = el("p", { class: "t-feedback" });
    var seen = {}, findIdx = 0;
    function show() {
      var pid = stations[cur][1], p = A.pages[pid];
      stage.innerHTML = "";
      if (!p) { stage.appendChild(el("p", { class: "t-feedback t-feedback--bad" }, "<strong>صفحة الأطلس غير موجودة في الحزمة</strong>" + esc(pid) + " — شغّل build_atlas_links.py")); return; }
      var finding = d.mode === "find" && d.find && findIdx < d.find.length;
      var target = finding ? p.hotspots.filter(function (h) { return h.id === d.find[findIdx]; })[0] : null;
      info.innerHTML = "<strong>" + esc(d.prompt || "") + "</strong>" + (target ? "ابحث على الخريطة عن: <b>" + esc(target.name) + "</b>" : "انقر الأرقام على الخريطة.");
      info.className = "t-feedback";
      stage.appendChild(atlasFigure(p, { pid: pid, hidden: finding, onHit: function (h, b) {
        if (finding) {
          if (h.id !== d.find[findIdx]) { fb(info, false, "مش ده المكان", "ده: " + esc(h.name) + ". دوّر تاني على: " + esc(target.name)); return; }
          findIdx++; b.classList.remove("is-hidden"); b.classList.add("is-found");
          if (findIdx < d.find.length) { var nx = p.hotspots.filter(function (x) { return x.id === d.find[findIdx]; })[0]; fb(info, true, h.name, esc(h.fact) + "<br>التالي: <b>" + esc(nx.name) + "</b>"); }
          else { show(); fb(info, true, h.name, esc(h.fact) + "<br>✓ لقيت كل الأماكن. الأرقام ظهرت: افتح الباقي."); }
          return;
        }
        seen[pid + h.id] = 1; $$(".atlas__hs", stage).forEach(function (x) { x.classList.toggle("is-open", x === b); });
        var total = stations.reduce(function (n, s) { return n + ((A.pages[s[1]] || {}).hotspots || []).length; }, 0);
        fb(info, true, h.name, esc(h.fact) + ' · <a href="' + atlasHref(pid, h.id) + '" target="_blank" rel="noopener">في الأطلس</a>' +
          (Object.keys(seen).length === total ? "<br><b>✓ فتحت كل المعالم.</b>" : ""));
      } }));
    }
    if (stations.length > 1) stations.forEach(function (s, i) { var b = el("button", { type: "button", "aria-pressed": String(i === 0) }, esc(s[0])); b.onclick = function () { cur = i; $$("button", bar).forEach(function (x) { x.setAttribute("aria-pressed", x === b); }); show(); }; bar.appendChild(b); });
    box.append.apply(box, (stations.length > 1 ? [bar] : []).concat([info, stage]));
    show();
  };

  R.P20 = function (box, d) {                // compare two atlas maps (the atlas's own comparison presets)
    var A = ATLAS(), c = A.comparisons[d.compare];
    if (!c) { box.appendChild(el("p", { class: "t-feedback t-feedback--bad" }, "<strong>المقارنة غير موجودة في الحزمة</strong>" + esc(d.compare))); return; }
    var L = A.pages[c.left], Rp = A.pages[c.right];
    box.appendChild(el("p", { class: "t-feedback" }, "<strong>" + esc(d.prompt || c.title) + "</strong>" + esc(c.title)));
    var wrap = el("div", { class: "atlas-cmp" + (c.registered ? " is-swipe" : "") });
    var pane = function (p, side) { return '<figure class="atlas-cmp__pane atlas-cmp__' + side + '"><div class="atlas__sheet" style="aspect-ratio:' + p.w + " / " + p.h + '"><img src="' + ROOT() + p.img + '" alt="' + esc(p.title) + '"></div><figcaption>' + esc(p.volume) + " · ص " + AR(p.printed) + " — " + esc(p.title) + "</figcaption></figure>"; };
    wrap.innerHTML = pane(L, "a") + pane(Rp, "b");   // RTL: the earlier map reads first (right)
    box.appendChild(wrap);
    if (c.registered) {                       // same base map: swipe one over the other
      var r = el("input", { type: "range", min: "0", max: "100", value: "50", "aria-label": "شريط المقارنة" });
      var top = $(".atlas-cmp__a", wrap), set = function () { top.style.clipPath = "inset(0 0 0 " + (100 - r.value) + "%)"; /* RTL: range grows leftwards; earlier map reveals from the right */ };
      r.addEventListener("input", set); set(); box.appendChild(r);
      box.appendChild(el("p", { class: "t-small atlas-cmp__legend" }, "يمين الشريط: " + esc(L.title) + " (" + esc(L.volume) + " · ص " + AR(L.printed) + ")<br>يسار الشريط: " + esc(Rp.title) + " (" + esc(Rp.volume) + " · ص " + AR(Rp.printed) + ")"));
    }
    box.appendChild(el("p", { class: "t-small" }, '<a href="' + ROOT() + "index.html#" + esc(d.compare) + '" target="_blank" rel="noopener">افتح المقارنة في الأطلس الكامل (تكبير متزامن) ←</a>' + (c.note ? " · " + esc(c.note) : "")));
  };


  window.Tasees = {
    render: function (box, pattern, data) { if (!R[pattern]) throw new Error("unknown pattern " + pattern); R[pattern](box, data); },
    patterns: Object.keys(R), AR: AR, el: el, store: store
  };
})();
