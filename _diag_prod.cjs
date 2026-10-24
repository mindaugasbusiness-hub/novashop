// Produkto foto (item kortele) matavimas: .art img / #artPhoto
const { chromium } = require('/workspace/node_modules/playwright');
const URL = process.env.PROBE_URL || 'https://penktadienioaukcionas.lt/';
const SHOT = process.env.SHOT || '';

const js = () => {
  const R = el => { if (!el) return null; const r = el.getBoundingClientRect();
    return { x: +r.x.toFixed(1), y: +r.y.toFixed(1), w: +r.width.toFixed(1), h: +r.height.toFixed(1),
             right: +r.right.toFixed(1), bottom: +r.bottom.toFixed(1) }; };
  const q = s => document.querySelector(s);
  const img = document.getElementById('artPhoto');
  const art = document.getElementById('artWrap');
  const card = document.getElementById('mainPanel');
  const out = { body: document.body.className,
    artWrap: R(art), artPhoto: R(img), card: R(card),
    artCS: art ? (({ overflow, background }) => ({ overflow, background: background.slice(0, 40) }))(getComputedStyle(art)) : null,
    imgCS: img ? (({ maxHeight, width, flex, objectFit, objectPosition, transform, display }) =>
      ({ maxHeight, width, flex, objectFit, objectPosition, transform, display }))(getComputedStyle(img)) : null,
    natural: img ? { w: img.naturalWidth, h: img.naturalHeight, src: String(img.currentSrc).slice(-40) } : null,
    itemTitle: R(document.getElementById('itemTitle')), descBox: R(q('.desc-box')),
    bidBtn: R(document.getElementById('bidBtn')), priceNum: R(document.getElementById('priceNum')),
    panelLeft: R(q('#participantsPanel')), wolf: R(document.getElementById('wolfPop')),
    queueRail: R(q('.queue-rail')), lotTag: R(q('.lot-tag')), viewers: R(q('.viewers')) };
  // turinio (matomos foto dalies) ribos pagal contain+object-position
  if (img && art) {
    const ar = art.getBoundingClientRect(), ir = img.getBoundingClientRect();
    const nA = img.naturalWidth / img.naturalHeight, boxA = ir.width / ir.height;
    let cw, ch;
    if (nA > boxA) { cw = ir.width; ch = ir.width / nA; } else { ch = ir.height; cw = ir.height * nA; }
    const pos = getComputedStyle(img).objectPosition.split(' ');
    const pxc = parseFloat(pos[0]) / 100, pyc = parseFloat(pos[1]) / 100;
    const cl = ir.x + (ir.width - cw) * pxc, ct = ir.y + (ir.height - ch) * pyc;
    out.content = { x: +cl.toFixed(1), y: +ct.toFixed(1), w: +cw.toFixed(1), h: +ch.toFixed(1),
      right: +(cl + cw).toFixed(1), bottom: +(ct + ch).toFixed(1),
      cardClippedLeft: +(ar.x - cl).toFixed(1), cardClippedTop: +(ar.y - ct).toFixed(1),
      gapRightInArt: +(ar.right - (cl + cw)).toFixed(1) };
  }
  return out;
};

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: +(process.env.VW || 1280), height: +(process.env.VH || 900) } });
  const page = await ctx.newPage();
  await page.route('**/*.mp4', r => r.abort());
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(6000);
  await page.evaluate(() => { document.body.classList.remove('cover-mode'); });
  await page.waitForTimeout(2500);
  const info = await page.evaluate(js);
  console.log(JSON.stringify(info, null, 1));
  if (SHOT) await page.screenshot({ path: '/workspace/_prod_' + SHOT + '.png', clip: { x: 300, y: 60, width: 700, height: 500 } });
  await browser.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
