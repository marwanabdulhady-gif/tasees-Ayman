# Content audit — Phase 1 (document forensics)

All numbers below were measured from the three PDF files in `google_drive/`.
No geographic fact, page title or OCR result has been invented in this phase.

## Source documents

| id | file | pages | bytes | selectable-text pages | embedded fonts | bookmarks |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `abubakr` | أطلس الخليفة أبي بكر الصديق.pdf | 121 | 17,196,097 | 0 | 0 | 17 |
| `sira` | الأطلس التاريخي لسيرة الرسول.pdf | 264 | 36,303,062 | 0 | 0 | 16 |
| `islamic-maps` | خرائط التاريخ الإسلامي مجمع.pdf | 8 | 2,228,192 | 0 | 0 | 0 |

## Measured totals

- PDF files: **3**
- Total pages inspected: **393**
- Pages with usable embedded/selectable text: **0**
- Pages requiring OCR: **393**
- Pages containing raster images: **387**
- Pages containing vector drawing operators: **8**
- Embedded font objects across all pages: **0**
- Maps identified in this phase: **not yet measured** (requires page rendering + index transcription)
- Searchable geographic entries: **not yet measured** (requires OCR output)

## Findings

1. All three PDFs are **image-only scans** (or, for the 8-page maps file, vector artwork with no text objects). There is no text layer and no embedded font, so Arabic OCR is mandatory for every page.
2. Page dimensions are A4-ish portrait; scans vary by a few points between pages, so the viewer must not assume a single fixed pixel size.
3. The `sira` atlas carries a real 16-entry PDF outline (8 chapters + 4 indexes). Its printed indexes (فهرس الخرائط / الجداول والأشكال / الصور / المواضيع) are the verified source of truth for page titles and must be transcribed from the page images.
4. Map labels are small relative to the scan resolution. OCR of labels inside maps is unreliable and must be flagged `uncertain`; the original page image always remains the authority.

## Per-document bookmarks (from the PDF outline)

### `abubakr` — أطلس الخليفة أبي بكر الصديق.pdf

- L1 · p.1 · أطلس أبي بكر الصديق
- L2 · p.4 · مقدمة
- L2 · p.9 · الباب الأول : أبو بكر الصديق في العهد المكي
- L3 · p.22 · أهم المراجع المستخدمة في الباب الأول
- L2 · p.23 · الباب الثاني : أبو بكر الصديق في العهد المدني
- L3 · p.34 · أهم المراجع المستخدمة في الباب الثاني
- L2 · p.35 · الباب الثالث : خلافة أبي بكر الصديق
- L3 · p.37 · الفصل الأول: توليه الخلافة
- L3 · p.41 · الفصل الثاني: القضاء على المرتدين
- L3 · p.65 · الفصل الثالث: الفتوحات الإسلامية في عهده -فارس - الروم-
- L3 · p.102 · أهم المراجع المستخدمة في الباب الثالث
- L2 · p.103 · الباب الرابع : ملامح عامة من عهد الصديق
- L3 · p.113 · أهم المراجع المستخدمة في الباب الرابع
- L2 · p.115 · ملاحق الكتاب
- L3 · p.115 · فهرس العناوين الرئيسية
- L3 · p.116 · فهارس الخرائط
- L3 · p.119 · فهارس الصور

### `sira` — الأطلس التاريخي لسيرة الرسول.pdf

- L1 · p.1 · الأطلس التاريخي لسيرة الرسول صلى الله عليه وسلم
- L2 · p.11 · تقديم
- L2 · p.13 · مقدمة
- L2 · p.15 · الباب الأول: مقتطفات عن شبه الجزيرة العربية
- L2 · p.31 · الباب الثاني: سكان الجزيرة العربية
- L2 · p.51 · الباب الثالث: أهم المراكز الحضارية في الحجاز في عهد الرسول
- L2 · p.71 · الباب الرابع: الجزيرة العربية قبل بعثة الرسول (العهد الجاهلي)
- L2 · p.83 · الباب الخامس: من المولد الشريف إلى البعثة المباركة (العهد المكي)
- L2 · p.121 · الباب السادس: من تأسيس الدولة الإسلامية إلى وفاة الرسول (العهد المدني)
- L2 · p.211 · الباب السابع: جوانب من سيرة الرسول الخاصة
- L2 · p.223 · الباب الثامن: الإسلام عقيدة وشريعة
- L2 · p.255 · الفهارس
- L3 · p.255 · فهرس المواضيع
- L3 · p.256 · فهرس الخرائط
- L3 · p.260 · فهرس الجداول والأشكال
- L3 · p.262 · فهرس الصور

### `islamic-maps` — خرائط التاريخ الإسلامي مجمع.pdf

- _No outline bookmarks in this PDF._

## Traceability

Every record in `data/page_inventory.json` carries `documentId`, `sourcePage`, `source.document`, `source.driveFileId` and a SHA-256 of its source PDF (in `data/source_documents.json`). Keep these fields intact when building the content manifest so that any extracted fact can be traced back to its page.

## Status

Phase 1 complete for structure/forensics; content extraction (OCR), verified titles, and the application itself are tracked separately. See `docs/KNOWN_LIMITATIONS.md`.
