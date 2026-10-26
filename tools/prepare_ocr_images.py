#!/usr/bin/env python3
"""Build OCR-optimised grayscale images (upscaled + contrast/sharpened).

The scans average ~817x1146 px. Upscaling x2 with a mild unsharp mask measurably
improves Arabic small-label recognition with the LSTM Tesseract model. These
files are throwaway build inputs in .cache/ and are never shipped.

Usage: .venv/bin/python tools/prepare_ocr_images.py
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "asset_manifest.json"
OUT = ROOT / ".cache" / "ocr" / "images"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    items = json.loads(MANIFEST.read_text(encoding="utf-8"))
    jobs = []
    for it in items:
        src = ROOT / it["pageAsset"]
        im = Image.open(src).convert("L")
        im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
        im = ImageEnhance.Contrast(im).enhance(1.30)
        im = im.filter(ImageFilter.UnsharpMask(radius=1.4, percent=130, threshold=2))
        dst = OUT / f"{it['id']}.png"
        im.save(dst, optimize=True)
        jobs.append(
            {
                "id": it["id"],
                "documentId": it["documentId"],
                "sourcePage": it["sourcePage"],
                "image": str(dst.relative_to(ROOT)),
                "width": im.width,
                "height": im.height,
            }
        )
    (ROOT / "data" / "ocr_jobs.json").write_text(
        json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"prepared {len(jobs)} OCR images in {OUT}")


if __name__ == "__main__":
    main()
