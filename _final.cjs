// GALUTINE patikra: visi 4 mokejimo zenklai + Taisykles, screenshot'ai
const { chromium } = require('/workspace/node_modules/playwright');
const URL = 'https://penktadienioaukcionas.lt/';
(async () => {
  const browser = await chromium.launch();
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !/ERR_FAILED|ERR_ABORTED/.test(m.text())) errs.push(m.text()); });
  await page.route('**/*.mp4', r => r.abort());
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(4000);

  const geo = await page.evaluate(() => {
    const R = s => { const e = document.querySelector(s); const r = e.getBoundingClientRect();
      return { l: +r.left.toFixed(1), r: +r.right.toFixed(1), t: +r.top.toFixed(1), b: +r.bottom.toFixed(1) }; };
    const ov = (a, b) => Math.round(Math.max(0, Math.min(a.r, b.r) - Math.max(a.l, b.l)) * Math.max(0, Math.min(a.b, b.b) - Math.max(a.t, b.t)));
    const n = R('.brand-name'), b = R('.brand-top .radio-badge'), s = R('#payStrip'), p = R('#participantsPanel');
    return { tarpas: +(b.l - n.r).toFixed(1), ov_name: ov(n, b), ov_strip: ov(b, s), ov_panel: ov(b, p),
      name: n, badge: b, strip: s, badgeText: document.querySelector('.radio-choice').innerText.replace(/\s+/g, ' ') };
  });
  console.log('GEO:', JSON.stringify(geo));

  // Taisykles
  await page.click('#aqrToggle'); await page.waitForTimeout(500);
  const rules = await page.evaluate(() => {
    const p = document.getElementById('aqrPanel'); const r = p.getBoundingClientRect();
    const t = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
    return { open: p.classList.contains('open'), display: getComputedStyle(p).display, y: Math.round(r.y), h: Math.round(r.height),
      virsuje: t ? t.tagName + '.' + String(t.className).slice(0, 24) : null };
  });
  console.log('TAISYKLES:', JSON.stringify(rules));
  await page.screenshot({ path: '/workspace/ui-fix-taisykles.png' });
  await page.click('#aqrToggle'); await page.waitForTimeout(300);

  // Visi 4 mokejimo zenklai
  for (const p of ['paypal', 'skrill', 'neteller', 'paysafe']) {
    await page.click('.pay-badge.' + p); await page.waitForTimeout(400);
    const r = await page.evaluate(() => {
      const d = document.getElementById('payStripDetail'); const b = d.getBoundingClientRect();
      const t = document.elementFromPoint(b.x + b.width / 2, b.y + b.height / 2);
      return { on: d.classList.contains('on'), name: document.getElementById('psdName').textContent.slice(0, 22),
        y: Math.round(b.y), h: Math.round(b.height), virsuje: t ? t.tagName + '.' + String(t.className).slice(0, 20) : null,
        radio: (document.querySelector('input[name="payMethod"]:checked') || {}).value };
    });
    console.log('PAY-' + p + ':', JSON.stringify(r));
    if (p === 'skrill') await page.screenshot({ path: '/workspace/ui-fix-mokejimas.png' });
  }
  console.log('JS klaidos:', errs.length ? errs.join(' | ') : 'nera');
  await browser.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
