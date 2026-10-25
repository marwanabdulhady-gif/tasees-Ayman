# Known limitations

This file is updated as the extraction pipeline runs. It deliberately states what
has **not** been verified yet; nothing here should be read as a claim of
completeness.

## Source material

- All three PDFs are image-only. **0 of 393 pages** have a selectable text layer
  and **0** embed fonts. Every Arabic string in the application therefore comes
  from OCR or from manual transcription of the printed pages, and is marked with
  its provenance and verification status.
- The scans are low-resolution by modern standards (roughly 817×1146 px for the
  two large atlases). Small labels inside maps frequently OCR incorrectly. Those
  results are stored as `ocr-unverified`; the high-resolution original page image
  remains authoritative in the Original Page Viewer.
- The 8-page `islamic-maps` PDF is vector artwork with no text objects at all;
  its labels are drawn as paths, so OCR is the only extraction route there too.

## Geographic interaction

- No vector boundaries, GeoJSON, or georeferencing information exists in the PDFs.
  Consequently the application must **not** claim clickable country/province
  boundaries. Planned interactions are limited to:
  - verified image-coordinate hotspots for discrete, identifiable labels,
  - OCR word boxes that let search results zoom to the exact printed word,
  - an enhanced image viewer (zoom/pan/compare) for everything else.
- Where a hotspot is derived from OCR rather than manual verification, it is
  labelled as such in the UI.
- Thematic layers cannot be independently toggled: the source combines all
  symbols and colours into a single flattened page image. Any layer control in
  the app toggles overlays *we* generated (OCR text layer, hotspot layer), not
  reconstructed cartographic layers. This is stated in the UI.

## Offline / portability

- A single self-contained HTML file is impractical: 393 source-fidelity page
  images plus OCR data are far larger than a portable single file. The shipped
  deliverable is a multi-file offline package (`index.html` + `assets/` + `data/`).
  A reduced portable edition may be produced with a subset of pages; its
  limitations will be listed here if it is built.
- Opening via `file://` works for the viewer but some browsers restrict
  `fetch()` of local JSON. A tiny local static server is the recommended usage
  mode, and the app detects and explains this case.

## Content verification

- Page titles are verified only where they come from (a) PDF outline bookmarks,
  (b) the printed indexes, or (c) direct visual inspection of the page. All other
  pages keep `title: null` / `verificationStatus: "needs-review"` until reviewed.
- Numeric values and place names are never auto-corrected. Arabic search
  normalisation affects the search index only, never displayed source text.

## Not yet measured

- Number of maps, legends, tables, interactive features and searchable
  geographic entries. These require the OCR run + index transcription to finish.
  See `docs/CORPUS-AUDIT.md` for the numbers that *have* been measured.
