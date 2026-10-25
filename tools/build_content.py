#!/usr/bin/env python3
"""
Build the source-of-truth content manifest (data/atlas.json) from:
  * data/vectors.json            (vector forensics: frames, glyph boxes, markers)
  * data/transcriptions/*.json   (visual transcriptions anchored to glyph clusters)

Every feature keeps a traceable link to its PDF page and to the exact PDF-point
geometry of the printed label.  Nothing here invents content: features exist
only where a printed label was transcribed.
"""
import collections
import glob
import hashlib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = json.load(open(os.path.join(ROOT, "data", "vectors.json"), encoding="utf-8"))
PDF = os.path.join(ROOT, "source", "islamic-history-maps.pdf")
OUT = os.path.join(ROOT, "data", "atlas.json")

OFFSET = 445.9
KIND_AR = {
    "caption": "تعليق الشكل",
    "legend": "مفتاح الخريطة",
    "country": "دولة",
    "polity": "كيان سياسي",
    "people": "شعب / جماعة",
    "place": "مدينة / موقع",
    "region": "إقليم / منطقة",
    "water": "مسطح مائي",
    "river": "نهر",
    "line": "خط مرجعي",
    "date": "رقم / سنة",
    "unreadable": "غير مقروء",
    "other": "أخرى",
}
CONF_AR = {"high": "عالية", "medium": "متوسطة", "low": "منخفضة"}

# figures in PDF order; east page holds the caption (except figure 1-3? no: all east)
FIGURES = [
    dict(id="fig-2", east=1, west=2),
    dict(id="fig-1-1", east=3, west=4),
    dict(id="fig-1-3", east=5, west=6),
    dict(id="fig-1-4", east=7, west=8),
]
# Registration of figure 1-1 onto figure 1-4 (same base map), measured by
# cross-correlating base-layer renders (see README / audit).
REGISTRATION = {"fig-1-1->fig-1-4": {"east": [-0.5, -0.5], "west": [-1.0, -1.0]}}

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
TASHKEEL = re.compile("[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")


