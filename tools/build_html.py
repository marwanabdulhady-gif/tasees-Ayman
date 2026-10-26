#!/usr/bin/env python3
"""
Bundle the application into ONE self-contained HTML file:
  release/islamic-history-atlas.html

Inlines: CSS, fonts (woff2, base64), JavaScript modules, the content manifest,
thumbnails + independent raster page renders (webp, base64) and the eight
layer-tagged vector pages (gzip + base64, decoded in the browser with the
native DecompressionStream API).  No network access is needed at runtime.
"""
import base64
import gzip
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
OUT_DIR = os.path.join(ROOT, "release")
OUT = os.path.join(OUT_DIR, "islamic-history-atlas.html")
JS_ORDER = ["util.js", "assets.js", "panzoom.js", "mapview.js", "learn.js", "app.js"]


def b64(path):
    return base64.b64encode(open(path, "rb").read()).decode("ascii")


def data_uri(path, mime):
    return f"data:{mime};base64,{b64(path)}"


def fonts_css():
    F = os.path.join(ROOT, "assets", "fonts")
    rules = []
    ar_range = "U+0600-06FF, U+0750-077F, U+0870-088E, U+0890-0891, U+0898-08E1, U+08E3-08FF, U+200C-200E, U+2010-2011, U+204F, U+2E41, U+FB50-FDFF, U+FE70-FE74, U+FE76-FEFC"
    for weight in (400, 500, 700):
        p = os.path.join(F, f"ibm-plex-sans-arabic-arabic-{weight}-normal.woff2")
        if os.path.exists(p):
            rules.append(f"@font-face{{font-family:'IBM Plex Sans Arabic';font-style:normal;font-weight:{weight};font-display:swap;"
                         f"src:url({data_uri(p, 'font/woff2')}) format('woff2');unicode-range:{ar_range};}}")
    for weight in (400, 700):
        p = os.path.join(F, f"ibm-plex-sans-arabic-latin-{weight}-normal.woff2")
        if os.path.exists(p):
            rules.append(f"@font-face{{font-family:'IBM Plex Sans Arabic';font-style:normal;font-weight:{weight};font-display:swap;"
                         f"src:url({data_uri(p, 'font/woff2')}) format('woff2');unicode-range:U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+2074, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;}}")
    return "\n".join(rules)


def main():
    atlas = json.load(open(os.path.join(ROOT, "data", "atlas.json"), encoding="utf-8"))
    thumbs = {}
    for fn in sorted(os.listdir(os.path.join(ROOT, "assets", "thumbs"))):
        thumbs[fn.rsplit(".", 1)[0]] = data_uri(os.path.join(ROOT, "assets", "thumbs", fn), "image/webp")
    pages = {}
    for i in range(1, 9):
        pages[str(i)] = data_uri(os.path.join(ROOT, "assets", "pages", f"page-{i:03d}.webp"), "image/webp")
    atlas["assets"] = {"thumbs": thumbs, "pages": pages}
    atlas["build"] = {"tool": "tools/build_html.py"}
    data_json = json.dumps(atlas, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    svg_blocks = []
    svg_total = 0
    for i in range(1, 9):
        raw = open(os.path.join(ROOT, "assets", "svg", f"page-{i:03d}.svg"), "rb").read()
        gz = gzip.compress(raw, 9)
        svg_total += len(gz)
        svg_blocks.append(f'<script type="application/octet-stream" class="svg-data" data-page="{i}" data-encoding="gzip+base64">'
                          f'{base64.b64encode(gz).decode("ascii")}</script>')

    css = open(os.path.join(SRC, "styles.css"), encoding="utf-8").read().replace("/*__FONTS__*/", fonts_css())
    js = "\n;\n".join(open(os.path.join(SRC, "js", f), encoding="utf-8").read() for f in JS_ORDER)
    if "</script" in js.lower():
        raise SystemExit("JS contains a closing script tag")
    html = open(os.path.join(SRC, "index.html"), encoding="utf-8").read()
    html = html.replace("/*__CSS__*/", css)
    html = html.replace("<!--__DATA__-->", f'<script type="application/json" id="atlas-data">{data_json}</script>\n' + "\n".join(svg_blocks))
    html = html.replace("/*__JS__*/", js)
    os.makedirs(OUT_DIR, exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(html)
    size = os.path.getsize(OUT)
    print(f"wrote {OUT}  {size/1048576:.2f} MB  (vector pages gzip {svg_total/1048576:.2f} MB, data json {len(data_json)/1048576:.2f} MB)")


if __name__ == "__main__":
    main()
