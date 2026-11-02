#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pc.py — siunčia komandas į M kompiuterį per relay ir grąžina rezultatą.

Naudojimas:
  python3 tools/relay/pc.py status
  python3 tools/relay/pc.py cmd "Get-Date"
  python3 tools/relay/pc.py cmd --lines 60 "Get-ChildItem 'C:\\Users\\M\\Desktop' -Force"

SVARBU dėl konteksto: visas komandos išvedimas VISADA įrašomas į failą,
o į ekraną spausdinama tik pradžia (--lines, numatyta 40).
Taip nešvaistomas Cline kontekstas ir negaunama raudonos klaidos.
Jei nori visko ekrane — naudok --full (atsargiai!).
"""

import argparse
import json
import os
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

DEFAULT_SAVE = '/tmp/pc-out'


def base_url():
    v = os.environ.get('RELAY_BASE')
    if v:
        return v.rstrip('/')
    p = '/tmp/relay.base'
    if os.path.isfile(p):
        return open(p).read().strip().rstrip('/')
    raise SystemExit('Nėra RELAY_BASE — įrašyk adresą į /tmp/relay.base')


def relay_key():
    v = os.environ.get('RELAY_KEY')
    if v:
        return v
    p = os.environ.get('RELAY_TOKEN_FILE', '/tmp/relay.token')
    if os.path.isfile(p):
        return open(p).read().strip()
    raise SystemExit('Nėra rakto — įrašyk tokeną į /tmp/relay.token')


def req(path, method='GET', body=None, timeout=90):
    data = body.encode('utf-8') if isinstance(body, str) else body
    r = Request(base_url() + path, data=data, method=method,
                headers={'X-Key': relay_key()})
    with urlopen(r, timeout=timeout) as resp:
        return resp.read().decode('utf-8', 'replace')


def send(text):
    return json.loads(req('/cmd', 'POST', text))


def out_of(i):
    try:
        return req('/out?id=%d' % i, timeout=30)
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def wait_out(i, timeout=240):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v = out_of(i)
        if v:
            return v
        time.sleep(1)
    return None


def save_and_show(text, path, lines, full):
    try:
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
    except OSError as exc:
        print('NEPAVYKO įrašyti %s: %s' % (path, exc))
        path = None
    rows = text.splitlines()
    print('--- išvestis: %d eil., %d simbolių%s' % (
        len(rows), len(text), (' | įrašyta: ' + path) if path else ''))
    if full:
        print(text)
    else:
        for line in rows[:lines]:
            print(line)
        if len(rows) > lines:
            print('... (dar %d eil. — viskas faile %s)' % (len(rows) - lines, path))


def main(argv=None):
    ap = argparse.ArgumentParser(description='Komandos į M kompiuterį per relay.')
    sub = ap.add_subparsers(dest='cmd_name')

    s = sub.add_parser('status', help='kas prisijungę, kiek komandų')
    s.add_argument('--full', action='store_true')

    c = sub.add_parser('cmd', help='įvykdyti komandą ir grąžinti rezultatą')
    c.add_argument('text', nargs='*', help='PowerShell komanda')
    c.add_argument('--file', default=None, help='imti komandą iš failo (patogiau ilgiems skriptams)')
    c.add_argument('--lines', type=int, default=40, help='kiek eilučių rodyti (numatyta 40)')
    c.add_argument('--save', default=None, help='kur įrašyti visą išvestį')
    c.add_argument('--timeout', type=int, default=240, help='kiek sekundžių laukti')
    c.add_argument('--full', action='store_true', help='rodyti VISĄ išvestį (atsargiai)')

    l = sub.add_parser('cmds', help='visos komandos eilėje')

    args = ap.parse_args(argv)
    if not args.cmd_name:
        ap.print_help()
        return 2

    if args.cmd_name == 'status':
        print(req('/status'))
        return 0
    if args.cmd_name == 'cmds':
        print(req('/cmds'))
        return 0

    if args.file:
        text = open(args.file, encoding='utf-8').read()
    else:
        text = ' '.join(args.text)
    if not text.strip():
        print('Nėra komandos (duok tekstą arba --file)')
        return 2
    res = send(text)
    i = res['id']
    print('--- įdėta į eilę id=%d, laukiu vykdymo...' % i)
    raw = wait_out(i, args.timeout)
    if raw is None:
        print('NEGAVAU atsakymo per %d s (ar langas "CLINE RYSYS" atidarytas?)' % args.timeout)
        return 1
    import base64
    try:
        out = base64.b64decode(raw).decode('utf-8', 'replace')
    except Exception:
        out = raw
    path = args.save or os.path.join(DEFAULT_SAVE, 'out-%d.txt' % i)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    save_and_show(out, path, args.lines, args.full)
    return 0


if __name__ == '__main__':
    sys.exit(main())
