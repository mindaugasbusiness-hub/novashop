import json, os, random, string, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.environ.get('RELAY_TOKEN_FILE', '/tmp/relay.token')
if os.path.exists(TOKEN_FILE):
    TOKEN = open(TOKEN_FILE).read().strip()
else:
    TOKEN = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(28))
    try:
        open(TOKEN_FILE, 'w').write(TOKEN)
    except Exception:
        pass

LOCK = threading.Lock()
CMDS = {}
OUTS = {}
CLAIMS = {}
CLIENTS = {}
SEQ = [20000]
TEMPLATE = open(os.path.join(HERE, 'agent-template.ps1'), encoding='utf-8').read()
CLAIM_TTL = 600


class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype='text/plain; charset=utf-8'):
        data = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except Exception:
            pass

    def _body(self):
        n = int(self.headers.get('Content-Length') or 0)
        return self.rfile.read(n).decode('utf-8') if n else ''

    def _auth(self):
        return self.headers.get('X-Key') == TOKEN

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == '/':
            return self._send(200, 'relay ok')
        if u.path == '/agent.ps1':
            host = self.headers.get('Host', '')
            txt = TEMPLATE.replace('__BASE__', 'https://' + host).replace('__KEY__', TOKEN)
            return self._send(200, txt, 'text/plain; charset=utf-8')
        if u.path == '/health':
            return self._send(200, 'ok')
        if not self._auth():
            return self._send(403, 'forbidden')
        if u.path == '/next':
            since = int(q.get('since', ['0'])[0])
            cid = q.get('cid', [''])[0] or 'anonymous'
            deadline = time.time() + 15
            while time.time() < deadline:
                now = time.time()
                with LOCK:
                    CLIENTS[cid] = now
                    ready = []
                    for i in sorted(CMDS):
                        if i <= since:
                            continue
                        c = CLAIMS.get(i)
                        if c is None or c[0] == cid or (now - c[1]) > CLAIM_TTL:
                            ready.append(i)
                if ready:
                    i = ready[0]
                    with LOCK:
                        CLAIMS[i] = (cid, now)
                        cmd = CMDS[i]
                    return self._send(200, json.dumps({'id': i, 'cmd': cmd}), 'application/json')
                time.sleep(0.25)
            return self._send(200, '{}', 'application/json')
        if u.path == '/out':
            i = int(q.get('id', ['0'])[0])
            with LOCK:
                v = OUTS.get(i)
            if v is None:
                return self._send(404, 'pending')
            return self._send(200, v)
        if u.path == '/cmds':
            with LOCK:
                out = {str(k): v for k, v in CMDS.items()}
            return self._send(200, json.dumps(out), 'application/json')
        if u.path == '/status':
            now = time.time()
            with LOCK:
                cl = {k: round(now - v, 1) for k, v in CLIENTS.items()}
            return self._send(200, json.dumps({'clients': cl, 'cmds': len(CMDS), 'outs': len(OUTS)}), 'application/json')
        return self._send(404, 'not found')

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if not self._auth():
            return self._send(403, 'forbidden')
        body = self._body()
        if u.path == '/cmd':
            with LOCK:
                SEQ[0] += 1
                i = SEQ[0]
                CMDS[i] = body
            return self._send(200, json.dumps({'id': i}), 'application/json')
        if u.path == '/out':
            i = int(q.get('id', ['0'])[0])
            with LOCK:
                OUTS[i] = body
            return self._send(200, 'ok')
        return self._send(404, 'not found')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8798'))
    srv = ThreadingHTTPServer(('127.0.0.1', port), H)
    srv.daemon_threads = True
    print('relay on', port, 'token', TOKEN, flush=True)
    srv.serve_forever()
