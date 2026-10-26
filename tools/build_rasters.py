#!/usr/bin/env python3
"""Independent raster renders (MuPDF, straight from the PDF) used for the
original-page verification view, plus thumbnails for navigation."""
import json, os
import pymupdf
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = json.load(open(os.path.join(ROOT, "data", "atlas.json"), encoding="utf-8"))
doc = pymupdf.open(os.path.join(ROOT, "source", "islamic-history-maps.pdf"))
os.makedirs(os.path.join(ROOT, "assets", "pages"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "assets", "thumbs"), exist_ok=True)
def pil(pix): return Image.frombytes("L" if pix.n == 1 else "RGB", (pix.width, pix.height), pix.samples)
for i, p in enumerate(doc, start=1):
    im = pil(p.get_pixmap(matrix=pymupdf.Matrix(2.5, 2.5), alpha=False, colorspace=pymupdf.csGRAY))
    im.save(os.path.join(ROOT, "assets", "pages", f"page-{i:03d}.webp"), "WEBP", quality=82, method=6)
    t = im.copy(); t.thumbnail((180, 260), Image.LANCZOS)
    t.save(os.path.join(ROOT, "assets", "thumbs", f"page-{i:03d}.webp"), "WEBP", quality=80, method=6)
# spread thumbnails (joined halves, map frame only)
out = pymupdf.open()
for f in A["figures"]:
    x, y, w, h = f["spreadViewBox"]
    pg = out.new_page(width=w, height=h)
    wc = pymupdf.Rect(*f["westClip"]); ec = pymupdf.Rect(*f["eastClip"])
    pg.show_pdf_page(pymupdf.Rect(wc.x0 - x, wc.y0 - y, wc.x1 - x, wc.y1 - y), doc, f["westPage"] - 1, clip=wc)
    pg.show_pdf_page(pymupdf.Rect(ec.x0 + f["eastOffsetX"] - x, ec.y0 - y, ec.x1 + f["eastOffsetX"] - x, ec.y1 - y), doc, f["eastPage"] - 1, clip=ec)
    im = pil(pg.get_pixmap(matrix=pymupdf.Matrix(0.62, 0.62), alpha=False, colorspace=pymupdf.csGRAY))
    im.save(os.path.join(ROOT, "assets", "thumbs", f"{f['id']}.webp"), "WEBP", quality=80, method=6)
    print(f["id"], im.size)
for d in ("pages", "thumbs"):
    tot = sum(os.path.getsize(os.path.join(ROOT, "assets", d, x)) for x in os.listdir(os.path.join(ROOT, "assets", d)))
    print(d, len(os.listdir(os.path.join(ROOT, "assets", d))), "files", tot // 1024, "KB")
