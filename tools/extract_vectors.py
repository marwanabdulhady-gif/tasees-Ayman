#!/usr/bin/env python3
"""
Vector forensics for the source atlas PDF.

The PDF contains NO text layer and NO fonts: every Arabic label is drawn as
filled vector outlines.  This script therefore works from the vector drawing
stream itself:

  1. Classifies every drawing path into a cartographic layer using its actual
     PDF paint attributes (fill colour, stroke colour/width, geometry).
  2. Exports each page as SVG (MuPDF) and tags every <path>/<image> with the
     layer class of the drawing it was produced from (1:1 order mapping is
     verified, the script aborts on any mismatch).
  3. Detects label glyph clusters (exact PDF-coordinate bounding boxes) and
     point markers (city dots) so that transcriptions can be anchored to the
     exact place they occupy on the printed page.
  4. Detects map frames and the two-page spread offset by matching identical
     geometry that is repeated on facing pages.

Outputs (all coordinates are PDF points, origin top-left, page 595x842):
  assets/svg/page-NNN.svg     layer-tagged vector page
  data/vectors.json           frames, spread offsets, layer stats, markers, clusters
"""
import collections
import json
import math
import os
import re
import sys

import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, "source", "islamic-history-maps.pdf")
SVG_DIR = os.path.join(ROOT, "assets", "svg")
OUT = os.path.join(ROOT, "data", "vectors.json")

LAYERS = {
    "base": "اليابسة والمسطحات المائية وخطوط السواحل",
    "border": "الحدود السياسية (خطوط رمادية رفيعة)",
    "buffer": "المنطقة الفاصلة (تنقيط)",
    "extent": "خط الامتداد (خط أسود عريض)",
    "marker": "علامات المواقع (نقاط)",
    "label": "التسميات والأرقام المكتوبة",
}


def lum(c):
    return sum(c) / 3.0 if c else None


def is_circle(d):
    its = d["items"]
    return len(its) == 4 and all(i[0] == "c" for i in its)


def classify(d):
    t = d["type"]
    r = d["rect"]
    f = d.get("fill")
    c = d.get("color")
    w = d.get("width") or 0
    fl = lum(f)
    if t == "f" and f is not None:
        if is_circle(d) and 0.25 < fl < 0.36 and r.width < 2.4 and r.height < 2.4:
            return "buffer"
        if 0.25 < fl < 0.36 and r.width < 9 and r.height < 9:
            return "buffer"          # stipple squares in the legend swatch
        if is_circle(d) and fl < 0.2 and 2.1 < r.width < 3.9 and abs(r.width - r.height) < 0.7:
            return "marker"
        if fl < 0.2:
            return "label"
        return "base"
    if t in ("s", "fs") and c is not None:
        cl = lum(c)
        if t == "s" and abs(w - 0.84) < 0.05 and 0.40 < cl < 0.47:
            return "border"
        if t == "s" and abs(w - 1.68) < 0.05 and cl < 0.2:
            return "extent"
    return "base"


GUTTER_CLIP = (75.0, 521.04)   # x-range of the map clip on every page (verified in SVG clipPaths)


def find_frame(page, side):
    """Measure the printed map border from a 4x greyscale raster.

    Each page holds one half of a two-page spread, so only three border lines
    are printed (top, bottom and the outer edge).  The inner edge is the clip
    boundary at the gutter.  side = 'east' | 'west'.
    """
    import numpy as np
    S = 4
    pix = page.get_pixmap(matrix=pymupdf.Matrix(S, S), alpha=False, colorspace=pymupdf.csGRAY)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    dark = a < 140
    rows = dark.mean(1)
    ys = [y / S for y in range(len(rows)) if rows[y] > 0.45]
    top, bottom = min(ys), max(ys)
    band = dark[int((top + 10) * S):int((bottom - 10) * S)].mean(0)
    xs = [x / S for x in range(len(band)) if band[x] > 0.9]
    if side == "east":
        x0, x1 = GUTTER_CLIP[0], max(xs)
    else:
        x0, x1 = min(xs), GUTTER_CLIP[1]
    return [round(x0, 2), round(top, 2), round(x1, 2), round(bottom, 2)]


def tag_svg(svg, drawings_classes, image_class, page_no):
    defs_end = svg.index("</defs>")
    head, body = svg[:defs_end], svg[defs_end:]
    # expected sequence of svg <path> elements after </defs>
    expected = []
    for cls, typ in drawings_classes:
        if typ == "fs":
            expected += [cls, cls]
        else:
            expected.append(cls)
    it = iter(expected)
    count = [0]

    def repl(m):
        count[0] += 1
        try:
            cls = next(it)
        except StopIteration:
            raise SystemExit(f"page {page_no}: more SVG paths than drawings")
        return m.group(0).replace("<path ", f'<path class="L-{cls}" ', 1)

    body = re.sub(r"<path ", lambda m: m.group(0), body)  # no-op, keeps intent explicit
    body = re.sub(r"<path [^>]*>", repl, body)
    if count[0] != len(expected):
        raise SystemExit(f"page {page_no}: svg paths {count[0]} != expected {len(expected)}")
    body = re.sub(r"<use ", f'<use class="L-{image_class}" ', body)
    body = body.replace("<image ", f'<image class="L-{image_class}" ')
    svg = head + body
    # namespace ids per page so several pages can live in one document
    svg = re.sub(r'id="(clip_|image_|mask_|pattern_|grad_)', rf'id="p{page_no}\1', svg)
    svg = re.sub(r'url\(#(clip_|image_|mask_|pattern_|grad_)', rf'url(#p{page_no}\1', svg)
    svg = re.sub(r'href="#(clip_|image_|mask_|pattern_|grad_)', rf'href="#p{page_no}\1', svg)
    svg = svg.replace(' xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"', "")
    # trim float noise e.g. 105.12000004 -> 105.12
    svg = re.sub(r"(\d+\.\d{2})\d+", r"\1", svg)
    return svg, len(expected)


