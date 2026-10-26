#!/usr/bin/env python3
"""
Builds Deliverable B: Single-File Portable HTML Edition (release/portable-atlas.html).
Inlines:
  - IBM Plex Sans Arabic woff2 fonts (base64 data URIs)
  - All CSS and modular JS scripts
  - Full 1,069-page manifest + 1,208 gazetteer entries + full search & quiz pools (gzip-compressed)
  - All 8 vector SVGs + 8 original WebP pages for Volume 1 (خرائط التاريخ الإسلامي)
  - Full WebP pages for all curated & comparison maps + covers across all 5 volumes
  - Thumbnails for bundled maps (and lightweight SVG data-URI placeholders for unbundled thumbs)
"""
import base64
import gzip
import io
import json
import os
import re
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def b64_data_uri(rel_path: str, mime: str) -> str:
    full = os.path.join(ROOT, rel_path)
    raw = open(full, "rb").read()
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")


def compact_webp_data_uri(rel_path: str, max_h: int = 960, quality: int = 52) -> str:
    full = os.path.join(ROOT, rel_path)
    im = Image.open(full).convert("RGB")
    w, h = im.size
    if h > max_h:
        nw = max(1, round(w * (max_h / h)))
        im = im.resize((nw, max_h), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="WEBP", quality=quality, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def gz_b64_json(obj) -> str:
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(gzip.compress(raw, compresslevel=9)).decode("ascii")


def load_ocr_words_bundle():
    raw = open(os.path.join(ROOT, "data/ocr-words-bundle.js"), encoding="utf-8").read().strip()
    gz_prefix = 'window.__ATLAS_OCR_WORDS_GZ__ = "'
    if raw.startswith(gz_prefix):
        b64 = raw[len(gz_prefix):].rstrip('";\n ')
        return json.loads(gzip.decompress(base64.b64decode(b64)).decode("utf-8"))
    plain_prefix = "window.__ATLAS_OCR_WORDS__ = "
    return json.loads(raw[len(plain_prefix):].rstrip(";\n "))


def main():
    manifest = json.load(open(os.path.join(ROOT, "data/manifest.json"), encoding="utf-8"))
    atlas_bundle_js = open(os.path.join(ROOT, "data/atlas-bundle.js"), encoding="utf-8").read()
    maps8_vecs_js = open(os.path.join(ROOT, "data/maps8-vectors.js"), encoding="utf-8").read()
    all_ocr_words = load_ocr_words_bundle()

    # Select bundled pages for portable single-file edition
    bundled_page_ids = set()
    for p in manifest["pages"]:
        if p["volumeId"] == "maps8":
            bundled_page_ids.add(p["id"])
        elif p.get("hotspots"):
            bundled_page_ids.add(p["id"])
    for cmp_item in manifest.get("comparisons", []):
        bundled_page_ids.add(cmp_item["leftId"])
        bundled_page_ids.add(cmp_item["rightId"])
    # Bundle all 5 scanned volume covers
    for cov in ("seerah-001", "abubakr-001", "umar-001", "uthman-001", "ali-001"):
        bundled_page_ids.add(cov)

    portable_assets = {}
    portable_ocr_words = {}
    for p in manifest["pages"]:
        if p["id"] in bundled_page_ids:
            if p["volumeId"] == "maps8":
                portable_assets[p["pageAsset"]] = b64_data_uri(p["pageAsset"], "image/webp")
            else:
                portable_assets[p["pageAsset"]] = compact_webp_data_uri(p["pageAsset"], max_h=900, quality=46)
            portable_assets[p["thumbAsset"]] = b64_data_uri(p["thumbAsset"], "image/webp")
            if p["id"] in all_ocr_words:
                portable_ocr_words[p["id"]] = all_ocr_words[p["id"]]
        else:
            svg_thumb = (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="165" viewBox="0 0 120 165">'
                f'<rect width="120" height="165" fill="#efe9db" stroke="#cbbba0"/>'
                f'<text x="60" y="85" text-anchor="middle" font-family="sans-serif" font-size="16" fill="#43515c">ص {p["sourcePage"]}</text>'
                f'</svg>'
            )
            portable_assets[p["thumbAsset"]] = "data:image/svg+xml;base64," + base64.b64encode(svg_thumb.encode("utf-8")).decode("ascii")

    # Inline CSS with embedded woff2 fonts
    css = open(os.path.join(ROOT, "src/styles.css"), encoding="utf-8").read()

    def replace_font(match):
        rel = match.group(1).replace("../", "")
        return f'url("{b64_data_uri(rel, "font/woff2")}")'

    css_inlined = re.sub(r'url\("([^"]+\.woff2)"\)', replace_font, css)

    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    html = re.sub(
        r'<link rel="stylesheet" href="src/styles\.css"\s*/>\s*<style>[\s\S]*?</style>',
        lambda _: f"<style>\n{css_inlined}\n</style>",
        html,
    )

    js_files = [
        "src/js/utils.js",
        "src/js/panzoom.js",
        "src/js/viewer.js",
        "src/js/search.js",
        "src/js/compare.js",
        "src/js/learn.js",
        "src/js/app.js",
    ]
    combined_app_js = "\n".join(open(os.path.join(ROOT, jf), encoding="utf-8").read() for jf in js_files)

    portable_boot = (
        "window.__IS_PORTABLE_EDITION__ = true;\n"
        "window.__PORTABLE_ASSETS__ = " + json.dumps(portable_assets, separators=(",", ":")).replace("</", "<\\/") + ";\n" +
        atlas_bundle_js.replace("</", "<\\/") + "\n" +
        'window.__ATLAS_OCR_WORDS_GZ__ = "' + gz_b64_json(portable_ocr_words) + '";\n' +
        maps8_vecs_js + "\n" +
        combined_app_js
    )

    html = re.sub(
        r'<!-- Local Offline Bundles[\s\S]*?</body>',
        lambda _: f"<script>\n{portable_boot}\n</script>\n</body>",
        html,
    )

    os.makedirs(os.path.join(ROOT, "release"), exist_ok=True)
    out_path = os.path.join(ROOT, "release/portable-atlas.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    sz_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"Built {out_path} ({sz_mb:.2f} MB) with {len(bundled_page_ids)} bundled pages + all {len(manifest['pages'])} pages indexed!")


if __name__ == "__main__":
    main()
