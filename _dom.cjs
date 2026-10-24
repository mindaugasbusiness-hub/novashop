// Detalus .brand DOM tyrimas
const { chromium } = require('/workspace/node_modules/playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
  await page.route('**/*.mp4', r => r.abort());
  await page.goto('https://penktadienioaukcionas.lt/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);
  const d = await page.evaluate(() => {
    const dump = sel => Array.from(document.querySelectorAll(sel)).map(el => {
      const r = el.getBoundingClientRect(); const c = getComputedStyle(el);
      return { sel, html: el.outerHTML.slice(0, 220), disp: c.display, vis: c.visibility, op: c.opacity,
        fs: c.fontSize, ff: c.fontFamily.slice(0, 30), color: c.color, tf: c.transform,
        w: +r.width.toFixed(1), h: +r.height.toFixed(1), x: +r.left.toFixed(1), y: +r.top.toFixed(1),
        textLen: (el.textContent || '').length, clientW: el.clientWidth, clientH: el.clientHeight };
    });
    const fonts = []; try { document.fonts.forEach(f => fonts.push(f.family + ' ' + f.status)); } catch (e) {}
    return {
      brand: dump('.brand'), brandName: dump('.brand-name'), brandTop: dump('.brand-top'),
      brandEvening: dump('.brand-evening'), badge: dump('.radio-badge'), choice: dump('.radio-choice'),
      cover: document.body.className, fontsLoaded: fonts.slice(0, 12),
      styleTags: document.querySelectorAll('style').length,
      sheets: Array.from(document.styleSheets).map(s => { try { return (s.href || 'inline') + ':' + s.cssRules.length; } catch (e) { return 'blocked'; } })
    };
  });
  console.log(JSON.stringify(d, null, 1));
  await browser.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
