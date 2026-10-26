#!/usr/bin/env node
// Apply manually inspected image-space anchors. Never infer anchors from page centres.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const zlib = require('zlib');
const ROOT = path.resolve(__dirname, '..');
function validate(review, manifest) {
  const errors = [];
  const maps = manifest.pages.filter(p => p.volumeId === 'dawal' && p.category === 'map');
  if (maps.length !== 89 || Object.keys(review.pages).length !== 89 || maps.some(p => !review.pages[p.id])) {
    errors.push('Dawal requires visual evidence for all 89 map pages');
  }
  for (const [id, r] of Object.entries(review.pages)) {
    const page = manifest.pages.find(p => p.id === id);
    if (!page || page.volumeId !== 'dawal') { errors.push(`${id}: missing page`); continue; }
    const image = fs.readFileSync(path.join(ROOT, page.pageAsset));
    if (crypto.createHash('sha256').update(image).digest('hex') !== r.imageSha256) errors.push(`${id}: source image changed; re-review required`);
    if (r.width !== page.width || r.height !== page.height) errors.push(`${id}: image dimensions changed`);
    if (!r.evidence || !r.name || !Number.isFinite(r.pixelX) || !Number.isFinite(r.pixelY) || r.pixelX < 0 || r.pixelX > r.width || r.pixelY < 0 || r.pixelY > r.height) errors.push(`${id}: invalid visual evidence/coordinates`);
    const h = page.hotspots.find(h => h.placementStatus === 'visually-reviewed');
    if (!h || h.kind !== (r.kind || 'city') || h.name !== r.name || Math.abs(h.x - (r.pixelX / r.width * 100 - 2.5)) > .011 || Math.abs(h.y - (r.pixelY / r.height * 100 - 2.5)) > .011 || h.w !== 5 || h.h !== 5) errors.push(`${id}: applied hotspot does not match reviewed anchor`);
  }
  for (const p of manifest.pages.filter(p => p.volumeId === 'dawal')) {
    for (const h of p.hotspots || []) {
      if (h.placementStatus === 'visually-reviewed' && !review.pages[p.id]) errors.push(`${p.id}: unsupported review claim`);
      if (!review.pages[p.id] && (h.placementStatus !== 'estimated' || h.conf !== 'low')) errors.push(`${p.id}: unreviewed placement must be explicitly estimated/low confidence`);
    }
  }
  return errors;
}
if (require.main === module) {
  const review = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/dawal_hotspot_review.json')));
  const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/manifest.json')));
  for (const p of manifest.pages.filter(p => p.volumeId === 'dawal' && p.hotspots.length)) {
    const r = review.pages[p.id];
    if (r) {
      p.hotspots = [{id: `${p.id}-reviewed-city`, name: r.name, kind: r.kind || 'city', x: +(r.pixelX/r.width*100-2.5).toFixed(2), y: +(r.pixelY/r.height*100-2.5).toFixed(2), w: 5, h: 5, fact: `${r.evidence} الموضع مقاس على صورة الصفحة الأصلية، وليس إحداثيات جغرافية.`, conf: 'high', placementStatus: 'visually-reviewed'}];
    } else {
      for (const h of p.hotspots) {
        h.conf = 'low'; h.placementStatus = 'estimated';
        h.fact = 'علامة عامة تقديرية في وسط الصفحة لفتح بطاقة الخريطة؛ لا تحدد موقع مدينة أو حدود دولة. لم يُراجع موضعها بصريًا بعد.';
      }
    }
  }
  const errors = validate(review, manifest);
  if (errors.length) throw new Error(errors.join('\n'));
  fs.writeFileSync(path.join(ROOT, 'data/manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
  fs.writeFileSync(path.join(ROOT, 'data/atlas-bundle.js'), `window.__ATLAS_MANIFEST_GZ__ = ${JSON.stringify(zlib.gzipSync(Buffer.from(JSON.stringify(manifest))).toString('base64'))};\n`);
  console.log(`Applied ${Object.keys(review.pages).length}/89 visual reviews.`);
}
module.exports = { validate };
