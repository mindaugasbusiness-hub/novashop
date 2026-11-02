#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test-relay.py — savitikra: ar relay + pc.py + agent.ps1 grandis tikrai veikia.

Ką daro:
  1. paleidžia relay.py atskirame procese (atsitiktinis portas),
  2. patikrina /health ir /agent.ps1 (ar tokenas ir adresas teisingai įrašomi),
  3. simuliuoja Windows agentą: long-pollina /next ir siunčia atsakymą į /out,
  4. per pc.py nusiunčia komandas ir patikrina, kad atsakymas grįžta,
  5. patikrina, kad be rakto (X-Key) relay atsako 403.

Naudojimas:
    python3 tools/relay/test-relay.py          # rodo tik rezultatą
    python3 tools/relay/test-relay.py -v       # rodo ir pc.py išvestį

NIEKO neliečia nei /tmp/relay.token, nei /tmp/relay.base — naudoja savo laikinus failus.
"""

import argparse
import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

HERE = os.path.dirname(os.path.abspath(__file__))
PASS, FAIL = [], []


def check(name, condition, detail=''):
    if condition:
        PASS.append(name)
        print('  [OK]   %s' % name)
    else:
        FAIL.append(name)
        print('  [FAIL] %s %s' % (name, detail))


def http(url, key=None, method='GET', body=None, timeout=30):
    data = body.encode('utf-8') if isinstance(body, str) else body
    headers = {'X-Key': key} if key else {}
    req = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode('utf-8', 'replace')
    except HTTPError as exc:
        return exc.code, exc.read().decode('utf-8', 'replace')


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


class SimAgent(threading.Thread):
    """Simuliuoja agent.ps1: ima komandas ir siunčia atsakymus."""

    def __init__(self, base, key, cid='selftest'):
        super().__init__(daemon=True)
        self.base = base
        self.key = key
        self.cid = cid
        self.since = 0
        self.seen = []
        self.stop = threading.Event()

    def run(self):
        while not self.stop.is_set():
            try:
                code, body = http('%s/next?since=%d&cid=%s' % (self.base, self.since, self.cid),
                                  self.key, timeout=30)
                if code != 200:
                    time.sleep(0.3)
                    continue
                msg = json.loads(body)
                if not msg.get('id'):
                    continue
                self.since = int(msg['id'])
                cmd = str(msg.get('cmd', ''))
                self.seen.append(cmd)
                out = '[sim] %s -> OK (%d simb.)' % (cmd, len(cmd))
                b64 = base64.b64encode(out.encode('utf-8')).decode('ascii')
                http('%s/out?id=%d' % (self.base, self.since), self.key, 'POST', b64)
            except Exception:
                time.sleep(0.3)

    def halt(self):
        self.stop.set()


def main(argv=None):
    ap = argparse.ArgumentParser(description='Relay grandinės savitikra.')
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args(argv)

    tmp = tempfile.mkdtemp(prefix='relay-test-')
    token = 'selftest-token-0123456789'
    port = free_port()
    base = 'http://127.0.0.1:%d' % port
    env = dict(os.environ)
    env['PORT'] = str(port)
    env['RELAY_TOKEN_FILE'] = os.path.join(tmp, 'token')
    with open(env['RELAY_TOKEN_FILE'], 'w') as fh:
        fh.write(token)

    print('Relay savitikra (portas %d, laikini failai %s)' % (port, tmp))
    proc = subprocess.Popen([sys.executable, os.path.join(HERE, 'relay.py')],
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, cwd=HERE)

    try:
        up = False
        for _ in range(40):
            try:
                code, _body = http(base + '/health', timeout=2)
                if code == 200:
                    up = True
                    break
            except Exception:
                time.sleep(0.25)
        check('relay.py pakilo ir /health atsako 200', up)
        if not up:
            return 1

        code, agent = http(base + '/agent.ps1')
        check('/agent.ps1 atiduodamas (200)', code == 200, 'gavau %s' % code)
        check('/agent.ps1 turi įrašytą tokeną', token in agent)
        check('/agent.ps1 turi savo adresą (ne __BASE__)',
              '__BASE__' not in agent and ('127.0.0.1:%d' % port) in agent)
        check('/agent.ps1 neturi likusių __KEY__', '__KEY__' not in agent)

        code, _ = http(base + '/next?since=0')
        check('be X-Key relay atsako 403 (saugumas)', code == 403, 'gavau %s' % code)

        agent_thr = SimAgent(base, token)
        agent_thr.start()
        time.sleep(0.5)
        code, status = http(base + '/status', token)
        clients = json.loads(status).get('clients', {}) if code == 200 else {}
        check('agentas matomas /status (prisijungęs)', 'selftest' in clients, 'clients=%s' % clients)

        env2 = dict(env)
        env2['RELAY_BASE'] = base
        env2['RELAY_KEY'] = token
        save = os.path.join(tmp, 'out.txt')
        r = subprocess.run([sys.executable, os.path.join(HERE, 'pc.py'), 'cmd',
                            'Get-Date', '--save', save, '--timeout', '30'],
                           env=env2, capture_output=True, text=True, timeout=120)
        out = (r.stdout or '') + (r.stderr or '')
        if args.verbose:
            print(out)
        check('pc.py grąžino atsakymą iš agento', '[sim] Get-Date -> OK' in out, out.strip()[:200])
        check('pc.py įrašė išvestį į failą', os.path.isfile(save) and os.path.getsize(save) > 0)

        r2 = subprocess.run([sys.executable, os.path.join(HERE, 'pc.py'), 'cmd',
                             'Get-ChildItem C:\\Users\\M', '--save', save + '2', '--timeout', '30'],
                            env=env2, capture_output=True, text=True, timeout=120)
        check('antra komanda taip pat įvykdyta',
              '[sim] Get-ChildItem' in ((r2.stdout or '') + (r2.stderr or '')))

        r3 = subprocess.run([sys.executable, os.path.join(HERE, 'pc.py'), 'status'],
                            env=env2, capture_output=True, text=True, timeout=60)
        check('pc.py status rodo prisijungusį agentą', 'selftest' in (r3.stdout or ''))

        agent_thr.halt()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)

    print('\nRezultatas: %d OK, %d FAIL' % (len(PASS), len(FAIL)))
    if FAIL:
        print('Nepavyko: ' + ', '.join(FAIL))
        return 1
    print('Grandis relay.py -> agent.ps1 -> pc.py veikia.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
