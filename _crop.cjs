// Istrina PNG regiona ir padidina (be PIL) per chromium canvas
const { chromium } = require('/workspace/node_modules/playwright');
const [src, out, x, y, w, h, scale] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const p = await b.newPage();
  await p.goto('file:///workspace/_crop.html');
  const dataUrl = await p.evaluate(async (a) => {
    const img = new Image();
    img.src = 'file://' + a.src;
    await img.decode();
    const c = document.createElement('canvas');
    c.width = Math.round(a.w * a.scale); c.height = Math.round(a.h * a.scale);
    const ctx = c.getContext('2d');
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(img, a.x, a.y, a.w, a.h, 0, 0, c.width, c.height);
    return c.toDataURL('image/png');
  }, { src, x: +x, y: +y, w: +w, h: +h, scale: +scale });
  require('fs').writeFileSync(out, Buffer.from(dataUrl.split(',')[1], 'base64'));
  console.log('OK', out);
  await b.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
