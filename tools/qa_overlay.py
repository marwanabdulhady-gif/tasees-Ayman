#!/usr/bin/env python3
"""QA: draw every resolved hotspot (blue), its linked marker (green) and every
label glyph path NOT linked to any transcription (red) over the page render."""
import json, os, sys
import pymupdf
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = json.load(open(os.path.join(ROOT, "data", "atlas.json"), encoding="utf-8"))
V = json.load(open(os.path.join(ROOT, "data", "vectors.json"), encoding="utf-8"))
doc = pymupdf.open(os.path.join(ROOT, "source", "islamic-history-maps.pdf"))
def inside(c, r): return r[0] <= c[0] <= r[2] and r[1] <= c[1] <= r[3]
for pno in [int(a) for a in sys.argv[1:]] or range(1, 9):
    S = float(os.environ.get("S", 2.2))
    clip = pymupdf.Rect(*[float(v) for v in os.environ["CLIP"].split(",")]) if os.environ.get("CLIP") else doc[pno-1].rect
    pix = doc[pno-1].get_pixmap(matrix=pymupdf.Matrix(S, S), clip=clip, alpha=False)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    T = lambda x, y: ((x - clip.x0) * S, (y - clip.y0) * S)
    feats = [f for f in A["features"] if f["page"] == pno]
    for f in feats:
        if f["poly"]:
            for ring in f["poly"]:
                dr.polygon([T(*p) for p in ring], outline=(0, 90, 255, 255), fill=(0, 90, 255, 40))
        else:
            for r in f["rects"]:
                dr.rectangle([*T(r[0], r[1]), *T(r[2], r[3])], outline=(0, 90, 255, 255), fill=(0, 90, 255, 40))
        if f["marker"]:
            x, y = T(*f["marker"]); dr.ellipse([x-5, y-5, x+5, y+5], outline=(0, 170, 0, 255), width=2)
            cx, cy = T((f["bbox"][0]+f["bbox"][2])/2, (f["bbox"][1]+f["bbox"][3])/2)
            dr.line([x, y, cx, cy], fill=(0, 170, 0, 160), width=1)
    pg = V["pages"][pno-1]
    for g in pg["glyphs"]:
        c = ((g[0]+g[2])/2, (g[1]+g[3])/2)
        if not any(inside(c, r) for f in feats for r in f["rects"]):
            dr.rectangle([*T(g[0], g[1]), *T(g[2], g[3])], outline=(230, 0, 0, 255), width=2)
    out = os.path.join(ROOT, "work", "layerqa", f"hotspots-p{pno}{os.environ.get('SUFFIX','')}.png")
    Image.alpha_composite(im, ov).convert("RGB").save(out); print(out)
