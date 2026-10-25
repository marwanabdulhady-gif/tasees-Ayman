# الأطلس التفاعلي — Interactive Arabic Historical Atlas

Transforming three Arabic PDF atlases (393 scanned pages) into an offline,
Arabic/RTL geographic learning platform.

> **Current status: Phase 1–2 (forensics + extraction pipeline).**
> The interactive application is still being built on this branch. See
> `docs/CONTENT_AUDIT.md` for measured results and `docs/KNOWN_LIMITATIONS.md`
> for an explicit list of what is not yet implemented.

## Source documents

| id | PDF | pages | selectable text |
| --- | --- | ---: | --- |
| `sira` | الأطلس التاريخي لسيرة الرسول.pdf | 264 | none |
| `abubakr` | أطلس الخليفة أبي بكر الصديق.pdf | 121 | none |
| `islamic-maps` | خرائط التاريخ الإسلامي مجمع.pdf | 8 | none (vector art) |

All 393 pages are image-only: **no text layer, no embedded fonts**. Arabic OCR is
therefore required for every page, and OCR output is always treated as
unverified until checked against the original page image.

## Repository layout

```
tools/                 build-time forensics, asset extraction and OCR
  audit_pdf.py         page-by-page inventory + content audit report
  extract_assets.py    source-fidelity WebP pages + thumbnails
  prepare_ocr_images.py  OCR-optimised grayscale inputs
  ocr/                 Tesseract.js LSTM runner (local WASM + local models)
data/                  generated inventories, asset and OCR manifests
docs/                  CONTENT_AUDIT.md, KNOWN_LIMITATIONS.md, PIPELINE.md
assets/                generated page images / thumbnails / OCR JSON (gitignored)
index.html             (planned) standalone offline application entry point
```

## Rebuilding

See `docs/PIPELINE.md`. Build tools need Python + Node; the shipped `index.html`
needs **neither**, and makes no network requests.

## Accuracy policy

- Original PDFs are the sole source of truth.
- No invented place names, coordinates, boundaries or numeric values.
- OCR text is stored verbatim with confidence flags; search normalisation never
  changes displayed source text.
- Every extracted fact keeps `documentId` + `sourcePage` so it can be checked in
  the Original Page Viewer.
- A map is never described as "fully interactive" when it only supports zoom/pan.
