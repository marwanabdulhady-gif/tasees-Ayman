# Dawal hotspot placement review

All 89 map pages now have one image-space anchor reviewed against the scanned
page. These replace the uniform 50%,50% placeholder rectangles. This is **not**
full feature extraction: most maps still have only one clickable feature, and
no geographic georeferencing or boundary verification is claimed.

## Evidence and reproduction

- `data/dawal_hotspot_review.json`: manually read feature names, pixel centres,
  source dimensions, SHA-256 image hashes and Arabic visual evidence notes.
- `node tools/refine_dawal_hotspots.cjs`: applies the reviewed coordinates to
  `data/manifest.json` and regenerates the browser's `data/atlas-bundle.js`.
- Viewer rectangles use top-left percentage coordinates. The script subtracts
  half the 5%-wide/high target from each reviewed pixel centre.
- Coordinates were read visually from 650×921 scans. They are approximate pixel
  selections around visible symbols, not survey-grade or geographic positions.
- `node tools/qa/run_qa.cjs`: checks complete 89-page evidence coverage, hashes,
  applied coordinates and bundle equality, then opens and clicks all 89 anchors
  through the TOC in an offline Chromium session.

## Non-city targets and source caveats

- Pages 118 and 134: the printed Africa label in the globe, not a city or a
  density measurement.
- Page 146: the printed Xinjiang region label, not a capital or border point.
- Page 143: Singapore's symbol in the detailed island inset, not the satellite
  locator rectangle.
- Page 158: Tananarive on the large Madagascar map. The index title mentions
  Mauritius, but Mauritius is a separate small island lower in the scan. The
  popup explicitly documents the distinction.
- Page 160: Mandalay in the Burma portion of the broader regional map.
- Historical names and boundaries are attributed to the printed atlas. City
  markers do not assert present-day capital status or political sovereignty.

Image hashes and coordinate consistency prevent silent drift, but do not
independently prove the correctness of a human reading. The evidence file
supports subsequent corrections and peer review.