def cluster_labels(rects, gx=1.7, gy=0.9):
    """Union-find of glyph boxes into words/lines (same baseline band)."""
    n = len(rects)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(n):
        a = rects[i]
        for j in range(i + 1, n):
            b = rects[j]
            if a[0] - gx > b[2] or b[0] - gx > a[2] or a[1] - gy > b[3] or b[1] - gy > a[3]:
                continue
            # require a reasonable vertical overlap (same text line) unless one is a
            # small diacritic/dot sitting above/below the other
            ov = min(a[3], b[3]) - max(a[1], b[1])
            ha, hb = a[3] - a[1], b[3] - b[1]
            small = min(a[2] - a[0], b[2] - b[0]) < 2.6 and min(ha, hb) < 2.6
            if ov > 0.25 * min(ha, hb) or small:
                parent[find(i)] = find(j)
    groups = collections.defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    out = []
    for g in groups.values():
        xs0 = min(rects[i][0] for i in g)
        ys0 = min(rects[i][1] for i in g)
        xs1 = max(rects[i][2] for i in g)
        ys1 = max(rects[i][3] for i in g)
        out.append(dict(bbox=[round(xs0, 2), round(ys0, 2), round(xs1, 2), round(ys1, 2)], glyphs=len(g)))
    out.sort(key=lambda c: (round(c["bbox"][1] / 6), -c["bbox"][2]))
    return out


def spread_offset(doc, a, b):
    def sigs(p):
        res = []
        for x in p.get_drawings():
            if len(x["items"]) < 8:
                continue
            r = x["rect"]
            res.append(((len(x["items"]), round(r.width, 1), round(r.height, 1), x["type"]), r))
        return res

    A, B = sigs(doc[a - 1]), sigs(doc[b - 1])
    idx = collections.defaultdict(list)
    for s, r in B:
        idx[s].append(r)
    c = collections.Counter()
    for s, r in A:
        for rb in idx.get(s, []):
            c[(round(r.x0 - rb.x0, 1), round(r.y0 - rb.y0, 1))] += 1
    (dx, dy), votes = c.most_common(1)[0]
    return dict(dx=dx, dy=dy, votes=votes)


def main():
    os.makedirs(SVG_DIR, exist_ok=True)
    doc = pymupdf.open(PDF)
    pages = []
    for pno, page in enumerate(doc, start=1):
        drs = page.get_drawings()
        classes = []
        stats = collections.Counter()
        label_rects, markers = [], []
        for d in drs:
            cls = classify(d)
            classes.append((cls, d["type"]))
            stats[cls] += 1
            r = d["rect"]
            if cls == "label":
                label_rects.append((r.x0, r.y0, r.x1, r.y1))
            if cls == "marker" or (cls == "label" and is_circle(d) and 1.5 < r.width <= 2.1
                                   and abs(r.width - r.height) < 0.5):
                # small round dots (e.g. page 4 city dots) stay in the label layer for
                # rendering, but are also recorded as point markers for association.
                markers.append([round((r.x0 + r.x1) / 2, 2), round((r.y0 + r.y1) / 2, 2), round(r.width, 2)])
        n_images = len(page.get_images())
        stats["buffer_images"] = n_images
        svg = page.get_svg_image(text_as_path=True)
        svg, n_paths = tag_svg(svg, classes, "buffer", pno)
        with open(os.path.join(SVG_DIR, f"page-{pno:03d}.svg"), "w", encoding="utf-8") as fh:
            fh.write(svg)
        frame = find_frame(page, "east" if pno % 2 == 1 else "west")
        clusters = cluster_labels(label_rects)
        import hashlib as _h
        sig = _h.sha1(json.dumps([c["bbox"] for c in clusters]).encode()).hexdigest()[:12]
        pages.append(dict(
            page=pno,
            size=[page.rect.width, page.rect.height],
            frame=frame,
            drawings=len(drs),
            svgPaths=n_paths,
            svgBytes=len(svg.encode("utf-8")),
            layerStats=dict(stats),
            markers=markers,
            clusters=clusters,
            clusterSignature=sig,
            glyphs=[[round(v, 2) for v in r] for r in label_rects],
        ))
        print(f"page {pno}: drawings={len(drs)} svg={len(svg)//1024}KB frame={frame} "
              f"labels-glyph-paths={stats['label']} clusters={len(clusters)} markers={len(markers)} {dict(stats)}")
    spreads = []
    for east, west in [(1, 2), (3, 4), (5, 6), (7, 8)]:
        off = spread_offset(doc, east, west)
        # Geometry repeated on both pages of a spread is shifted by exactly the clip
        # width (445.9pt ~ 521.04-75).  For spread 3/4 a coincidental shape match
        # out-votes it 4:3; the 445.9 join was verified visually (continuous coasts,
        # conquest arrows and labels across the gutter) for all four spreads.
        cands = off
        dx = 445.9
        spreads.append(dict(east=east, west=west, eastOffsetX=dx, matchVotes=cands,
                            verification="visual: coastlines and gutter-crossing labels continuous"))
        print("spread", east, west, "auto-vote", off, "-> using", dx)
    json.dump(dict(source=os.path.basename(PDF), layers=LAYERS, pages=pages, spreads=spreads),
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
