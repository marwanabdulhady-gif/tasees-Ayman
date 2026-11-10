/*
 * NotebookLM — export the full text (transcripts) of EVERY source in the open notebook.
 *
 * How to use:
 *   1. Open the notebook at https://notebooklm.google.com/notebook/<id>
 *      (a notebook opened from Gemini: use "Open in NotebookLM" first).
 *   2. Press F12 → Console. Chrome may ask you to type: allow pasting
 *   3. Paste this whole file and press Enter.
 *
 * Output (downloaded by the browser):
 *   <notebook>_sources.md    — every source, one after another, with its title
 *   <notebook>_sources.json  — same data, machine-readable
 *   one .txt per source      — only if SEPARATE_FILES = true
 * The result also stays in the console as `window.notebookSources`.
 *
 * It only reads; it changes nothing in the notebook. It uses NotebookLM's own
 * internal calls with your logged-in session, so if Google changes them the
 * script stops working and prints why.
 */
(async () => {
  const SEPARATE_FILES = false; // true → also one .txt file per source
  const DELAY_MS = 400;         // pause between sources, to be gentle

  const RPC_GET_NOTEBOOK = 'rLM1Ne';
  const RPC_GET_SOURCE = 'hizoJc';
  const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  const notebookId = (location.pathname.match(/\/notebook\/([\w-]+)/) || [])[1];
  const wiz = window.WIZ_global_data || {};
  const at = wiz.SNlM0e;
  if (!location.hostname.endsWith('notebooklm.google.com') || !notebookId) {
    console.error('Open a notebook on notebooklm.google.com/notebook/... first, then run this again.');
    return;
  }
  if (!at) {
    console.error('Could not find the session token (WIZ_global_data.SNlM0e). Reload the page and try again.');
    return;
  }

  let reqId = 100000 + Math.floor(Math.random() * 900000);
  async function rpc(rpcId, params) {
    const query = new URLSearchParams({
      rpcids: rpcId,
      'source-path': '/notebook/' + notebookId,
      hl: 'en',
      _reqid: String((reqId += 100000)),
      rt: 'c',
    });
    if (wiz.cfb2h) query.set('bl', wiz.cfb2h);
    if (wiz.FdrFJe) query.set('f.sid', wiz.FdrFJe);
    const body = new URLSearchParams({
      'f.req': JSON.stringify([[[rpcId, JSON.stringify(params), null, 'generic']]]),
      at,
    });
    const res = await fetch('/_/LabsTailwindUi/data/batchexecute?' + query, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
      body,
    });
    if (!res.ok) throw new Error(`${rpcId}: HTTP ${res.status}`);
    const raw = await res.text();
    for (const line of raw.split('\n')) {
      if (!line.includes('"wrb.fr"')) continue;
      let chunk;
      try { chunk = JSON.parse(line); } catch { continue; }
      for (const item of chunk) {
        if (item[0] === 'wrb.fr' && item[1] === rpcId) return item[2] ? JSON.parse(item[2]) : null;
      }
    }
    throw new Error(`${rpcId}: no data in the response`);
  }

  // A source entry looks like [[<uuid>], <title>, ...]; find them wherever they sit.
  function findSources(node, found = new Map()) {
    if (!Array.isArray(node)) return found;
    const head = node[0];
    if (Array.isArray(head) && head.length === 1 && typeof head[0] === 'string'
        && UUID.test(head[0]) && typeof node[1] === 'string') {
      if (!found.has(head[0])) found.set(head[0], node[1]);
      return found;
    }
    for (const child of node) findSources(child, found);
    return found;
  }

  function collectStrings(node, out = []) {
    if (typeof node === 'string') {
      const s = node.trim();
      if (s && !UUID.test(s) && out[out.length - 1] !== s) out.push(s);
    } else if (Array.isArray(node)) {
      for (const child of node) collectStrings(child, out);
    }
    return out;
  }

  function sourceText(data, title) {
    let parts = Array.isArray(data?.[3]) ? collectStrings(data[3]) : [];
    if (parts.join('').length < 200) parts = collectStrings(data).filter((s) => s !== title);
    if (!parts.length) return '';
    // Short pieces = transcript segments → one flowing text; long pieces = paragraphs.
    const average = parts.join('').length / parts.length;
    return parts.join(average < 60 ? ' ' : '\n\n').replace(/[ \t]+/g, ' ').trim();
  }

  function download(name, text, type) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([text], { type }));
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 2000);
  }
  const safeName = (s) => (s || 'untitled').replace(/[\\/:*?"<>|\n\r]+/g, '_').slice(0, 120).trim();
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  console.log('Reading the source list…');
  const notebook = await rpc(RPC_GET_NOTEBOOK, [notebookId, null, [2], null, 0]);
  const sources = [...findSources(notebook)].map(([id, title]) => ({ id, title }));
  if (!sources.length) {
    window.__notebookDebug = notebook;
    console.error('No sources found. Google may have changed the format; raw reply saved in window.__notebookDebug.');
    return;
  }
  console.log(`Found ${sources.length} sources.`);

  const results = [];
  for (const [i, src] of sources.entries()) {
    const label = `[${i + 1}/${sources.length}] ${src.title}`;
    try {
      const data = await rpc(RPC_GET_SOURCE, [[src.id], [2], [2]]);
      const text = sourceText(data, src.title);
      results.push({ ...src, chars: text.length, text });
      console.log(`${label} — ${text.length.toLocaleString()} characters`);
      if (!text) console.warn(`${label}: empty (still processing, or an image/PDF with no text?)`);
    } catch (err) {
      results.push({ ...src, chars: 0, text: '', error: String(err.message || err) });
      console.warn(`${label}: FAILED — ${err.message || err}`);
    }
    await sleep(DELAY_MS);
  }

  const notebookTitle = safeName(document.title.replace(/\s*[-|–]\s*NotebookLM\s*$/i, '')) || notebookId;
  const markdown = [
    `# ${notebookTitle}`,
    '',
    `${results.length} sources · exported ${new Date().toISOString()}`,
    '',
    ...results.map((r, i) => [
      `## ${i + 1}. ${r.title}`,
      '',
      r.error ? `> Failed: ${r.error}` : (r.text || '> (no text)'),
      '',
    ].join('\n')),
  ].join('\n');

  download(`${notebookTitle}_sources.md`, markdown, 'text/markdown;charset=utf-8');
  download(`${notebookTitle}_sources.json`, JSON.stringify({ notebookId, title: notebookTitle, sources: results }, null, 2), 'application/json');
  if (SEPARATE_FILES) {
    for (const [i, r] of results.entries()) {
      if (!r.text) continue;
      download(`${String(i + 1).padStart(2, '0')}_${safeName(r.title)}.txt`, r.text, 'text/plain;charset=utf-8');
      await sleep(300);
    }
  }

  window.notebookSources = results;
  console.table(results.map(({ title, chars, error }) => ({ title, chars, error: error || '' })));
  const failed = results.filter((r) => !r.text).length;
  console.log(`Done: ${results.length - failed}/${results.length} sources exported. Data also in window.notebookSources`);
})();
