// Diagnostika: foto/sokeju elementu geometrija live svetaineje (1280x900)
const { chromium } = require('/workspace/node_modules/playwright');
const URL = process.env.PROBE_URL || 'https://penktadienioaukcionas.lt/';
const SEL = ['.stage', '#showcase', '#showcaseImg', '.wolf-table', '#wolfPop', '.wolf-photo', '#wolfPhotoImg', '.brand', '.brand-name'];

const js = (sel) => {
  const R = el => { if (!el) return null; const r = el.getBoundingClientRect();
    return { x: +r.x.toFixed(1), y: +r.y.toFixed(1), w: +r.width.toFixed(1), h: +r.height.toFixed(1),
             right: +r.right.toFixed(1), bottom: +r.bottom.toFixed(1) }; };
  const out = {};
  for (const s of sel) {
    const el = document.querySelector(s);
    if (!el) { out[s] = 'NERA'; continue; }
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const t = (r.width && r.height) ? document.elementFromPoint(Math.min(innerWidth - 1, r.x + r.width / 2), Math.min(innerHeight - 1, r.y + r.height / 2)) : null;
    out[s] = { rect: R(el), display: cs.display, visibility: cs.visibility, opacity: cs.opacity,
      zIndex: cs.zIndex, transform: cs.transform, overflow: cs.overflow,
      topAtCenter: t ? t.tagName + '.' + String(t.className || '').slice(0, 26) + '#' + (t.id || '') : null };
  }
  const vids = [...document.querySelectorAll('video')].map(v => {
    const cs = getComputedStyle(v);
    return { src: String(v.currentSrc || v.getAttribute('src') || '').slice(-60), display: cs.display,
      vis: cs.visibility, rect: R(v), paused: v.paused, ready: v.readyState, cls: String(v.className || '') };
  });
  return { body: document.body.className, viewport: innerWidth + 'x' + innerHeight,
    scrollY: Math.round(window.scrollY), docH: document.documentElement.scrollHeight, els: out, videos: vids,
    dancerCount: (document.getElementById('dancerCount') || {}).textContent || null,
    mainPanel: R(document.getElementById('mainPanel')) };
};

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text().slice(0, 160)); });
  page.on('pageerror', e => errors.push('pageerror: ' + e.message.slice(0, 160)));

  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(9000);

  console.log('=== A) PO IKELIMO (intro / cover-mode) ===');
  console.log(JSON.stringify(await page.evaluate(js, SEL), null, 1));
  await page.screenshot({ path: '/workspace/_diag_intro.png' });

  // isjungiam intro (cover-mode) taip pat, kaip tai daro syncCoverMode()
  await page.evaluate(() => {
    document.body.classList.remove('cover-mode');
    try { if (typeof syncCoverMode === 'function') { /* paliekam rankini valdyma */ } } catch (e) {}
    try { if (typeof render === 'function' && window.state) render(); } catch (e) {}
  });
  await page.waitForTimeout(3500);
  console.log('=== B) PO INTRO ISJUNGIMO (aukciono rezimas) ===');
  console.log(JSON.stringify(await page.evaluate(js, SEL), null, 1));
  await page.screenshot({ path: '/workspace/_diag_show.png' });

  // api/dancer tiesiai is puslapio konteksto
  const api = await page.evaluate(async () => {
    const a = await (await fetch('/api/dancer', { cache: 'no-store' })).json();
    const b = await (await fetch('/api/dancer/next', { method: 'POST' })).json();
    return { dancer: a, next: b };
  });
  console.log('=== C) API ===');
  console.log(JSON.stringify(api));

  console.log('=== D) JS klaidos ===');
  console.log(errors.length ? errors.join('\n') : 'nera');
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
