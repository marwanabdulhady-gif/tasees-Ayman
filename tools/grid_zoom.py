#!/usr/bin/env python3
"""Render a region of a PDF page at high zoom with a labelled PDF-point grid.
Usage: grid_zoom.py PAGE x0 y0 x1 y1 SCALE OUTNAME [STEP]
Scratch tool used for visual transcription (output in work/sheets)."""
import os, sys
import pymupdf
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pno, x0, y0, x1, y1, S = int(sys.argv[1]), *map(float, sys.argv[2:7])
name = sys.argv[7]; step = int(sys.argv[8]) if len(sys.argv) > 8 else 10
d = pymupdf.open(os.path.join(ROOT, "source", "islamic-history-maps.pdf"))
r = pymupdf.Rect(x0, y0, x1, y1)
pix = d[pno - 1].get_pixmap(matrix=pymupdf.Matrix(S, S), clip=r, alpha=False)
im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
dr = ImageDraw.Draw(im)
for x in range(int(x0) // step * step + step, int(x1), step):
    X = (x - x0) * S; dr.line([X, 0, X, im.height], fill=(0, 170, 255)); dr.text((X + 2, 2), str(x), fill=(0, 70, 230))
for y in range(int(y0) // step * step + step, int(y1), step):
    Y = (y - y0) * S; dr.line([0, Y, im.width, Y], fill=(0, 170, 255)); dr.text((2, Y + 2), str(y), fill=(0, 70, 230))
os.makedirs(os.path.join(ROOT, "work", "sheets"), exist_ok=True)
out = os.path.join(ROOT, "work", "sheets", name + ".png"); im.save(out); print(out, im.size)
