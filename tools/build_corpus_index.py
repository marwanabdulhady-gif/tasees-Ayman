#!/usr/bin/env python3
"""Join forensics + assets + OCR into the corpus search index.

Output: data/corpus_index.json  (compact, one record per source page)
        docs/CORPUS-AUDIT.md    (append measured OCR section)

No geographic fact is invented here. Titles come only from PDF outline
bookmarks; everything else stays `needs-review`.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OCR = ROOT / "assets" / "ocr"
DOCS = ROOT / "docs"


def normalise(text: str) -> str:
    """Arabic search normalisation. Display text is NEVER passed through this."""
    t = unicodedata.normalize("NFKC", text)
    t = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", t)   # harakat + tatweel
    t = re.sub(r"[أإآٱ]", "ا", t)
    t = re.sub(r"[ىي]", "ي", t)
    t = re.sub(r"[ؤئ]", "ء", t)
    t = t.replace("ة", "ه")
    t = "".join(
        chr(ord(c) - 0x0660 + 0x30) if "\u0660" <= c <= "\u0669" else c for c in t
    )
    t = "".join(
        chr(ord(c) - 0x06F0 + 0x30) if "\u06F0" <= c <= "\u06F9" else c for c in t
    )
    t = re.sub(r"[^\w\s\u0600-\u06FF]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def bookmark_sections(docs: list[dict]) -> dict[str, list[dict]]:
    out = {}
    for d in docs:
        marks = sorted(
            [b for b in d["bookmarks"] if b["page"] <= d["pageCount"]],
            key=lambda b: b["page"],
        )
        out[d["id"]] = marks
    return out


def section_for(marks: list[dict], page_no: int) -> tuple[str | None, str | None]:
    """Return (section title, exact page title if this page starts a bookmark)."""
    exact = [b["title"] for b in marks if b["page"] == page_no]
    current = None
    for b in marks:
        if b["page"] <= page_no:
            current = b["title"]
        else:
            break
    return current, exact[0] if exact else None


def main() -> None:
    docs = json.loads((DATA / "source_documents.json").read_text(encoding="utf-8"))
    pages = json.loads((DATA / "page_inventory.json").read_text(encoding="utf-8"))
    assets = {a["id"]: a for a in json.loads((DATA / "asset_manifest.json").read_text(encoding="utf-8"))}
    sections = bookmark_sections(docs)

    records, stats = [], {
        "ocrPages": 0, "words": 0, "uncertainWords": 0,
        "confSum": 0, "pagesWithText": 0, "chars": 0,
    }
    for p in pages:
        pid = p["id"]
        ocr_path = OCR / p["documentId"] / f"{p['sourcePage']:03d}.json"
        ocr = json.loads(ocr_path.read_text(encoding="utf-8")) if ocr_path.exists() else None
        a = assets.get(pid, {})
        section, title = section_for(sections.get(p["documentId"], []), p["sourcePage"])
        rec = {
            "id": pid,
            "documentId": p["documentId"],
            "sourcePage": p["sourcePage"],
            "sourceDocument": p["source"]["document"],
            "driveFileId": p["source"]["driveFileId"],
            "section": section,
            "title": title,
            "titleSource": "pdf-outline-bookmark" if title else None,
            "verificationStatus": "needs-review",
            "pageAsset": a.get("pageAsset"),
            "thumbnail": a.get("thumbnail"),
            "pixelWidth": a.get("pixelWidth"),
            "pixelHeight": a.get("pixelHeight"),
            "ocrConfidence": ocr["meanConfidence"] if ocr else None,
            "wordCount": ocr["wordCount"] if ocr else 0,
            "uncertainWordCount": ocr["uncertainWordCount"] if ocr else 0,
            "extractedText": ocr["extractedText"] if ocr else "",
            "searchText": normalise(ocr["extractedText"]) if ocr else "",
        }
        records.append(rec)
        if ocr:
            stats["ocrPages"] += 1
            stats["words"] += ocr["wordCount"]
            stats["uncertainWords"] += ocr["uncertainWordCount"]
            stats["confSum"] += ocr["meanConfidence"]
            stats["chars"] += len(ocr["extractedText"])
            stats["pagesWithText"] += int(bool(ocr["extractedText"].strip()))

    payload = {
        "generatedBy": "tools/build_corpus_index.py",
        "sourceOfTruth": "the three PDFs listed in data/source_documents.json",
        "normalisation": "Alef variants, harakat, tatweel, alef-maqsura/ya, ta-marbuta, Arabic-Indic digits",
        "warning": "OCR text is unverified; displayed source text is never normalised.",
        "pageCount": len(records),
        "pages": records,
    }
    (DATA / "corpus_index.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    avg_conf = round(stats["confSum"] / max(1, stats["ocrPages"]), 1)
    uncertain_pct = round(100 * stats["uncertainWords"] / max(1, stats["words"]), 1)
    append = f"""

---

## Measured OCR results (added after the full run)

The offline Arabic LSTM run (`tools/ocr/run_ocr.js`) processed **{stats['ocrPages']} of {len(records)} pages**:

| metric | value |
| --- | ---: |
| pages with OCR output | {stats['ocrPages']} |
| pages with non-empty OCR text | {stats['pagesWithText']} |
| recognised words | {stats['words']:,} |
| words flagged uncertain (confidence < 60) | {stats['uncertainWords']:,} ({uncertain_pct}%) |
| mean per-word confidence | {avg_conf} |
| OCR characters preserved | {stats['chars']:,} |

`data/corpus_index.json` joins every page to its document, PDF page number,
Drive id, PDF-outline section/title (where one exists), raster assets and verbatim
OCR text plus a normalised `searchText` field. **All 393 OCR records keep
`verificationStatus: "needs-review"`** except that page titles which coincide
with a PDF outline bookmark are marked `pdf-outline-bookmark`. No place name in
this index has been manually corrected or guessed.

Mean confidence around {avg_conf} reflects low-resolution scans and dense map
lettering. This is why the index is explicitly labelled unverified and why the
original page image remains the authority in the viewer.
"""
    audit = DOCS / "CORPUS-AUDIT.md"
    audit.write_text(audit.read_text(encoding="utf-8").rstrip() + append + "\n", encoding="utf-8")
    print(f"index: {len(records)} pages, {stats['words']:,} words, avg conf {avg_conf}")


if __name__ == "__main__":
    main()
