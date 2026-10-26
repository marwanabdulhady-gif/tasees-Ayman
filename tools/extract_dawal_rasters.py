#!/usr/bin/env python3
"""
Raster extraction for volume 7: أطلس دول العالم الإسلامي (Dr. Shuqayqi Abu Khalil, 2nd ed. 2003).
- Extracts the native embedded 100-DPI JPEG scans at 1:1 pixel fidelity (650x921).
- Outputs assets/pages/dawal/page-NNN.webp (q82) and assets/thumbs/dawal/page-NNN.webp (150px, q56).
- Appends metrics to data/raw_page_metrics.json under the 'dawal' slug.
"""
import io
import json
import os

import pymupdf
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLUG = "dawal"
PDF = os.path.join(ROOT, "source", "islamic-states-atlas-abu-khalil.pdf")
PAGE_QUALITY = 82


def main() -> None:
    doc = pymupdf.open(PDF)
    pdir = os.path.join(ROOT, "assets", "pages", SLUG)
    tdir = os.path.join(ROOT, "assets", "thumbs", SLUG)
    os.makedirs(pdir, exist_ok=True)
    os.makedirs(tdir, exist_ok=True)

    meta = []
    for idx, page in enumerate(doc):
        pnum = idx + 1
        imgs = page.get_images(full=True)
        assert len(imgs) == 1, f"page {pnum}: expected exactly 1 embedded image, found {len(imgs)}"
        base = doc.extract_image(imgs[0][0])
        pil_img = Image.open(io.BytesIO(base["image"])).convert("RGB")
        w, h = pil_img.size
        out_p = os.path.join(pdir, f"page-{pnum:03d}.webp")
        pil_img.save(out_p, "WEBP", quality=PAGE_QUALITY, method=6)
        tw = 150
        th = max(1, round(h * (tw / w)))
        pil_img.resize((tw, th), Image.Resampling.LANCZOS).save(
            os.path.join(tdir, f"page-{pnum:03d}.webp"), "WEBP", quality=56, method=6
        )
        meta.append(
            {
                "page": pnum,
                "width": w,
                "height": h,
                "pdfWidthPt": round(page.rect.width, 2),
                "pdfHeightPt": round(page.rect.height, 2),
                "sourceMode": f"embedded-{base.get('ext', 'jpg')}",
                "pageBytes": os.path.getsize(out_p),
            }
        )
        if pnum % 64 == 0:
            print(f"  {pnum}/{doc.page_count} extracted")

    mpath = os.path.join(ROOT, "data", "raw_page_metrics.json")
    metrics = json.load(open(mpath, encoding="utf-8"))
    if SLUG in metrics:
        del metrics[SLUG]
    metrics[SLUG] = meta
    json.dump(metrics, open(mpath, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"done: {len(meta)} pages for slug '{SLUG}'")


if __name__ == "__main__":
    main()
