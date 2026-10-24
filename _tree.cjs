// .brand medis + fontai
const { chromium } = require('/workspace/node_modules/playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 } })).newPage();
  const reqs = [];
  page.on('response', r => { const u = r.url(); if (/fonts|gstatic|googleapis/.test(u)) reqs.push(r.status() + ' ' + u.slice(0, 110)); });
  await page.route('**/*.mp4', r => r.abort());
  await page.goto('https://penktadienioaukcionas.lt/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);
  const out = await page.evaluate(() => {
    const walk = (el, depth) => {
      const r = el.getBoundingClientRect(); const c = getComputedStyle(el);
      const pad = '  '.repeat(depth);
      let s = pad + el.tagName + (el.id ? '#' + el.id : '') + (el.className ? '.' + String(el.className).split(' ').join('.') : '') +
        ' [' + Math.round(r.left) + ',' + Math.round(r.top) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height) + ']' +
        ' disp=' + c.display + ' pos=' + c.position + ' ov=' + c.overflow + ' tf=' + c.transform.replace(/matrix\(1, 0, 0, 1, /, 'T(').replace(')', ')');
      if (el.children.length === 0) s += ' TEXT="' + (el.textContent || '').trim().slice(0, 40) + '"';
      s += '\n';
      if (depth < 3) for (const ch of el.children) s += walk(ch, depth + 1);
      return s;
    };
    const fonts = []; document.fonts.forEach(f => fonts.push(f.family + '=' + f.status));
    const ff = ['Archivo', 'Anton', 'JetBrains Mono'];
    return { tree: walk(document.querySelector('.brand'), 0), fonts,
      checks: ff.map(f => f + ':' + document.fonts.check('24px "' + f + '"')),
      bodyW: document.body.clientWidth, stageW: document.querySelector('.stage').getBoundingClientRect().width };
  });
  console.log(out.tree);
  console.log('fontai:', out.fonts.join(', '));
  console.log('check:', out.checks.join(', '), '| body', out.bodyW, 'stage', out.stageW);
  console.log('font tinklas:'); console.log(reqs.join('\n') || 'nera uzklausu');
  await browser.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
