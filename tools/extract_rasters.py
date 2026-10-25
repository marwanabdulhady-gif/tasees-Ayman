#!/usr/bin/env python3
"""
Reproducible raster extraction pipeline for all 3 source PDFs (393 pages total):
  - Extracts native embedded DCTDecode scans at 1:1 pixel fidelity for seerah & abubakr
  - Renders 200 DPI verification pages for maps8 vector atlas
  - Generates lightweight 180px-wide WebP thumbnails for fast TOC & search browsing
  - Outputs data/raw_page_metrics.json
"""
import io
import json
import os
import pymupdf
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def extract_scanned(pdf_path: str, slug: str):
    doc = pymupdf.open(pdf_path)
    pdir = os.path.join(ROOT, "assets", "pages", slug)
    tdir = os.path.join(ROOT, "assets", "thumbs", slug)
    os.makedirs(pdir, exist_ok=True)
    os.makedirs(tdir, exist_ok=True)
    meta = []
    for idx, page in enumerate(doc):
        pnum = idx + 1
        imgs = page.get_images(full=True)
        if len(imgs) == 1:
            base = doc.extract_image(imgs[0][0])
            pil_img = Image.open(io.BytesIO(base["image"])).convert("RGB")
            src_mode = f"embedded-{base.get('ext', 'jpg')}"
        else:
            pix = page.get_pixmap(dpi=150, alpha=False)
            pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            src_mode = "rendered-150dpi"
        w, h = pil_img.size
        out_p = os.path.join(pdir, f"page-{pnum:03d}.webp")
        pil_img.save(out_p, "WEBP", quality=82, method=4)
        tw = 180
        th = max(1, round(h * (tw / w)))
        pil_img.resize((tw, th), Image.Resampling.LANCZOS).save(
            os.path.join(tdir, f"page-{pnum:03d}.webp"), "WEBP", quality=72, method=4
        )
        meta.append({
            "page": pnum,
            "width": w,
            "height": h,
            "pdfWidthPt": round(page.rect.width, 2),
            "pdfHeightPt": round(page.rect.height, 2),
            "sourceMode": src_mode,
            "pageBytes": os.path.getsize(out_p),
        })
    return meta


def render_vector(pdf_path: str, slug: str, dpi: int = 200):
    doc = pymupdf.open(pdf_path)
    pdir = os.path.join(ROOT, "assets", "pages", slug)
    tdir = os.path.join(ROOT, "assets", "thumbs", slug)
    os.makedirs(pdir, exist_ok=True)
    os.makedirs(tdir, exist_ok=True)
    meta = []
    for idx, page in enumerate(doc):
        pnum = idx + 1
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        w, h = pil_img.size
        out_p = os.path.join(pdir, f"page-{pnum:03d}.webp")
        pil_img.save(out_p, "WEBP", quality=85, method=4)
        tw = 180
        th = max(1, round(h * (tw / w)))
        pil_img.resize((tw, th), Image.Resampling.LANCZOS).save(
            os.path.join(tdir, f"page-{pnum:03d}.webp"), "WEBP", quality=75, method=4
        )
        meta.append({
            "page": pnum,
            "width": w,
            "height": h,
            "pdfWidthPt": round(page.rect.width, 2),
            "pdfHeightPt": round(page.rect.height, 2),
            "sourceMode": f"rendered-{dpi}dpi",
            "pageBytes": os.path.getsize(out_p),
        })
    return meta


if __name__ == "__main__":
    maps8_pdf = os.path.join(ROOT, ".cache/source_pdfs/maps8.pdf")
    if not os.path.exists(maps8_pdf):
        maps8_pdf = os.path.join(ROOT, "source/islamic-history-maps.pdf")
    seerah_pdf = os.path.join(ROOT, ".cache/source_pdfs/seerah.pdf")
    abubakr_pdf = os.path.join(ROOT, ".cache/source_pdfs/abubakr.pdf")

    out = {
        "maps8": render_vector(maps8_pdf, "maps8", 200),
        "seerah": extract_scanned(seerah_pdf, "seerah"),
        "abubakr": extract_scanned(abubakr_pdf, "abubakr"),
    }
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(os.path.join(ROOT, "data/raw_page_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("Saved data/raw_page_metrics.json")
