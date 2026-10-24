// Kur badge susiduria su pay-strip? (viewport testas)
const { chromium } = require('/workspace/node_modules/playwright');
const URL = 'https://penktadienioaukcionas.lt/';
const VPS = [1280, 1200, 1150, 1128, 1100, 1050, 1000, 950, 900];
(async () => {
  const browser = await chromium.launch();
  for (const w of VPS) {
    const page = await (await browser.newContext({ viewport: { width: w, height: 800 } })).newPage();
    await page.route('**/*.mp4', r => r.abort());
    await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    const d = await page.evaluate(() => {
      const R = s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect();
        return { l: +r.left.toFixed(1), r: +r.right.toFixed(1), t: +r.top.toFixed(1), b: +r.bottom.toFixed(1) }; };
      const ov = (a, b) => Math.max(0, Math.min(a.r, b.r) - Math.max(a.l, b.l)) * Math.max(0, Math.min(a.b, b.b) - Math.max(a.t, b.t));
      const badge = R('.brand-top .radio-badge'), strip = R('#payStrip'), name = R('.brand-name'), panel = R('#participantsPanel');
      return { docW: document.documentElement.scrollWidth, cliW: document.documentElement.clientWidth,
        bodyW: document.body.getBoundingClientRect().width,
        badge, strip, name, panel,
        badge_strip_overlap: Math.round(ov(badge, strip)),
        badge_name_overlap: Math.round(ov(badge, name)),
        badge_panel_overlap: Math.round(ov(badge, panel)),
        gap_name_badge: +(badge.l - name.r).toFixed(1) };
    });
    console.log('vw=' + w, 'doc=' + d.docW, 'cli=' + d.cliW, 'body=' + Math.round(d.bodyW),
      '| badge[' + d.badge.l + '..' + d.badge.r + ']', 'strip[' + d.strip.l + '..' + d.strip.r + ']',
      '| badge/strip ov=' + d.badge_strip_overlap, 'badge/name ov=' + d.badge_name_overlap,
      'badge/panel ov=' + d.badge_panel_overlap, 'tarpas=' + d.gap_name_badge);
    await page.close();
  }
  await browser.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
