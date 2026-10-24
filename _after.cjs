// Testas: kaip atrodys PO pakeitimu (CSS override, failo dar nelieciam)
const { chromium } = require('/workspace/node_modules/playwright');
const URL = 'https://penktadienioaukcionas.lt/';
const OVERRIDE = process.env.CSS || '';
const VPS = (process.env.VPS || '1280,1100,1000').split(',').map(Number);
(async () => {
  const browser = await chromium.launch();
  for (const w of VPS) {
    const page = await (await browser.newContext({ viewport: { width: w, height: 800 } })).newPage();
    await page.route('**/*.mp4', r => r.abort());
    await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    if (OVERRIDE) await page.addStyleTag({ content: OVERRIDE });
    await page.waitForTimeout(300);
    const m = await page.evaluate(() => {
      const R = s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect();
        return { l: +r.left.toFixed(1), r: +r.right.toFixed(1), t: +r.top.toFixed(1), b: +r.bottom.toFixed(1) }; };
      const ov = (a, b) => Math.round(Math.max(0, Math.min(a.r, b.r) - Math.max(a.l, b.l)) * Math.max(0, Math.min(a.b, b.b) - Math.max(a.t, b.t)));
      const name = R('.brand-name'), badge = R('.brand-top .radio-badge'), strip = R('#payStrip'), panel = R('#participantsPanel');
      return { name, badge, strip,
        tarpas: +(badge.l - name.r).toFixed(1), ov_name: ov(name, badge), ov_strip: ov(badge, strip),
        ov_panel: ov(badge, panel), panelRight: panel.r, nameLeft: name.l, badgeRight: badge.r, stripLeft: strip.l };
    });
    // Taisykliu ir PayPal paspaudimo testas
    await page.click('#aqrToggle'); await page.waitForTimeout(400);
    const rules = await page.evaluate(() => {
      const p = document.getElementById('aqrPanel'); const r = p.getBoundingClientRect();
      const t = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
      return { open: p.classList.contains('open'), y: Math.round(r.y), h: Math.round(r.height),
        virsuje: t ? t.tagName + '.' + String(t.className).slice(0, 30) : null };
    });
    await page.click('#aqrToggle'); await page.waitForTimeout(200);
    await page.click('.pay-badge.paypal'); await page.waitForTimeout(400);
    const pay = await page.evaluate(() => {
      const d = document.getElementById('payStripDetail'); const r = d.getBoundingClientRect();
      const t = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
      return { on: d.classList.contains('on'), y: Math.round(r.y), h: Math.round(r.height),
        virsuje: t ? t.tagName + '.' + String(t.className).slice(0, 30) : null };
    });
    console.log('vw=' + w, '| tarpas name-badge=' + m.tarpas, '| ov name/badge=' + m.ov_name,
      '| ov badge/strip=' + m.ov_strip, '| ov badge/panel=' + m.ov_panel,
      '| nameLeft=' + m.nameLeft, 'panelRight=' + m.panelRight, 'badgeRight=' + m.badgeRight, 'stripLeft=' + m.stripLeft);
    console.log('    Taisykles:', JSON.stringify(rules), '| PayPal:', JSON.stringify(pay));
    if (process.env.SHOT) await page.screenshot({ path: '/workspace/_after_' + (process.env.SHOT) + '_' + w + '.png' });
    await page.close();
  }
  await browser.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
