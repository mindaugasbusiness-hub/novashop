// GALUTINE patikra: .brand-evening centravimas po .brand-name (1280px) + screenshot
const { chromium } = require('/workspace/node_modules/playwright');
const URL = 'https://penktadienioaukcionas.lt/';
(async () => {
  const browser = await chromium.launch();
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(e.message));
  await page.route('**/*.mp4', r => r.abort());
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(4000);

  const d = await page.evaluate(() => {
    const R = s => { const e = document.querySelector(s); const r = e.getBoundingClientRect();
      return { l: +r.left.toFixed(1), r: +r.right.toFixed(1), t: +r.top.toFixed(1), b: +r.bottom.toFixed(1) }; };
    const ov = (a, b) => Math.round(Math.max(0, Math.min(a.r, b.r) - Math.max(a.l, b.l)) * Math.max(0, Math.min(a.b, b.b) - Math.max(a.t, b.t)));
    const n = R('.brand-name'), e = R('.brand-evening'), b = R('.brand-top .radio-badge');
    const cs = getComputedStyle(document.querySelector('.brand-evening'));
    return { transform: cs.transform, text: document.querySelector('.brand-evening').innerText.replace(/\s+/g, ' '),
      name: n, eve: e, badge: b,
      nameC: +((n.l + n.r) / 2).toFixed(1), eveC: +((e.l + e.r) / 2).toFixed(1),
      eveEilute: e.t.toFixed(0) + '-' + e.b.toFixed(0),
      deltaC: +(((e.l + e.r) / 2) - ((n.l + n.r) / 2)).toFixed(1),
      ov_badge: ov(e, b), tarpas_badge: +(b.l - e.r).toFixed(1),
      kairys_krastas_ok: e.l > 0, desinys_krastas_ok: e.r < 1280,
      docW: document.documentElement.scrollWidth, cliW: document.documentElement.clientWidth };
  });
  console.log('TRANSFORM:', d.transform);
  console.log('TEKSTAS  :', d.text);
  console.log('brand-name [' + d.name.l + '..' + d.name.r + '] centras=' + d.nameC);
  console.log('evening    [' + d.eve.l + '..' + d.eve.r + '] centras=' + d.eveC + ' eilute=' + d.eveEilute);
  console.log('badge      [' + d.badge.l + '..' + d.badge.r + ']');
  console.log('evening_c - name_c = ' + d.deltaC + ' px  (tikslas: |delta| <= 30)  -> ' + (Math.abs(d.deltaC) <= 30 ? 'OK' : 'NE OK'));
  console.log('persidengimas su badge = ' + d.ov_badge + ' px2 (turi buti 0), tarpas=' + d.tarpas_badge + ' px');
  console.log('krastai: kairys>0 ' + (d.kairys_krastas_ok ? 'OK' : 'NE') + ' (' + d.eve.l + '), desinys<1280 ' + (d.desinys_krastas_ok ? 'OK' : 'NE') + ' (' + d.eve.r + ')');
  console.log('docW=' + d.docW + ' cliW=' + d.cliW + ' | JS klaidos: ' + (errs.length ? errs.join(' | ') : 'nera'));

  await page.screenshot({ path: '/workspace/_evening_fix_1280.png' });
  await page.locator('.brand').screenshot({ path: '/workspace/_evening_fix_brand.png' });
  await browser.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
