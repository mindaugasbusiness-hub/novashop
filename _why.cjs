// Kodel elementai dingsta? Diagnostika
const { chromium } = require('/workspace/node_modules/playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
  page.on('framenavigated', f => { if (f === page.mainFrame()) console.log('NAV ->', f.url()); });
  page.on('console', m => console.log('CONSOLE', m.type(), m.text().slice(0, 160)));
  await page.route('**/*.mp4', r => r.abort());
  const resp = await page.goto('https://penktadienioaukcionas.lt/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  console.log('status', resp.status(), 'url', page.url());
  for (const t of [1500, 3000, 5000, 8000]) {
    await page.waitForTimeout(t === 1500 ? 1500 : 1500);
    const d = await page.evaluate(() => ({
      t: Math.round(performance.now()), ready: document.readyState, url: location.href,
      bodyClass: document.body ? document.body.className : 'NO BODY',
      htmlLen: document.documentElement.outerHTML.length,
      nBrand: document.querySelectorAll('.brand').length, nStage: document.querySelectorAll('.stage').length,
      nName: document.querySelectorAll('.brand-name').length, nBadge: document.querySelectorAll('#radioBadge').length,
      title: document.title
    }));
    console.log(JSON.stringify(d));
  }
  await browser.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
