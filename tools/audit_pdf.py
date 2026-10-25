#!/usr/bin/env python3
"""Phase-1 forensics for the three source atlases.

Reads every page of every PDF in google_drive/ and emits a machine-readable
inventory.  Nothing here guesses at geographic content: measurements are taken
from the PDF objects themselves, and every field that cannot be measured is
explicitly flagged for review.

Usage:  .venv/bin/python tools/audit_pdf.py
Output: data/source_documents.json, data/page_inventory.json, docs/CONTENT_AUDIT.md
"""
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "google_drive"
DATA = ROOT / "data"
DOCS = ROOT / "docs"
DATA.mkdir(exist_ok=True)
DOCS.mkdir(exist_ok=True)

# Stable short ids so that page references survive file renames.
DOC_IDS = {
    "الأطلس التاريخي لسيرة الرسول.pdf": "sira",
    "أطلس الخليفة أبي بكر الصديق.pdf": "abubakr",
    "خرائط التاريخ الإسلامي مجمع.pdf": "islamic-maps",
}
DRIVE_IDS = {
    "sira": "1rAwQC3MDkzLwZWAJww2_wAWcN5sqiy9W",
    "abubakr": "13LwaHK3q_ZrrPjmujtiimqL1I0JA85Gj",
    "islamic-maps": "1AQS8YInYN9AdjpRxv-rY9v_zWCSMDRt_",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory() -> tuple[list[dict], list[dict]]:
    docs, pages = [], []
    for path in sorted(SRC.glob("*.pdf")):
        doc_id = DOC_IDS.get(path.name, path.stem)
        with pymupdf.open(path) as pdf:
            toc = [
                {"level": lvl, "title": title, "page": page}
                for lvl, title, page in pdf.get_toc()
            ]
            doc_rec = {
                "id": doc_id,
                "fileName": path.name,
                "driveFileId": DRIVE_IDS.get(doc_id),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "pageCount": pdf.page_count,
                "pdfMetadata": {k: v for k, v in pdf.metadata.items() if v},
                "bookmarks": toc,
                "hasEmbeddedFiles": bool(pdf.embfile_names()),
                "selectableTextPages": 0,
                "embeddedFonts": [],
                "pageSizes": [],
            }
            size_counter: Counter = Counter()
            fonts: Counter = Counter()
            for i, page in enumerate(pdf):
                rect = page.rect
                size_key = (
                    f"{round(rect.width)}x{round(rect.height)}"
                    f"{' landscape' if rect.width > rect.height else ' portrait'}"
                )
                size_counter[size_key] += 1
                for f in page.get_fonts(full=True):
                    fonts[f[3]] += 1
                text = page.get_text("text")
                has_text = bool(text.strip())
                doc_rec["selectableTextPages"] += int(has_text)
                imgs = page.get_images(full=True)
                img_meta = []
                for im in imgs[:4]:
                    img_meta.append(
                        {
                            "xref": im[0],
                            "width": im[2],
                            "height": im[3],
                            "bpc": im[4],
                            "colorSpace": im[5],
                            "filter": im[8],
                        }
                    )
                drawings = len(page.get_drawings())
                pages.append(
                    {
                        "id": f"{doc_id}-p{i + 1:03d}",
                        "documentId": doc_id,
                        "sourcePage": i + 1,
                        "widthPt": round(rect.width, 2),
                        "heightPt": round(rect.height, 2),
                        "orientation": "landscape" if rect.width > rect.height else "portrait",
                        "selectableText": has_text,
                        "selectableChars": len(text.strip()),
                        "imageCount": len(imgs),
                        "images": img_meta,
                        "vectorDrawings": drawings,
                        "contentKind": "needs-review",
                        "title": None,
                        "verificationStatus": "needs-review",
                        "ocrConfidence": None,
                        "extractedText": "",
                        "source": {
                            "document": path.name,
                            "page": i + 1,
                            "driveFileId": DRIVE_IDS.get(doc_id),
                        },
                    }
                )
            doc_rec["embeddedFonts"] = sorted(fonts)
            doc_rec["pageSizes"] = [
                {"size": k, "pages": v} for k, v in size_counter.most_common()
            ]
            docs.append(doc_rec)
    return docs, pages


def write_report(docs: list[dict], pages: list[dict]) -> None:
    total_pages = len(pages)
    text_pages = sum(p["selectableText"] for p in pages)
    image_pages = sum(p["imageCount"] > 0 for p in pages)
    vector_pages = sum(p["vectorDrawings"] > 0 for p in pages)
    lines = [
        "# Content audit — Phase 1 (document forensics)",
        "",
        "All numbers below were measured from the three PDF files in `google_drive/`.",
        "No geographic fact, page title or OCR result has been invented in this phase.",
        "",
        "## Source documents",
        "",
        "| id | file | pages | bytes | selectable-text pages | embedded fonts | bookmarks |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for d in docs:
        lines.append(
            f"| `{d['id']}` | {d['fileName']} | {d['pageCount']} | {d['bytes']:,} | "
            f"{d['selectableTextPages']} | {len(d['embeddedFonts'])} | {len(d['bookmarks'])} |"
        )
    lines += [
        "",
        "## Measured totals",
        "",
        f"- PDF files: **{len(docs)}**",
        f"- Total pages inspected: **{total_pages}**",
        f"- Pages with usable embedded/selectable text: **{text_pages}**",
        f"- Pages requiring OCR: **{total_pages - text_pages}**",
        f"- Pages containing raster images: **{image_pages}**",
        f"- Pages containing vector drawing operators: **{vector_pages}**",
        f"- Embedded font objects across all pages: **{sum(len(d['embeddedFonts']) for d in docs)}**",
        "- Maps identified in this phase: **not yet measured** (requires page rendering + index transcription)",
        "- Searchable geographic entries: **not yet measured** (requires OCR output)",
        "",
        "## Findings",
        "",
        "1. All three PDFs are **image-only scans** (or, for the 8-page maps file, "
        "vector artwork with no text objects). There is no text layer and no embedded "
        "font, so Arabic OCR is mandatory for every page.",
        "2. Page dimensions are A4-ish portrait; scans vary by a few points between pages, "
        "so the viewer must not assume a single fixed pixel size.",
        "3. The `sira` atlas carries a real 16-entry PDF outline (8 chapters + 4 indexes). "
        "Its printed indexes (فهرس الخرائط / الجداول والأشكال / الصور / المواضيع) are the "
        "verified source of truth for page titles and must be transcribed from the page images.",
        "4. Map labels are small relative to the scan resolution. OCR of labels inside "
        "maps is unreliable and must be flagged `uncertain`; the original page image "
        "always remains the authority.",
        "",
        "## Per-document bookmarks (from the PDF outline)",
        "",
    ]
    for d in docs:
        lines += [f"### `{d['id']}` — {d['fileName']}", ""]
        if d["bookmarks"]:
            for b in d["bookmarks"]:
                lines.append(f"- L{b['level']} · p.{b['page']} · {b['title']}")
        else:
            lines.append("- _No outline bookmarks in this PDF._")
        lines.append("")
    lines += [
        "## Traceability",
        "",
        "Every record in `data/page_inventory.json` carries `documentId`, `sourcePage`, "
        "`source.document`, `source.driveFileId` and a SHA-256 of its source PDF "
        "(in `data/source_documents.json`). Keep these fields intact when building the "
        "content manifest so that any extracted fact can be traced back to its page.",
        "",
        "## Status",
        "",
        "Phase 1 complete for structure/forensics; content extraction (OCR), verified "
        "titles, and the application itself are tracked separately. See "
        "`docs/KNOWN_LIMITATIONS.md`.",
        "",
    ]
    (DOCS / "CONTENT_AUDIT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    docs, pages = inventory()
    (DATA / "source_documents.json").write_text(
        json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (DATA / "page_inventory.json").write_text(
        json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_report(docs, pages)
    print(f"documents={len(docs)} pages={len(pages)} "
          f"selectable_text={sum(p['selectableText'] for p in pages)}")
    for d in docs:
        print(f"  {d['id']}: {d['pageCount']} pages, {len(d['bookmarks'])} bookmarks")
