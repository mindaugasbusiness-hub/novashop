// Paneles vidaus elementu hit-testas (ar kas nors uzdengia)
const { chromium } = require('/workspace/node_modules/playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
  await page.route('**/*.mp4', r => r.abort());
  await page.goto('https://penktadienioaukcionas.lt/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(4000);
  await page.click('#aqrToggle'); await page.waitForTimeout(600);
  const r = await page.evaluate(() => {
    const out = [];
    const p = document.getElementById('aqrPanel'); const pr = p.getBoundingClientRect();
    out.push(['panel', Math.round(pr.x) + ',' + Math.round(pr.y) + ' ' + Math.round(pr.width) + 'x' + Math.round(pr.height), getComputedStyle(p).overflow]);
    p.querySelectorAll('li, .aqr-contact a, .aqr-contact, #aqrClose').forEach(el => {
      const b = el.getBoundingClientRect();
      const t = document.elementFromPoint(b.x + b.width / 2, b.y + b.height / 2);
      out.push([el.tagName + (el.id ? '#' + el.id : '.' + String(el.className).slice(0, 12)), (el.innerText || '').replace(/\s+/g, ' ').slice(0, 34),
        'rect=' + Math.round(b.x) + '..' + Math.round(b.right), 'virsuje=' + (t ? t.tagName + '.' + String(t.className).slice(0, 16) : 'null')]);
    });
    // ar panelė tilptu ekrane
    out.push(['panel apacia', Math.round(pr.bottom), 'viewport 800', pr.bottom <= 800 ? 'TELPA' : 'NETELPA']);
    return out;
  });
  r.forEach(x => console.log(x.join(' | ')));
  await browser.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
