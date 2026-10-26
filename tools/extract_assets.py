#!/usr/bin/env python3
"""Extract source-fidelity page images + thumbnails from the three PDFs.

For raster-scan pages the embedded JPEG is copied byte-for-byte (no generational
loss).  For the 8 vector-only map pages we render at 2.5x so that small Arabic
labels stay legible.  Thumbnails are generated from the same source image.

Usage:  .venv/bin/python tools/extract_assets.py
Output: assets/pages/<docId>/pNNN.webp, assets/thumbnails/<docId>/pNNN.webp,
        data/asset_manifest.json
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "google_drive"
PAGES = ROOT / "assets" / "pages"
THUMBS = ROOT / "assets" / "thumbnails"
DATA = ROOT / "data"

DOC_IDS = {
    "الأطلس التاريخي لسيرة الرسول.pdf": "sira",
    "أطلس الخليفة أبي بكر الصديق.pdf": "abubakr",
    "خرائط التاريخ الإسلامي مجمع.pdf": "islamic-maps",
}

# Deliberately conservative: the scans are ~817x1146 px and labels are small.
# WEBP quality 88 keeps Arabic glyph edges readable while staying offline-friendly.
PAGE_QUALITY = 88
THUMB_QUALITY = 72
THUMB_MAX = (260, 366)


def page_image(pdf: pymupdf.Document, page: pymupdf.Page) -> Image.Image:
    imgs = page.get_images(full=True)
    if imgs:
        xref = imgs[0][0]
        raw = pdf.extract_image(xref)
        return Image.open(io.BytesIO(raw["image"])).convert("RGB")
    # Vector-only page: render at high resolution, never downscale the source.
    pix = page.get_pixmap(matrix=pymupdf.Matrix(2.5, 2.5), alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def main() -> None:
    out = []
    for path in sorted(SRC.glob("*.pdf")):
        doc_id = DOC_IDS.get(path.name, path.stem)
        (PAGES / doc_id).mkdir(parents=True, exist_ok=True)
        (THUMBS / doc_id).mkdir(parents=True, exist_ok=True)
        with pymupdf.open(path) as pdf:
            for i, page in enumerate(pdf, start=1):
                im = page_image(pdf, page)
                stem = f"p{i:03d}.webp"
                page_rel = f"assets/pages/{doc_id}/{stem}"
                thumb_rel = f"assets/thumbnails/{doc_id}/{stem}"
                im.save(ROOT / page_rel, "WEBP", quality=PAGE_QUALITY, method=5)
                thumb = ImageOps.contain(im, THUMB_MAX, Image.LANCZOS)
                thumb.save(ROOT / thumb_rel, "WEBP", quality=THUMB_QUALITY, method=5)
                out.append(
                    {
                        "id": f"{doc_id}-p{i:03d}",
                        "documentId": doc_id,
                        "sourcePage": i,
                        "pageAsset": page_rel,
                        "thumbnail": thumb_rel,
                        "pixelWidth": im.width,
                        "pixelHeight": im.height,
                        "sourceDocument": path.name,
                    }
                )
                if i % 50 == 0:
                    print(f"  {doc_id}: {i}/{pdf.page_count}")
    (DATA / "asset_manifest.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"extracted {len(out)} pages")


if __name__ == "__main__":
    main()
