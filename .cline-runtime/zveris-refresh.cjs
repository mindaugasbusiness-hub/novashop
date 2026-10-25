const http = require('http');

function targets() {
  return new Promise((resolve, reject) => {
    const req = http.get('http://127.0.0.1:9222/json', res => {
      let data = '';
      res.on('data', chunk => { data += chunk; });
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch (error) { reject(error); }
      });
    });
    req.on('error', reject);
    req.setTimeout(5000, () => req.destroy(new Error('CDP timeout')));
  });
}

function reload(target) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    const finish = (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try { ws.close(); } catch (_) {}
      error ? reject(error) : resolve();
    };
    const timer = setTimeout(() => finish(new Error('reload timeout')), 8000);
    ws.onopen = () => ws.send(JSON.stringify({ id: 1, method: 'Page.reload', params: { ignoreCache: true } }));
    ws.onmessage = event => {
      try {
        const message = JSON.parse(event.data);
        if (message.id === 1) finish(null);
      } catch (_) {}
    };
    ws.onerror = () => finish(new Error('WebSocket error'));
  });
}

(async () => {
  const all = await targets();
  const pages = all.filter(t => t.type === 'page' && /^https?:\/\/(127\.0\.0\.1|localhost):8091(?:\/|$)/.test(t.url || ''));
  if (!pages.length) {
    console.log('Zveris tabo atidarytoje agento narsykleje nera; F5 nepriverstinis.');
    return;
  }
  for (const page of pages) {
    await reload(page);
    console.log('F5 atliktas: ' + page.url);
  }
})().catch(error => {
  console.error('F5 KLAIDA: ' + error.message);
  process.exitCode = 1;
});