def normalize(s):
    s = TASHKEEL.sub("", s)
    s = s.replace("\u0640", "")
    s = re.sub("[أإآٱ]", "ا", s)
    s = s.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    s = s.translate(AR_DIGITS)
    s = re.sub(r"[\-–—_/\\.,:؛،()«»\"'…]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def union(rects):
    return [round(min(r[0] for r in rects), 2), round(min(r[1] for r in rects), 2),
            round(max(r[2] for r in rects), 2), round(max(r[3] for r in rects), 2)]


def area(r):
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def center(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def inside(pt, r):
    return r[0] <= pt[0] <= r[2] and r[1] <= pt[1] <= r[3]


def dist_rect(pt, r):
    dx = max(r[0] - pt[0], 0, pt[0] - r[2])
    dy = max(r[1] - pt[1], 0, pt[1] - r[3])
    return (dx * dx + dy * dy) ** 0.5


def main():
    pages = {p["page"]: p for p in V["pages"]}
    trans = {}
    for fn in sorted(glob.glob(os.path.join(ROOT, "data", "transcriptions", "page-*.json"))):
        t = json.load(open(fn, encoding="utf-8"))
        trans[t["page"]] = t

    features = []
    warnings = []
    page_stats = {}
    for pno in range(1, 9):
        pg = pages[pno]
        t = trans.get(pno, {"features": []})
        if t.get("clusterSignature") and t["clusterSignature"] != pg["clusterSignature"]:
            raise SystemExit(f"page {pno}: transcription was made against cluster set "
                             f"{t['clusterSignature']} but vectors.json has {pg['clusterSignature']}. "
                             "Cluster ids would be misaligned - re-check transcriptions.")
        clusters = pg["clusters"]
        glyphs = pg["glyphs"]
        used_clusters = set()
        # ---- approx snapping: each glyph goes to the smallest approx rect containing its centre
        approx_owner = {}
        approx_rects = []
        for fi, f in enumerate(t["features"]):
            for ri, r in enumerate(f.get("approx", [])):
                approx_rects.append((area(r), fi, ri, r))
        approx_rects.sort()
        for gi, g in enumerate(glyphs):
            c = center(g)
            for _, fi, ri, r in approx_rects:
                if inside(c, r):
                    approx_owner[gi] = (fi, ri)
                    break
        # Region growing: rotated labels often poke out of the hand-drawn box.
        # Absorb unowned glyphs that touch (<=0.9pt gap) an owned glyph, max 3 rounds.
        # Glyphs referenced by explicit cluster ids are never absorbed.
        id_glyphs = set()
        for f in t["features"]:
            for cid in f.get("ids", []):
                if cid < len(clusters):
                    b = clusters[cid]["bbox"]
                    for gi, g in enumerate(glyphs):
                        if inside(center(g), b):
                            id_glyphs.add(gi)
        GAP = 0.9
        for _ in range(3 if t.get("growApprox") else 0):
            added = {}
            for gi, g in enumerate(glyphs):
                if gi in approx_owner or gi in id_glyphs:
                    continue
                for gj, own in approx_owner.items():
                    h = glyphs[gj]
                    if g[0] - GAP <= h[2] and h[0] - GAP <= g[2] and g[1] - GAP <= h[3] and h[1] - GAP <= g[3]:
                        added[gi] = own
                        break
            if not added:
                break
            approx_owner.update(added)
        owned = collections.defaultdict(list)
        for gi, (fi, ri) in approx_owner.items():
            owned[(fi, ri)].append(glyphs[gi])

        for fi, f in enumerate(t["features"]):
            rects, source = [], None
            if "ids" in f:
                for cid in f["ids"]:
                    if cid >= len(clusters):
                        warnings.append(f"page {pno}: cluster {cid} out of range for {f['text']}")
                        continue
                    rects.append(clusters[cid]["bbox"])
                    used_clusters.add(cid)
                source = "glyph-clusters"
            if "approx" in f:
                for ri, r in enumerate(f["approx"]):
                    gs = owned.get((fi, ri), [])
                    if gs:
                        rects.append(union(gs))
                    else:
                        warnings.append(f"page {pno}: approx box {r} for «{f['text']}» captured no glyphs; using box as drawn")
                        rects.append(r)
                source = "snapped-approx"
            poly = None
            if "poly" in f:
                poly = [[[round(x, 2), round(y, 2)] for x, y in ring] for ring in f["poly"]]
                pts = [p for ring in poly for p in ring]
                rects.append(union([[p[0], p[1], p[0], p[1]] for p in pts]))
                source = "manual-polygon"
            bbox = union(rects)
            features.append(dict(
                page=pno, text=f["text"], kind=f["kind"], bold=bool(f.get("bold")),
                conf=f.get("conf", "medium"), note=f.get("note"), crossPage=f.get("crossPage"),
                rects=[[round(v, 2) for v in r] for r in rects], poly=poly, bbox=bbox,
                geometrySource=source,
            ))
        # stats: clusters never referenced by ids and glyphs never owned
        referenced_glyphs = set(approx_owner.keys())
        for cid in used_clusters:
            b = clusters[cid]["bbox"]
            for gi, g in enumerate(glyphs):
                if inside(center(g), b):
                    referenced_glyphs.add(gi)
        for f in features:
            if f["page"] == pno and f["poly"]:
                for gi, g in enumerate(glyphs):
                    if inside(center(g), f["bbox"]):
                        referenced_glyphs.add(gi)
        page_stats[pno] = dict(
            labelGlyphPaths=len(glyphs),
            glyphClusters=len(clusters),
            glyphPathsLinkedToTranscription=len(referenced_glyphs),
            glyphPathsNotLinked=len(glyphs) - len(referenced_glyphs),
            markers=len(pg["markers"]),
        )

    # ---- ids, normalisation, figure membership, spread coordinates
    fig_of_page = {}
    for f in FIGURES:
        fig_of_page[f["east"]] = (f["id"], "east")
        fig_of_page[f["west"]] = (f["id"], "west")
    counters = collections.Counter()
    for f in features:
        counters[f["page"]] += 1
        f["id"] = f"p{f['page']}-{counters[f['page']]:03d}"
        f["norm"] = normalize(f["text"])
        f["kindLabel"] = KIND_AR[f["kind"]]
        fid, half = fig_of_page[f["page"]]
        f["figure"] = fid
        f["half"] = half
        dx = OFFSET if half == "east" else 0.0
        f["spreadRects"] = [[round(r[0] + dx, 2), r[1], round(r[2] + dx, 2), r[3]] for r in f["rects"]]
        f["spreadPoly"] = [[[round(x + dx, 2), y] for x, y in ring] for ring in f["poly"]] if f["poly"] else None

    # ---- marker association (each dot -> nearest place-like label within 14pt)
    place_kinds = {"place", "region", "polity", "country", "people"}
    marker_links = []
    for pno in range(1, 9):
        cands = [f for f in features if f["page"] == pno and f["kind"] in place_kinds]
        taken = {}
        for mi, (mx, my, mw) in enumerate(pages[pno]["markers"]):
            best = None
            for f in cands:
                d = min(dist_rect((mx, my), r) for r in f["rects"])
                if d <= 14 and (best is None or d < best[0]):
                    best = (d, f)
            if best:
                d, f = best
                prev = taken.get(f["id"])
                if prev is None or d < prev[0]:
                    taken[f["id"]] = (d, mx, my, mi)
        for f in cands:
            if f["id"] in taken:
                d, mx, my, mi = taken[f["id"]]
                f["marker"] = [mx, my]
                dx = OFFSET if f["half"] == "east" else 0.0
                f["spreadMarker"] = [round(mx + dx, 2), my]
                marker_links.append(mi)
        pages[pno]["_linkedMarkers"] = len(taken)
    for f in features:
        f.setdefault("marker", None)
        f.setdefault("spreadMarker", None)

    # ---- occurrences of the same (normalised) name across the atlas
    by_norm = collections.defaultdict(list)
    for f in features:
        if f["kind"] not in ("caption", "legend", "date", "unreadable"):
            by_norm[f["norm"]].append(f["id"])
    for f in features:
        f["sameName"] = [i for i in by_norm.get(f["norm"], []) if i != f["id"]]

    # ---- composite: gutter-crossing label المحيط (p1) + الهندي (p2)
    composites = []
    a = next((f for f in features if f["page"] == 1 and f["text"] == "المحيط"), None)
    b = next((f for f in features if f["page"] == 2 and f["text"] == "الهندي"), None)
    if a and b:
        composites.append(dict(id="fig-2-c1", figure="fig-2", text="المحيط الهندي", norm=normalize("المحيط الهندي"),
                               parts=[a["id"], b["id"]], kind="water", kindLabel=KIND_AR["water"],
                               note="تسمية واحدة تمتد عبر حافة التقاء الصفحتين ١ و٢"))

    # ---- figures
    figs = []
    for f in FIGURES:
        e, w = pages[f["east"]], pages[f["west"]]
        cap = next((x for x in features if x["page"] in (f["east"], f["west"]) and x["kind"] == "caption"), None)
        legend = [x for x in features if x["page"] in (f["east"], f["west"]) and x["kind"] == "legend"]
        m = re.match(r"شكل\s*([٠-٩\-]+)\s*:\s*(.+?)\.?$", cap["text"]) if cap else None
        number, title = (m.group(1), m.group(2)) if m else (None, None)
        x0 = w["frame"][0]
        x1 = e["frame"][2] + OFFSET
        y0 = min(e["frame"][1], w["frame"][1])
        y1 = max(e["frame"][3], w["frame"][3])
        layer_counts = collections.Counter()
        for p in (e, w):
            for k, v in p["layerStats"].items():
                layer_counts[k] += v
        feats = [x for x in features if x["figure"] == f["id"]]
        figs.append(dict(
            id=f["id"], eastPage=f["east"], westPage=f["west"], pages=[f["east"], f["west"]],
            caption=cap["text"] if cap else None, captionFeature=cap["id"] if cap else None,
            captionPage=cap["page"] if cap else None, number=number, title=title,
            spreadViewBox=[round(x0, 2), round(y0, 2), round(x1 - x0, 2), round(y1 - y0, 2)],
            westClip=[w["frame"][0], w["frame"][1], 521.04, w["frame"][3]],
            eastClip=[75.0, e["frame"][1], e["frame"][2], e["frame"][3]],
            eastOffsetX=OFFSET,
            layers={k: int(v) for k, v in layer_counts.items()},
            legend=[dict(text=x["text"], feature=x["id"], symbol="stipple",
                         meaning="المساحات المنقطة على الخريطة") for x in legend],
            featureCount=len([x for x in feats if x["kind"] not in ("caption", "legend")]),
        ))

    # ---- pages
    out_pages = []
    for pno in range(1, 9):
        pg = pages[pno]
        fid, half = fig_of_page[pno]
        fig = next(x for x in figs if x["id"] == fid)
        feats = [x for x in features if x["page"] == pno]
        needs_review = [x["id"] for x in feats if x["conf"] == "low" or x["kind"] == "unreadable"]
        st = page_stats[pno]
        out_pages.append(dict(
            page=pno, id=f"page-{pno:03d}", figure=fid, half=half,
            halfLabel="النصف الشرقي من الخريطة" if half == "east" else "النصف الغربي من الخريطة",
            title=(fig["caption"] or "") + (" — " + ("النصف الشرقي" if half == "east" else "النصف الغربي")),
            hasCaption=bool(fig["captionPage"] == pno),
            size=pg["size"], frame=pg["frame"],
            textLayer=False, fonts=0, rasterImages=pg["layerStats"].get("buffer_images", 0),
            vectorDrawings=pg["drawings"],
            layerStats=pg["layerStats"],
            transcribedFeatures=len(feats),
            lowConfidence=len([x for x in feats if x["conf"] == "low"]),
            mediumConfidence=len([x for x in feats if x["conf"] == "medium"]),
            stats=st,
            linkedMarkers=pg.get("_linkedMarkers", 0),
            needsReview=needs_review,
            verificationStatus=("partially-transcribed" if trans.get(pno, {}).get("completeness") == "partial"
                                or st["glyphPathsNotLinked"] > 0.15 * st["labelGlyphPaths"] else "transcribed-visually"),
            completenessNote=trans.get(pno, {}).get("completenessNote"),
        ))

    md5 = hashlib.md5(open(PDF, "rb").read()).hexdigest()
    totals = dict(
        pdfPages=8, pagesProcessed=8, figures=len(figs), mapHalves=8,
        pagesWithTextLayer=0, pagesRequiringVisualTranscription=8,
        transcribedFeatures=len(features),
        searchableEntries=len([f for f in features if f["kind"] not in ("caption",)]) + len(composites),
        interactiveHotspots=len([f for f in features if f["kind"] not in ("caption",)]),
        uniqueNames=len(by_norm),
        namesOnMultipleFigures=len([k for k, v in by_norm.items()
                                    if len({next(f["figure"] for f in features if f["id"] == i) for i in v}) > 1]),
        lowConfidence=len([f for f in features if f["conf"] == "low"]),
        mediumConfidence=len([f for f in features if f["conf"] == "medium"]),
        markersDetected=sum(len(p["markers"]) for p in V["pages"]),
        markersLinked=sum(p.get("_linkedMarkers", 0) for p in V["pages"]),
        labelGlyphPaths=sum(s["labelGlyphPaths"] for s in page_stats.values()),
        labelGlyphPathsLinked=sum(s["glyphPathsLinkedToTranscription"] for s in page_stats.values()),
    )
    atlas = dict(
        schema="atlas-manifest/1",
        source=dict(file="islamic-history-maps.pdf",
                    originalName="خرائط التاريخ الإسلامي مجمع.pdf",
                    md5=md5, bytes=os.path.getsize(PDF), pdfTitleMetadata="التاريخ_الإسلامي.pdf",
                    producer="pdfFactory Pro 4.50", created="2016-12-24",
                    pageSize="595×842 pt (A4 portrait)",
                    drive="https://drive.google.com/file/d/1AQS8YInYN9AdjpRxv-rY9v_zWCSMDRt_/view"),
        kinds=KIND_AR, confidence=CONF_AR,
        layers=V["layers"],
        registration=REGISTRATION,
        figures=figs, pages=out_pages, features=features, composites=composites,
        totals=totals, warnings=warnings,
    )
    json.dump(atlas, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(totals, ensure_ascii=False, indent=1))
    for w in warnings:
        print("WARN", w)
    for p in out_pages:
        print(p["page"], p["verificationStatus"], p["stats"], "features", p["transcribedFeatures"], "linkedMarkers", p["linkedMarkers"])


if __name__ == "__main__":
    main()
