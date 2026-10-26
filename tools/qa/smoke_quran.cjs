// Smoke test — أطلس القرآن (atlas-modules/atlas-of-quran) offline over file://
const path = require('path');
const libsDir = '/home/user/tasees-Ayman/.cache/qa/libs';
process.env.LD_LIBRARY_PATH = `${libsDir}/lib:${process.env.LD_LIBRARY_PATH || ''}`;
const puppeteer = require(path.join(__dirname, 'node_modules', 'puppeteer-core'));
const chromium = require(path.join(__dirname, 'node_modules', '@sparticuz/chromium'));

const URL = 'file:///home/user/tasees-Ayman/atlas-modules/atlas-of-quran/index.html';

(async () => {
  const browser = await puppeteer.launch({
    executablePath: await chromium.executablePath(),
    args: chromium.args.filter(a => !String(a).startsWith('--enable-automation')),
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 900 });
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('requestfailed', r => {
    const u = r.url();
    if (!u.startsWith('file://')) errors.push('net-fail: ' + u.slice(0, 80));
  });

  let pass = 0, fail = 0;
  const check = (name, ok, d) => { console.log((ok ? 'PASS' : 'FAIL') + '  ' + name + (d ? ' — ' + d : '')); ok ? pass++ : fail++; };

  await page.goto(URL, { waitUntil: 'load', timeout: 30000 });
  await new Promise(r => setTimeout(r, 1500));

  // 1. RTL Arabic + data
  const meta = await page.evaluate(() => ({
    dir: document.documentElement.dir,
    lang: document.documentElement.lang,
    title: document.title,
    locs: (window.QURAN_DATA || { locations: [] }).locations.length,
  }));
  check('RTL + Arabic + data loaded', meta.dir === 'rtl' && meta.lang === 'ar' && meta.locs === 46, 'locs=' + meta.locs);

  // 2. list items
  const nItems = await page.$$eval('ul.list li', els => els.length);
  check('sidebar list = 46 items', nItems === 46, 'items=' + nItems);

  // 3. markers
  const nMarkers = await page.$$eval('.leaflet-marker-icon', els => els.length);
  check('map markers = 46', nMarkers === 46, 'markers=' + nMarkers);

  // 4. stats
  const stats = await page.$eval('#stats', el => el.textContent);
  check('stats in header', stats.includes('46') && stats.includes('مدينة'), stats.slice(0, 60));

  // 5. search
  await page.type('#q', 'مكة');
  await new Promise(r => setTimeout(r, 400));
  const visible = await page.$$eval('ul.list li', els => els.filter(e => e.style.display !== 'none').length);
  check('search "مكة" filters list', visible >= 1 && visible < 46, 'shown=' + visible);
  await page.evaluate(() => { const i = document.getElementById('q'); i.value = ''; i.dispatchEvent(new Event('input')); });
  await new Promise(r => setTimeout(r, 200));

  // 6. click item → popup
  await page.click('ul.list li[data-id="makkah"]');
  await new Promise(r => setTimeout(r, 1600));
  const popup = await page.evaluate(() => {
    const p = document.querySelector('.leaflet-popup-content');
    return p ? {
      title: p.querySelector('.pp-title').textContent,
      verse: p.querySelector('.pp-verse') ? p.querySelector('.pp-verse').textContent.includes('مَثَابَةً') : false
    } : null;
  });
  check('popup opens with Quran text', !!popup && popup.title.includes('مكة') && popup.verse, popup && popup.title);

  // 7. confidence badge
  const conf = await page.$eval('.leaflet-popup .badge', el => el.textContent).catch(() => '');
  check('confidence badge', conf === 'مرفوع', conf);

  // 8. graticule
  const grat = await page.evaluate(() => document.querySelectorAll('#map path').length);
  check('graticule drawn', grat >= 20, 'paths=' + grat);

  // 9. type chips
  const chips = await page.$$eval('.chips .chip', els => els.map(e => e.textContent));
  check('type chips rendered', chips.length >= 5, chips.join(' | ').slice(0, 120));

  // 10. no JS errors (external tile/iframe failures expected offline are filtered)
  const realErrors = errors.filter(e =>
    !e.includes('basemaps.cartocdn') && !e.includes('google.com') &&
    !e.includes('ERR_NAME_NOT_RESOLVED') && !e.includes('ERR_INTERNET_DISCONNECTED') &&
    !e.includes('net-err') && !e.includes('ERR_') && !e.startsWith('net-fail'));
  check('no JS errors', realErrors.length === 0, realErrors.slice(0, 3).join(' ; '));

  await page.screenshot({ path: '/home/user/tasees-Ayman/.cache/qa/quran_smoke.png' });
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  await browser.close();
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('SMOKE CRASH:', e); process.exit(2); });
