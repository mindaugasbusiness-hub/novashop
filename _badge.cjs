// Badge matavimas + screenshot (brand zona)
const { chromium } = require('/workspace/node_modules/playwright');
const URL = process.env.PROBE_URL || 'https://penktadienioaukcionas.lt/';
const TAG = process.env.TAG || 'pries';

(async () => {
  const browser = await chromium.launch();
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
  await page.route('**/*.mp4', r => r.abort());
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(4000);

  const d = await page.evaluate(() => {
    const R = el => { if (!el) return null; const r = el.getBoundingClientRect();
      return { l: +r.left.toFixed(1), r: +r.right.toFixed(1), t: +r.top.toFixed(1), b: +r.bottom.toFixed(1), w: +r.width.toFixed(1), h: +r.height.toFixed(1) }; };
    const cs = (el, p) => el ? getComputedStyle(el)[p] : null;
    const name = document.querySelector('.brand-name');
    const badge = document.querySelector('.brand-top .radio-badge');
    const even = document.querySelector('.brand-evening');
    const top = document.querySelector('.brand-top');
    const nr = R(name), br = R(badge), er = R(even);
    const ov = (a, b) => (a && b) ? +(Math.min(a.r, b.r) - Math.max(a.l, b.l)).toFixed(1) : null;
    const ovV = (a, b) => (a && b) ? +(Math.min(a.b, b.b) - Math.max(a.t, b.t)).toFixed(1) : null;
    return {
      name: nr, badge: br, evening: er, brandTop: R(top),
      badgeTransform: cs(badge, 'transform'), nameTransform: cs(name, 'transform'),
      gapName_badge: (nr && br) ? +(br.l - nr.r).toFixed(1) : null,
      overlapH_name_badge: ov(nr, br), overlapV_name_badge: ovV(nr, br),
      gapName_badge_v: (nr && br) ? +(br.t - nr.b).toFixed(1) : null,
      overlapH_badge_evening: ov(br, er), overlapV_badge_evening: ovV(br, er),
      badgeText: badge ? badge.innerText.replace(/\s+/g, ' ').trim() : null
    };
  });
  console.log('=== ' + TAG + ' ===');
  console.log(JSON.stringify(d, null, 1));
  await page.locator('.brand').screenshot({ path: '/workspace/_brand_' + TAG + '.png' }).catch(e => console.log('shot err', e.message));
  await page.screenshot({ path: '/workspace/_full_' + TAG + '.png' });
  await browser.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
