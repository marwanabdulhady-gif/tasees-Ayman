/* ===== mapview.js — builds interactive map SVGs from the vector pages ===== */
"use strict";
const MapView = (() => {
  let uid = 0;

  /** Nested <svg> containing one full PDF page (vector), or its raster render as fallback. */
  async function pageNode(pageNo, { forceRaster = false } = {}) {
    const nested = s("svg", { x: 0, y: 0, width: 595, height: 842, viewBox: "0 0 595 842", overflow: "hidden" });
    let vector = false;
    if (!forceRaster) {
      const doc = await Assets.pageSvg(pageNo);
      if (doc) {
        const root = doc.documentElement;
        for (const child of Array.from(root.childNodes)) nested.appendChild(document.importNode(child, true));
        vector = true;
      }
    }
    if (!vector) {
      nested.appendChild(s("image", { href: Assets.pageImage(pageNo), x: 0, y: 0, width: 595, height: 842, preserveAspectRatio: "none" }));
    }
    return { node: nested, vector };
  }

  function baseSvg(viewBox) {
    const svg = s("svg", { class: "map-svg", viewBox: viewBox.join(" "), role: "img" });
    const defs = s("defs");
    svg.appendChild(defs);
    return { svg, defs };
  }

  function addHotspots(svg, features, coord) {
    const g = s("g", { class: "hotspots" });
    const byId = new Map();
    for (const f of features) {
      const hs = s("g", { class: `hs kind-${f.kind} conf-${f.conf}`, "data-id": f.id });
      const rects = coord === "spread" ? f.spreadRects : f.rects;
      const polys = coord === "spread" ? f.spreadPoly : f.poly;
      const t = s("title"); t.textContent = f.text; hs.appendChild(t);
      if (polys) {
        for (const ring of polys) hs.appendChild(s("polygon", { class: "hs-shape", points: ring.map((p) => p.join(",")).join(" ") }));
      } else {
        for (const r of rects) {
          const pad = 0.9;
          hs.appendChild(s("rect", { class: "hs-shape", x: (r[0] - pad).toFixed(2), y: (r[1] - pad).toFixed(2), width: (r[2] - r[0] + 2 * pad).toFixed(2), height: (r[3] - r[1] + 2 * pad).toFixed(2), rx: 1.2 }));
        }
      }
      g.appendChild(hs); byId.set(f.id, hs);
    }
    svg.appendChild(g);
    const sel = s("g", { class: "selection" });
    svg.appendChild(sel);
    return { group: g, sel, byId };
  }

  /** Joined two-page spread for a figure (west half + east half offset by 445.9pt). */
  async function spread(fig, { hotspots = true, features = null, translate = null } = {}) {
    const vb = fig.spreadViewBox;
    const { svg, defs } = baseSvg(vb);
    const id = ++uid;
    const cw = fig.westClip, ce = fig.eastClip, off = fig.eastOffsetX;
    const cpW = s("clipPath", { id: `cw${id}` }); cpW.appendChild(s("rect", { x: cw[0], y: cw[1], width: cw[2] - cw[0], height: cw[3] - cw[1] }));
    const cpE = s("clipPath", { id: `ce${id}` }); cpE.appendChild(s("rect", { x: ce[0] + off, y: ce[1], width: ce[2] - ce[0], height: ce[3] - ce[1] }));
    defs.append(cpW, cpE);
    svg.appendChild(s("rect", { class: "paper", x: vb[0] - 4, y: vb[1] - 4, width: vb[2] + 8, height: vb[3] + 8 }));
    const [w, e] = await Promise.all([pageNode(fig.westPage), pageNode(fig.eastPage)]);
    const tw = translate ? translate.west : [0, 0], te = translate ? translate.east : [0, 0];
    const gW = s("g", { "clip-path": `url(#cw${id})` });
    const inW = s("g", { transform: `translate(${tw[0]} ${tw[1]})` }); inW.appendChild(w.node); gW.appendChild(inW);
    const gE = s("g", { "clip-path": `url(#ce${id})` });
    const inE = s("g", { transform: `translate(${off + te[0]} ${te[1]})` }); inE.appendChild(e.node); gE.appendChild(inE);
    svg.append(gW, gE);
    svg.appendChild(s("rect", { class: "frame-shadow", x: vb[0], y: vb[1], width: vb[2], height: vb[3] }));
    let hs = null;
    if (hotspots) {
      const feats = (features || Atlas.featuresOf(fig.id)).filter((f) => f.kind !== "caption");
      hs = addHotspots(svg, feats, "spread");
    }
    svg.setAttribute("aria-label", `${fig.caption || ""} — خريطة مركّبة من الصفحتين ${toArabicDigits(fig.westPage)} و${toArabicDigits(fig.eastPage)}`);
    return { svg, content: vb, hs, vector: w.vector && e.vector, coord: "spread" };
  }

  /** One original PDF page. mode: 'raster' (independent MuPDF render) | 'vector'. */
  async function page(pageNo, { mode = "raster", hotspots = false } = {}) {
    const vb = [0, 0, 595, 842];
    const { svg } = baseSvg(vb);
    svg.appendChild(s("rect", { class: "paper", x: 0, y: 0, width: 595, height: 842 }));
    const p = await pageNode(pageNo, { forceRaster: mode === "raster" });
    svg.appendChild(p.node);
    let hs = null;
    if (hotspots) hs = addHotspots(svg, Atlas.featuresOnPage(pageNo), "page");
    svg.setAttribute("aria-label", `الصفحة ${toArabicDigits(pageNo)} من ملف PDF (${mode === "raster" ? "صورة مستخرجة من الملف" : "رسومات متجهية"})`);
    return { svg, content: vb, hs, vector: p.vector, coord: "page" };
  }

  function setLayers(svg, hidden) {
    for (const k of ["label", "marker", "border", "buffer", "extent", "base"]) svg.classList.toggle("hide-" + k, hidden.has(k));
  }

  /** Draw selection highlight (+ marker ring & connector when a marker dot is linked). */
  function select(view, f) {
    if (!view || !view.hs) return;
    for (const el of view.hs.group.querySelectorAll(".hs.selected")) el.classList.remove("selected");
    view.hs.sel.replaceChildren();
    if (!f) return;
    const el = view.hs.byId.get(f.id);
    if (el) { el.classList.add("selected"); }
    const m = view.coord === "spread" ? f.spreadMarker : f.marker;
    if (m) {
      const bb = view.coord === "spread" ? Atlas.spreadBBox(f) : f.bbox;
      const cx = (bb[0] + bb[2]) / 2, cy = (bb[1] + bb[3]) / 2;
      view.hs.sel.append(
        s("line", { class: "sel-link", x1: m[0], y1: m[1], x2: cx, y2: cy }),
        s("circle", { class: "sel-marker pulse", cx: m[0], cy: m[1], r: 4.2 }),
      );
    }
  }

  return { spread, page, setLayers, select };
})();
