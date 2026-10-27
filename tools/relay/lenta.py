#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lenta.py — adresų lenta (atsarginis prisijungimo kelias).

Lenta yra failas `relay-adresas.txt` nuolatinėje šakoje `cline/lenta`.
Kodėl nuolatinė šaka: kiekviena sesija turi naują darbo šaką, o `cline/lenta`
niekada nesikeičia — todėl adresas, kurį skaito M kompiuterio paleidėjas,
visada yra tas pats kelias:

    https://raw.githubusercontent.com/mindaugasbusiness-hub/novashop/cline/lenta/relay-adresas.txt

SAUGUMAS (svarbu, perskaityk):
    Repo `novashop` yra VIEŠAS. Kas perskaito lentą, tas gauna pilną prieigą
    prie M kompiuterio, kol gyva sesija (agent.ps1 turi raktą viduje).
    Todėl numatytuoju režimu skelbimas BLOKUOJAMAS, kol repo viešas.
    Leidžiama tik su `--force` arba kai repo padarytas privatus.

Naudojimas:
    python3 tools/relay/lenta.py busena          # ką lenta sako dabar
    python3 tools/relay/lenta.py skelbti         # įrašyti /tmp/adresas.txt į lentą
    python3 tools/relay/lenta.py isvalyti        # lenta: "nėra aktyvaus adreso"
    python3 tools/relay/lenta.py skelbti --force # apeiti viešumo patikrinimą
"""

import base64
import datetime
import json
import os
import subprocess
import sys

REPO = os.environ.get('LENTA_REPO', 'mindaugasbusiness-hub/novashop')
SAKA = os.environ.get('LENTA_SAKA', 'cline/lenta')
FAILAS = 'relay-adresas.txt'
ADRESO_FAILAS = os.environ.get('RELAY_ADDRESS_FILE', '/tmp/adresas.txt')
TUSCIA = ('# CLINE adresu lenta\n'
          '# Siuo metu aktyvaus adreso nera (sesija nepaleista arba jau baigta).\n'
          '# Paleidejas tada paprasys iklijuoti komanda ranka.\n')


def gh(args, input_json=None):
    cmd = ['gh', 'api'] + args
    r = subprocess.run(cmd, capture_output=True, text=True, input=input_json)
    if r.returncode != 0:
        raise SystemExit('gh klaida (%d): %s' % (r.returncode, (r.stderr or r.stdout).strip()))
    return r.stdout


def repo_viesas():
    out = gh(['repos/' + REPO, '--jq', '.private'])
    return out.strip() == 'false'


def saka_yra():
    r = subprocess.run(['gh', 'api', 'repos/%s/branches/%s' % (REPO, SAKA)],
                       capture_output=True, text=True)
    return r.returncode == 0


def sukurk_saka():
    out = gh(['repos/' + REPO, '--jq', '.default_branch'])
    pagrindine = out.strip()
    sha = gh(['repos/%s/git/ref/heads/%s' % (REPO, pagrindine), '--jq', '.object.sha']).strip()
    gh(['--method', 'POST', 'repos/%s/git/refs' % REPO,
        '-f', 'ref=refs/heads/' + SAKA, '-f', 'sha=' + sha])
    print('Sukurta nuolatinė šaka %s (nuo %s)' % (SAKA, pagrindine))


def dabartinis():
    """Grąžina (turinys, sha) arba (None, None)."""
    r = subprocess.run(['gh', 'api', 'repos/%s/contents/%s?ref=%s' % (REPO, FAILAS, SAKA)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, None
    d = json.loads(r.stdout)
    turinys = base64.b64decode(d.get('content', '')).decode('utf-8', 'replace')
    return turinys, d.get('sha')


def irasyk(turinys, zinute):
    if not saka_yra():
        sukurk_saka()
    _senas, sha = dabartinis()
    body = {
        'message': zinute,
        'content': base64.b64encode(turinys.encode('utf-8')).decode('ascii'),
        'branch': SAKA,
    }
    if sha:
        body['sha'] = sha
    gh(['--method', 'PUT', 'repos/%s/contents/%s' % (REPO, FAILAS),
        '-H', 'Accept: application/vnd.github+json',
        '--input', '-'], input_json=json.dumps(body))
    print('Lenta atnaujinta: %s (%s)' % (FAILAS, SAKA))


def adresas_is_failo():
    if not os.path.isfile(ADRESO_FAILAS):
        return None
    turinys = open(ADRESO_FAILAS, encoding='utf-8').read().strip()
    for eil in turinys.splitlines():
        eil = eil.strip()
        if eil.startswith('https://'):
            eil = eil.rstrip('/')
            if not eil.endswith('/agent.ps1'):
                eil += '/agent.ps1'
            return eil
    return None


def main(argv):
    veiksmas = argv[1] if len(argv) > 1 else 'busena'
    force = '--force' in argv

    if veiksmas == 'busena':
        turinys, _sha = dabartinis()
        if turinys is None:
            print('Lentos dar nėra (šaka %s arba failas nerastas).' % SAKA)
            return 1
        print(turinys.strip())
        return 0

    if veiksmas == 'isvalyti':
        irasyk(TUSCIA, 'Lenta: nera aktyvaus adreso (sesija baigta)')
        return 0

    if veiksmas == 'skelbti':
        adresas = adresas_is_failo()
        if not adresas:
            print('Nėra adreso: įrašyk jį į %s (arba paleisk start.sh)' % ADRESO_FAILAS)
            return 2
        if repo_viesas() and not force:
            print('')
            print('STOP: repo %s yra VIEŠAS.' % REPO)
            print('Jei paskelbsiu šį adresą, kas perskaitys lentą galės vykdyti')
            print('PowerShell komandas M kompiuteryje, kol gyva sesija.')
            print('')
            print('Ką daryti (vienas iš trijų):')
            print('  1) Padaryti repo privatų (GitHub -> Settings -> Danger Zone -> Change visibility).')
            print('  2) Naudoti rankinį kelią (įklijuoti eilutę ir Ctrl+C) - tada nieko nereikia skelbti.')
            print('  3) Jei riziką prisiimi sąmoningai: skelbti --force')
            print('')
            return 3
        turinys = ('# CLINE adresu lenta (atsarginis kelias)\n'
                   '# Gyva tik tol, kol veikia sesija. Atnaujinta: %s\n' % datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC') + adresas + '\n')
        irasyk(turinys, 'Lenta: naujas adresas (%s)' % adresas.split('/')[2])
        print('M kompiuterio paleidėjas šį adresą ras per:')
        print('  https://raw.githubusercontent.com/%s/%s/%s' % (REPO, SAKA, FAILAS))
        return 0

    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))