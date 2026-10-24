// Matavimas: .brand-name ir .brand-evening pozicijos + naturali evening pozicija (be transform)
const { chromium } = require('/workspace/node_modules/playwright');
const URL = 'https://penktadienioaukcionas.lt/';
const VPS = [1280, 1024, 899, 720, 480];
(async () => {
  const browser = await chromium.launch();
  for (const w of VPS) {
    const page = await (await browser.newContext({ viewport: { width: w, height: 900 } })).newPage();
    await page.route('**/*.mp4', r => r.abort());
    await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    const d = await page.evaluate(() => {
      const R = e => { const r = e.getBoundingClientRect();
        return { l: +r.left.toFixed(1), r: +r.right.toFixed(1), t: +r.top.toFixed(1), b: +r.bottom.toFixed(1), w: +r.width.toFixed(1) }; };
      const name = document.querySelector('.brand-name');
      const eve = document.querySelector('.brand-evening');
      const badge = document.querySelector('.brand-top .radio-badge');
      const brand = document.querySelector('.brand');
      const rn = R(name), re = R(eve), rb = R(badge), rbrand = R(brand);
      const cs = getComputedStyle(eve);
      const curT = cs.transform;
      // naturali pozicija: nuimam transform
      const save = eve.style.transform;
      eve.style.transform = 'none';
      const nat = R(eve);
      eve.style.transform = save;
      const ncs = getComputedStyle(name);
      const saveN = name.style.transform;
      name.style.transform = 'none';
      const natName = R(name);
      name.style.transform = saveN;
      return { cover: document.body.className, curT, eveW: re.w,
        name: rn, eve: re, badge: rb, brand: rbrand, eveNat: nat, nameNat: natName,
        nameCenter: +((rn.l + rn.r) / 2).toFixed(1), eveCenter: +((re.l + re.r) / 2).toFixed(1),
        natNameCenter: +((natName.l + natName.r) / 2).toFixed(1), natEveCenter: +((nat.l + nat.r) / 2).toFixed(1),
        pxPerPct: +(re.w / 100).toFixed(3) };
    });
    const dLeft = +(d.eveCenter - d.nameCenter).toFixed(1);
    const dRight = +(d.badge.l - d.eve.r).toFixed(1);
    console.log('=== vw=' + w + ' | body="' + d.cover + '" | transform=' + d.curT);
    console.log('    name  [' + d.name.l + '..' + d.name.r + '] c=' + d.nameCenter + ' (nat c=' + d.natNameCenter + ')');
    console.log('    eve   [' + d.eve.l + '..' + d.eve.r + '] c=' + d.eveCenter + ' (nat c=' + d.natEveCenter + ', w=' + d.eveW + ')');
    console.log('    badge [' + d.badge.l + '..' + d.badge.r + '] | brand [' + d.brand.l + '..' + d.brand.r + ']');
    console.log('    eve_c - name_c = ' + dLeft + ' px | tarpas iki badge = ' + dRight + ' px | 1% = ' + d.pxPerPct + 'px');
    await page.close();
  }
  await browser.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
