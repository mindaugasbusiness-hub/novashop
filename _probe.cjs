// Vizuali diagnostika: badge persidengimas + pay-strip paneles
const { chromium } = require('/workspace/node_modules/playwright');

const URL = process.env.PROBE_URL || 'https://penktadienioaukcionas.lt/';

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  // greitinam: blokuojam video
  await page.route('**/*.mp4', r => r.abort());

  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(4000);

  const info = await page.evaluate(() => {
    const R = el => { if (!el) return null; const r = el.getBoundingClientRect();
      return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height),
               right: Math.round(r.right), bottom: Math.round(r.bottom) }; };
    const at = (el) => { if (!el) return null; const r = el.getBoundingClientRect();
      const t = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
      return t ? (t.tagName + '.' + (t.className || '') + '#' + (t.id || '')) : null; };
    const q = s => document.querySelector(s);
    const name = q('.brand-name'), badge = q('.brand-top .radio-badge');
    const nr = name ? name.getBoundingClientRect() : null, br = badge ? badge.getBoundingClientRect() : null;
    const strip = q('.pay-strip');
    const stripCS = strip ? getComputedStyle(strip) : null;
    return {
      bodyClass: document.body.className,
      brandName: R(name), radioBadge: R(badge), brandTop: R(q('.brand-top')),
      gapPx: (nr && br) ? Math.round(br.left - nr.right) : null,
      overlapPx: (nr && br) ? Math.round(Math.min(nr.right, br.right) - Math.max(nr.left, br.left)) : null,
      strip: R(strip), stripOverflow: stripCS ? stripCS.overflow : null, stripZ: stripCS ? stripCS.zIndex : null,
      aqrToggle: R(q('#aqrToggle')), aqrToggleHit: at(q('#aqrToggle')),
      paypal: R(q('.pay-badge.paypal')), paypalHit: at(q('.pay-badge.paypal')),
      payStripDetailDisplay: getComputedStyle(q('#payStripDetail')).display,
      aqrPanelDisplay: getComputedStyle(q('#aqrPanel')).display
    };
  });
  console.log('--- BUVO (pries pakeitimus) ---');
  console.log(JSON.stringify(info, null, 1));

  await page.click('#aqrToggle');
  await page.waitForTimeout(500);
  const afterRules = await page.evaluate(() => {
    const p = document.getElementById('aqrPanel'); const r = p.getBoundingClientRect();
    const cx = r.x + r.width / 2, cy = r.y + r.height / 2;
    const top = document.elementFromPoint(cx, cy);
    const strip = document.querySelector('.pay-strip');
    const sr = strip.getBoundingClientRect();
    const cs = getComputedStyle(strip);
    return { open: p.classList.contains('open'), display: getComputedStyle(p).display, rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
      clipBox: { x: Math.round(sr.x), y: Math.round(sr.y), w: Math.round(sr.width), h: Math.round(sr.height), overflow: cs.overflow, clip: cs.clipPath },
      panelCenterInsideStrip: cy <= sr.bottom, topElementAtPanelCenter: top ? top.tagName + '.' + (top.className || '') : null };
  });
  console.log('--- PO #aqrToggle paspaudimo ---');
  console.log(JSON.stringify(afterRules, null, 1));
  await page.screenshot({ path: '/workspace/_shot_rules.png' });

  await page.click('#aqrToggle'); // uzdarom
  await page.click('.pay-badge.paypal');
  await page.waitForTimeout(500);
  const afterPay = await page.evaluate(() => {
    const d = document.getElementById('payStripDetail'); const r = d.getBoundingClientRect();
    const cx = r.x + r.width / 2, cy = r.y + r.height / 2;
    const top = document.elementFromPoint(cx, cy);
    const strip = document.querySelector('.pay-strip'); const sr = strip.getBoundingClientRect();
    return { on: d.classList.contains('on'), display: getComputedStyle(d).display,
      rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
      stripBottom: Math.round(sr.bottom), detailCenterInsideStrip: cy <= sr.bottom,
      topElementAtDetailCenter: top ? top.tagName + '.' + (top.className || '') : null };
  });
  console.log('--- PO PayPal paspaudimo ---');
  console.log(JSON.stringify(afterPay, null, 1));
  await page.screenshot({ path: '/workspace/_shot_pay.png' });

  console.log('--- JS KLAIDOS ---');
  console.log(errors.length ? errors.join('\n') : 'nera');
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
