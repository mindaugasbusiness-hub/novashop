// Pries/po palyginimas TAM PACIAM loto foto: sena vs nauja .art img CSS
const { chromium } = require('/workspace/node_modules/playwright');
const URL = process.env.PROBE_URL || 'https://penktadienioaukcionas.lt/';

const OLD = ".art img{flex:1 1 0;min-width:0;width:100%;max-height:340px;object-fit:contain;object-position:20% center;display:block;margin:0;padding:0;border:0;}";
const NEW = ".art img{flex:0 0 75%;min-width:0;width:75%;max-height:255px;object-fit:contain;object-position:0% center;display:block;margin:0;padding:0;border:0;}";

const measure = () => {
  const R = el => { if (!el) return null; const r = el.getBoundingClientRect();
    return { x: +r.x.toFixed(1), y: +r.y.toFixed(1), w: +r.width.toFixed(1), h: +r.height.toFixed(1),
             right: +r.right.toFixed(1), bottom: +r.bottom.toFixed(1) }; };
  const ov = (a, b) => (a && b) ? +(Math.max(0, Math.min(a.right, b.right) - Math.max(a.x, b.x)) *
                                     Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.y, b.y))).toFixed(1) : null;
  const img = document.getElementById('artPhoto'), art = document.getElementById('artWrap');
  if (!img || !art) return { klaida: 'nera artPhoto/artWrap' };
  const ar = art.getBoundingClientRect(), ir = img.getBoundingClientRect();
  const cs = getComputedStyle(img);
  const nA = img.naturalWidth / img.naturalHeight, boxA = ir.width / ir.height;
  let cw, ch;
  if (nA > boxA) { cw = ir.width; ch = ir.width / nA; } else { ch = ir.height; cw = ir.height * nA; }
  const pos = cs.objectPosition.split(' ');
  const cl = ir.x + (ir.width - cw) * (parseFloat(pos[0]) / 100);
  const ct = ir.y + (ir.height - ch) * (parseFloat(pos[1]) / 100);
  const content = { x: +cl.toFixed(1), y: +ct.toFixed(1), w: +cw.toFixed(1), h: +ch.toFixed(1),
    right: +(cl + cw).toFixed(1), bottom: +(ct + ch).toFixed(1) };
  const title = R(document.getElementById('itemTitle')), desc = R(document.querySelector('.desc-box'));
  const bid = R(document.getElementById('bidBtn')), price = R(document.getElementById('priceNum'));
  return {
    foto_natural: img.naturalWidth + 'x' + img.naturalHeight, css: { maxHeight: cs.maxHeight, flex: cs.flex, objectPosition: cs.objectPosition },
    artWrap: R(art), imgBox: R(img), content,
    tarpasKairej: +(cl - ar.x).toFixed(1), tarpasDesinej: +(ar.right - (cl + cw)).toFixed(1),
    iskirptaKairej: +(ar.x - cl).toFixed(1), iskirptaDesinej: +((cl + cw) - ar.right).toFixed(1),
    ovSuTitle: ov(content, title), ovSuDesc: ov(content, desc), ovSuKaina: ov(content, price), ovSuMygtuku: ov(content, bid),
    panelHeight: +ar.height.toFixed(1), kortelesAukstis: R(document.getElementById('mainPanel')).h,
    cardBottom: R(document.getElementById('mainPanel')).bottom, docH: document.documentElement.scrollHeight
  };
};

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  await page.route('**/*.mp4', r => r.abort());
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(6000);
  await page.evaluate(() => document.body.classList.remove('cover-mode'));
  await page.waitForTimeout(2000);

  const foto = await page.evaluate(() => { const i = document.getElementById('artPhoto'); return i ? i.currentSrc.split('/').pop() : null; });
  console.log('LOTO FOTO:', foto);

  const tag = await page.addStyleTag({ content: OLD });
  await page.waitForTimeout(400);
  const before = await page.evaluate(measure);
  console.log('=== PRIES (sena CSS) ===\n' + JSON.stringify(before, null, 1));
  await page.screenshot({ path: '/workspace/_prod_pries.png', clip: { x: 300, y: 60, width: 700, height: 460 } });

  await page.evaluate(() => { const t = [...document.querySelectorAll('style')].pop(); t.remove(); });
  await page.waitForTimeout(400);
  const after = await page.evaluate(measure);
  console.log('=== PO (nauja CSS) ===\n' + JSON.stringify(after, null, 1));
  await page.screenshot({ path: '/workspace/_prod_po.png', clip: { x: 300, y: 60, width: 700, height: 460 } });

  const pc = (a, b) => (b ? +(100 * a / b).toFixed(1) : null);
  console.log('=== SANTRAUKA ===');
  console.log('foto plotis: ' + before.content.w + ' -> ' + after.content.w + ' (' + pc(after.content.w, before.content.w) + '% )');
  console.log('foto aukstis: ' + before.content.h + ' -> ' + after.content.h + ' (' + pc(after.content.h, before.content.h) + '% )');
  console.log('foto x: ' + before.content.x + ' -> ' + after.content.x + ' (pajudejo ' + (after.content.x - before.content.x).toFixed(1) + ' px)');
  console.log('tarpas kairej: ' + before.tarpasKairej + ' -> ' + after.tarpasKairej + ' px');
  console.log('persidengimas su title/desc/kaina/mygtuku (po): ' + after.ovSuTitle + '/' + after.ovSuDesc + '/' + after.ovSuKaina + '/' + after.ovSuMygtuku);
  console.log('iskirpta kairej/desinej (po): ' + after.iskirptaKairej + '/' + after.iskirptaDesinej);
  console.log('paneles auksstis: ' + before.panelHeight + ' -> ' + after.panelHeight + ' | kortele: ' + before.kortelesAukstis + ' -> ' + after.kortelesAukstis);
  await browser.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
