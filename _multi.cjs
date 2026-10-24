// Multi-viewport matavimas: brand-name vs radio-badge ir badge vs brand-evening
const { chromium } = require('/workspace/node_modules/playwright');
const URL = 'https://penktadienioaukcionas.lt/';
const VPS = [[1280, 800], [1366, 768], [1440, 900], [1920, 1080], [1024, 768], [900, 800], [800, 600]];
(async () => {
  const browser = await chromium.launch();
  for (const [w, h] of VPS) {
    const page = await (await browser.newContext({ viewport: { width: w, height: h } })).newPage();
    await page.route('**/*.mp4', r => r.abort());
    await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3500);
    const d = await page.evaluate(() => {
      const R = s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect();
        return { l: +r.left.toFixed(1), r: +r.right.toFixed(1), t: +r.top.toFixed(1), b: +r.bottom.toFixed(1), w: +r.width.toFixed(1), h: +r.height.toFixed(1) }; };
      const n = R('.brand-name'), b = R('.brand-top .radio-badge'), e = R('.brand-evening');
      if (!n || !b || !e) return { missing: { name: !n, badge: !b, evening: !e } };
      const ovh = (a, c) => Math.max(0, Math.min(a.r, c.r) - Math.max(a.l, c.l));
      const ovv = (a, c) => Math.max(0, Math.min(a.b, c.b) - Math.max(a.t, c.t));
      return { name: n, badge: b, evening: e,
        gap_name_badge: +(b.l - n.r).toFixed(1),
        ov_name: +Math.min(ovh(n, b), ovv(n, b)).toFixed(1),
        gap_badge_evening_h: +(e.l - b.r).toFixed(1),
        ov_badge_evening: +Math.min(ovh(b, e), ovv(b, e)).toFixed(1),
        badgeText: (document.querySelector('.radio-choice') || {}).innerText };
    });
    if (d.missing) { console.log(w + 'x' + h, 'NERA elementu:', JSON.stringify(d.missing)); await page.close(); continue; }
    console.log(w + 'x' + h, 'name[' + d.name.l + '..' + d.name.r + ' y' + d.name.t + '-' + d.name.b + ']',
      'badge[' + d.badge.l + '..' + d.badge.r + ' y' + d.badge.t + '-' + d.badge.b + ']',
      'evening[' + d.evening.l + '..' + d.evening.r + ' y' + d.evening.t + '-' + d.evening.b + ']');
    console.log('   tarpas name-badge:', d.gap_name_badge, '| persidengimas name/badge:', d.ov_name,
      '| tarpas badge-evening H:', d.gap_badge_evening_h, '| persidengimas badge/evening:', d.ov_badge_evening);
    if (w === 1280 || w === 1920) { await page.locator('.brand').screenshot({ path: '/workspace/_brand_' + w + '.png' }); }
    await page.close();
  }
  await browser.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
