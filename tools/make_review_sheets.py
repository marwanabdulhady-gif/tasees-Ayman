#!/usr/bin/env python3
"""Render numbered review sheets: every detected label cluster (red box + id)
and point marker (blue ring) over a high-resolution render of the page.
Used to transcribe the vector-outlined Arabic labels and anchor each
transcription to exact PDF coordinates.  Output goes to work/sheets/ (scratch).
"""
import json
import os
import sys

import pymupdf
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = json.load(open(os.path.join(ROOT, "data", "vectors.json"), encoding="utf-8"))
doc = pymupdf.open(os.path.join(ROOT, "source", "islamic-history-maps.pdf"))
OUT = os.path.join(ROOT, "work", "sheets")
os.makedirs(OUT, exist_ok=True)

# page -> (scale, list of tile rects in PDF points)
def tiles_for(pno, frame):
    x0, y0, x1, y1 = 70, 60, 525, 790
    if pno == 2:
        cols, rows, S = 3, 4, 5.0
    elif pno in (1, 4):
        cols, rows, S = 2, 3, 3.6
    else:
        cols, rows, S = 2, 2, 3.0
    w = (x1 - x0) / cols
    h = (y1 - y0) / rows
    pad = 12
    res = []
    for r in range(rows):
        for c in range(cols):
            res.append((S, pymupdf.Rect(x0 + c * w - pad, y0 + r * h - pad, x0 + (c + 1) * w + pad, y0 + (r + 1) * h + pad)))
    return res


def main(pages):
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 15)
    except Exception:
        font = ImageFont.load_default()
    for pg in V["pages"]:
        pno = pg["page"]
        if pages and pno not in pages:
            continue
        page = doc[pno - 1]
        for ti, (S, rect) in enumerate(tiles_for(pno, pg["frame"])):
            pix = page.get_pixmap(matrix=pymupdf.Matrix(S, S), clip=rect, alpha=False)
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            dr = ImageDraw.Draw(im)
            n = 0
            for cid, c in enumerate(pg["clusters"]):
                bx = c["bbox"]
                cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
                if not (rect.x0 + 8 <= cx <= rect.x1 - 8 and rect.y0 + 8 <= cy <= rect.y1 - 8):
                    continue
                n += 1
                X0 = (bx[0] - rect.x0) * S; Y0 = (bx[1] - rect.y0) * S
                X1 = (bx[2] - rect.x0) * S; Y1 = (bx[3] - rect.y0) * S
                dr.rectangle([X0 - 1, Y0 - 1, X1 + 1, Y1 + 1], outline=(230, 0, 0), width=1)
                label = str(cid)
                tx, ty = X1 + 2, Y0 - 13
                tw = dr.textlength(label, font=font)
                dr.rectangle([tx - 1, ty, tx + tw + 1, ty + 15], fill=(255, 255, 210))
                dr.text((tx, ty), label, fill=(200, 0, 0), font=font)
            for mx, my, mw in pg["markers"]:
                if rect.x0 <= mx <= rect.x1 and rect.y0 <= my <= rect.y1:
                    X, Y = (mx - rect.x0) * S, (my - rect.y0) * S
                    dr.ellipse([X - 6, Y - 6, X + 6, Y + 6], outline=(0, 90, 255), width=2)
            if n == 0:
                continue
            fn = os.path.join(OUT, f"p{pno}-t{ti:02d}.png")
            im.save(fn)
            print(fn, im.size, "clusters", n)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]])
