/* ==========================================================================
   search.js — Fast Arabic-Aware Search Engine Across All 393 Pages & Gazetteer
   ========================================================================== */
(function () {
  "use strict";

  const { normAr, toWesternDigits, toArabicDigits, highlightAr, makeSnippet } = window.AtlasUtils;

  class AtlasSearchEngine {
    constructor(manifest) {
      this.manifest = manifest;
      this.pageById = new Map(manifest.pages.map((p) => [p.id, p]));
      this.volById = new Map(manifest.volumes.map((v) => [v.id, v]));
      this.docs = [];
      this._buildIndex();
    }

    _buildIndex() {
      const m = this.manifest;
      const maps8Vol = this.volById.get("maps8");

      // 1. Index verified vector features on maps8
      if (maps8Vol && Array.isArray(maps8Vol.features)) {
        for (const ft of maps8Vol.features) {
          if (!ft.text || ft.kind === "unreadable") continue;
          const pid = `maps8-${String(ft.page).padStart(3, "0")}`;
          const page = this.pageById.get(pid);
          this.docs.push({
            type: "feature",
            sourceTier: "verified",
            volumeId: "maps8",
            pageId: pid,
            sourcePage: ft.page,
            figureId: ft.figure,
            featureId: ft.id,
            title: ft.text,
            titleNorm: ft.norm || normAr(ft.text),
            body: `${ft.kindLabel || ""} — ${page ? page.sectionTitle : ""}`,
            bodyNorm: normAr(`${ft.kindLabel || ""} ${page ? page.sectionTitle : ""}`),
            category: page ? page.category : "spread-map",
            thumb: page ? page.thumbAsset : "",
            badge: `تسمية متجهية (${ft.kindLabel || "معلم"})`,
            confidence: ft.conf,
          });
        }
      }

      // 2. Index curated verified hotspots on seerah & abubakr
      for (const page of m.pages) {
        for (const hs of page.hotspots || []) {
          this.docs.push({
            type: "hotspot",
            sourceTier: "verified",
            volumeId: page.volumeId,
            pageId: page.id,
            sourcePage: page.sourcePage,
            hotspotId: hs.id,
            title: hs.name,
            titleNorm: normAr(hs.name),
            body: hs.fact || page.title,
            bodyNorm: normAr(`${hs.fact || ""} ${page.title}`),
            category: page.category,
            thumb: page.thumbAsset,
            badge: "معلم خريطة محقق",
            confidence: "high",
          });
        }
      }

      // 3. Index all 393 pages (verified titles, index entries, and OCR text)
      for (const page of m.pages) {
        const idxTitles = (page.indexEntries || []).map((e) => e.title).join(" · ");
        this.docs.push({
          type: "page",
          sourceTier: page.titleSource === "section-page-ref" ? "ocr" : "verified",
          volumeId: page.volumeId,
          pageId: page.id,
          sourcePage: page.sourcePage,
          figureId: page.figureId || null,
          title: page.title,
          titleNorm: page.titleNorm || normAr(page.title),
          idxNorm: normAr(idxTitles),
          body: (idxTitles ? idxTitles + " — " : "") + (page.extractedText || page.description || ""),
          bodyNorm: page.extractedTextNorm || normAr(page.extractedText || ""),
          category: page.category,
          thumb: page.thumbAsset,
          badge: page.titleSource === "section-page-ref"
            ? `نص OCR (${toArabicDigits(page.ocrConfidence || 0)}%)`
            : "صفحة مفهرسة محققة",
          ocrConfidence: page.ocrConfidence,
        });
      }
    }

    /**
     * Parses direct page jump queries like "ص 159", "صفحة ١١٨", "سيرة 90", "صديق 54", "عمر 81", "عثمان 157", "علي 181"
     */
    _parsePageJump(rawQuery, volumeFilter) {
      const w = toWesternDigits(rawQuery).trim();
      const m = w.match(/^(?:ص|صفحة|صفحه|p|page|سيرة|سيره|صديق|ابو بكر|أبو بكر|عمر|الفاروق|عثمان|ذو النورين|ذي النورين|علي|على|أبو الحسن|ابو الحسن|خرائط|دول|أبو خليل|ابو خليل)?\s*(\d{1,3})$/i);
      if (!m) return [];
      const pnum = Number(m[1]);
      if (!pnum) return [];

      let targetVols = ["maps8", "seerah", "abubakr", "umar", "uthman", "ali", "dawal"];
      if (/سير/.test(w)) targetVols = ["seerah"];
      else if (/صديق|بكر/.test(w)) targetVols = ["abubakr"];
      else if (/عمر|فاروق/.test(w)) targetVols = ["umar"];
      else if (/عثمان|نورين/.test(w)) targetVols = ["uthman"];
      else if (/علي|على|حسن/.test(w)) targetVols = ["ali"];
      else if (/خرائط/.test(w)) targetVols = ["maps8"];
      else if (/دول|ابو خليل|أبو خليل/.test(w)) targetVols = ["dawal"];
      else if (volumeFilter && volumeFilter !== "all") targetVols = [volumeFilter];

      const out = [];
      for (const vid of targetVols) {
        const pid = `${vid}-${String(pnum).padStart(3, "0")}`;
        const p = this.pageById.get(pid);
        if (p) {
          const vol = this.volById.get(vid);
          out.push({
            score: 1000,
            doc: {
              type: "page-jump",
              sourceTier: "verified",
              volumeId: vid,
              pageId: pid,
              sourcePage: pnum,
              figureId: p.figureId || null,
              title: p.title,
              body: p.description,
              category: p.category,
              thumb: p.thumbAsset,
              badge: `انتقال مباشر — ${vol ? vol.shortTitle : vid} ص ${toArabicDigits(pnum)}`,
            },
          });
        }
      }
      return out;
    }

    search(rawQuery, opts = {}) {
      const volumeFilter = opts.volume || "all";
      const tierFilter = opts.tier || "all"; // all | verified | maps-only
      const limit = opts.limit || 45;

      const jumps = this._parsePageJump(rawQuery, volumeFilter);
      const qNorm = normAr(rawQuery);
      if (!qNorm && !jumps.length) return [];

      const tokens = qNorm.split(" ").filter(Boolean);
      const scored = [...jumps];

      for (const d of this.docs) {
        if (volumeFilter !== "all" && d.volumeId !== volumeFilter) continue;
        if (tierFilter === "verified" && d.sourceTier !== "verified") continue;
        if (tierFilter === "maps-only" && d.category !== "map" && d.category !== "spread-map" && d.type !== "feature" && d.type !== "hotspot") continue;

        let score = 0;
        if (d.titleNorm === qNorm) {
          score += 500;
        } else if (d.titleNorm.startsWith(qNorm)) {
          score += 320;
        } else if (d.titleNorm.includes(qNorm)) {
          score += 220;
        } else if (d.idxNorm && d.idxNorm.includes(qNorm)) {
          score += 190;
        }

        // Token-by-token check across title + body
        let allMatched = true;
        let titleHits = 0;
        let bodyHits = 0;
        for (const tk of tokens) {
          const inTitle = d.titleNorm.includes(tk) || (d.idxNorm && d.idxNorm.includes(tk));
          const inBody = d.bodyNorm.includes(tk);
          if (!inTitle && !inBody) {
            allMatched = false;
            break;
          }
          if (inTitle) titleHits++;
          if (inBody) bodyHits++;
        }

        if (!allMatched) continue;
        score += titleHits * 75 + bodyHits * 25;
        if (d.sourceTier === "verified") score += 45;
        if (d.type === "feature" || d.type === "hotspot") score += 20;

        if (score > 0) {
          scored.push({ score, doc: d });
        }
      }

      scored.sort((a, b) => b.score - a.score || a.doc.sourcePage - b.doc.sourcePage);

      const seen = new Set();
      const results = [];
      for (const item of scored) {
        const d = item.doc;
        const dedupKey = `${d.type}:${d.pageId}:${d.featureId || d.hotspotId || ""}`;
        if (seen.has(dedupKey)) continue;
        seen.add(dedupKey);

        const vol = this.volById.get(d.volumeId);
        results.push({
          ...d,
          volumeTitle: vol ? vol.shortTitle : d.volumeId,
          titleHtml: highlightAr(d.title, rawQuery),
          snippetHtml: makeSnippet(d.body, rawQuery, 135),
          rawQuery,
        });
        if (results.length >= limit) break;
      }
      return results;
    }
  }

  window.AtlasSearch = { AtlasSearchEngine };
})();
