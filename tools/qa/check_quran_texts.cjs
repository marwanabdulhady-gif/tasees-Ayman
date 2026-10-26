// أطلس القرآن — every excerpt must be an exact slice of its cited verse in the vendored Uthmani text,
// and every cited reference must exist. Runs without a browser:  node tools/qa/check_quran_texts.cjs
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "../..");
const DATA = path.join(ROOT, "atlas-modules/atlas-of-quran/data");

function verify() {
  const loc = JSON.parse(fs.readFileSync(path.join(DATA, "locations.json"), "utf8")).locations;
  const quran = JSON.parse(fs.readFileSync(path.join(DATA, "quran-uthmani.json"), "utf8")).verses;
  const problems = [];
  let refs = 0, texts = 0;
  for (const l of loc) {
    for (const r of l.verses) { refs++; if (!quran[r]) problems.push(`${l.id}: reference ${r} does not exist`); }
    for (const t of l.texts || []) {
      texts++;
      if (!quran[t.ref]) problems.push(`${l.id}: excerpt reference ${t.ref} does not exist`);
      else if (!quran[t.ref].includes(t.text)) problems.push(`${l.id}: excerpt is not in ${t.ref}: «${t.text.slice(0, 40)}»`);
      if (!l.verses.includes(t.ref)) problems.push(`${l.id}: excerpt ${t.ref} is not in the entry's verse list`);
    }
  }
  return { entries: loc.length, refs, texts, verses: Object.keys(quran).length, problems };
}

module.exports = { verify };
if (require.main === module) {
  const r = verify();
  r.problems.forEach((p) => console.log("FAIL " + p));
  console.log(`${r.problems.length ? "FAIL" : "ok"}: ${r.entries} entries · ${r.refs} references · ${r.texts} excerpts checked against ${r.verses} verses`);
  process.exit(r.problems.length ? 1 : 0);
}
