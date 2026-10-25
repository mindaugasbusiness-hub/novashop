#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PULTO TIKRINTUVAS (saugus kontekstui)
=====================================
Kodėl reikalingas: kai agentui sakai "peržiūrėk, netvarka yra čia http://127.0.0.1:8790/",
agentas įtraukia VISĄ puslapio HTML į pokalbį. Vienas toks žingsnis gali būti
20-50 tūkst. tokenų -> konteksto limitas -> raudona klaida ir sesija miršta.

Šis įrankis tą patį padaro SAUGIAI:
  - parsiunčia puslapį ir IŠSAUGO jį į failą (failas NEįtraukiamas į pokalbį)
  - į ekraną išveda tik TRUMPĄ ataskaitą (iki ~50 eilučių, ~400-700 tokenų)
  - suranda konkrečią "netvarką": pasikartojantys id, nerasti failai (404),
    inline onclick, tušti href, mojibake, ilgiausios eilutės ir t.t.

NIEKO NETRINA. Tik skaito tinklą ir įrašo 2 failus (raw HTML + ataskaita).

Paleidimas:
  python pulto-tikrintuvas.py
  python pulto-tikrintuvas.py --url http://127.0.0.1:8790/ --out-dir "C:\\Users\\M\\CLINE"
  python pulto-tikrintuvas.py --no-asset-check      (neprašinėti kiekvieno failo atskirai)
"""

import argparse
import os
import re
import sys
import time
from collections import Counter
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

TAG_RE = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)")
ID_RE = re.compile(r"""\bid\s*=\s*["']([^"']*)["']""")
ASSET_RE = re.compile(
    r"""<(?:link|script|img)\b[^>]*?\b(?:href|src)\s*=\s*["']([^"']+)["']""", re.I)
INLINE_EV_RE = re.compile(
    r"""\son(?:click|change|input|submit|load|error|mouseover|mouseout|"""
    r"""keyup|keydown|blur|focus|dblclick)\s*=""", re.I)
STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
BUTTON_NO_TYPE_RE = re.compile(r"<button\b(?![^>]*\btype\s*=)[^>]*>", re.I)
IMG_NO_ALT_RE = re.compile(r"<img\b(?![^>]*\balt\s*=)[^>]*>", re.I)

PLACEHOLDERS = ["TODO", "FIXME", "Lorem", "undefined", "NaN", 'href="#"', 'href=""', "XXX"]


def fetch(url, timeout=15):
    """Parsiunčia puslapį. Grąžina (status, bytes, ms, klaida)."""
    start = time.time()
    try:
        req = Request(url, headers={"User-Agent": "pulto-tikrintuvas/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            ms = int((time.time() - start) * 1000)
            return resp.getcode(), body, ms, None
    except HTTPError as exc:
        return exc.code, b"", int((time.time() - start) * 1000), str(exc)
    except URLError as exc:
        return None, b"", int((time.time() - start) * 1000), str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        return None, b"", int((time.time() - start) * 1000), str(exc)


def asset_exists(url, timeout=5):
    """Ar lokalus failas tikrai yra (HEAD, o jei nepalaiko - GET su Range)."""
    try:
        req = Request(url, method="HEAD",
                      headers={"User-Agent": "pulto-tikrintuvas/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.getcode() < 400
    except HTTPError as exc:
        if exc.code in (403, 405, 501):
            try:
                req = Request(url, headers={"Range": "bytes=0-0",
                                            "User-Agent": "pulto-tikrintuvas/1.0"})
                with urlopen(req, timeout=timeout) as resp:
                    return 200 <= resp.getcode() < 400
            except Exception:  # noqa: BLE001
                return False
        return False
    except Exception:  # noqa: BLE001
        return False


def top_long_lines(text, limit=10):
    rows = []
    for i, line in enumerate(text.splitlines(), 1):
        rows.append((len(line), i, line))
    rows.sort(reverse=True)
    return rows[:limit]


def build_report(html, url, body_len, status, ms, raw_path, do_assets, asset_limit=25):
    text = html
    lines = text.splitlines()
    out = []

    out.append("=== PULTO TIKRINTUVAS ===")
    out.append("URL        : " + url)
    if status is None:
        out.append("Busena     : NEPASIEKTA - pultas nepaleistas arba kitas adresas")
    else:
        out.append("Busena     : HTTP {0}, {1} B ({2:.1f} KB), {3} eil., {4} ms".format(
            status, human(body_len), body_len / 1024.0, len(lines), ms))
    if raw_path:
        out.append("Irasyta    : " + raw_path)
        out.append("             (SIO failo i pokalbi NEkelti - jis per didelis)")
    out.append("")

    title = TITLE_RE.search(text)
    h1 = len(re.findall(r"<h1\b", text, re.I))
    meta_enc = re.search(r"""<meta[^>]+charset\s*=\s*["']?([\w-]+)""", text, re.I)
    out.append("--- 1) PAGRINDINE INFO ---")
    out.append("Title      : " + (title.group(1).strip()[:80] if title else "(nera <title>)"))
    out.append("H1 kiekis  : {0}".format(h1))
    out.append("Encoding   : " + (meta_enc.group(1) if meta_enc else "(nenurodytas)"))
    out.append("")

    tags = Counter(t.lower() for t in TAG_RE.findall(text))
    interesting = ["div", "span", "button", "a", "input", "form", "table",
                   "script", "style", "iframe", "canvas", "svg"]
    parts = ["{0} {1}".format(t, tags.get(t, 0)) for t in interesting if tags.get(t, 0)]
    out.append("--- 2) ELEMENTU KIEKIAI ---")
    out.append(" | ".join(parts) if parts else "(nera elementu)")
    out.append("")

    out.append("--- 3) NETVARKA ---")

    ids = [i for i in ID_RE.findall(text) if i.strip()]
    dupes = sorted([kv for kv in Counter(ids).items() if kv[1] > 1],
                   key=lambda kv: kv[1], reverse=True)
    if dupes:
        out.append("[!] Pasikartojantys id ({0}): {1}".format(
            len(dupes), ", ".join('"{0}" x{1}'.format(k, v) for k, v in dupes[:6])))
    else:
        out.append("[OK] Pasikartojanciu id nera")

    assets = [a for a in ASSET_RE.findall(text)
              if not re.match(r"^(https?:|data:|#|mailto:|javascript:)", a, re.I)]
    assets = list(dict.fromkeys(assets))
    if assets and do_assets:
        broken = []
        for rel in assets[:asset_limit]:
            full = urljoin(url, rel)
            if not asset_exists(full):
                broken.append(rel)
        if broken:
            out.append("[!] Nerasti lokalus failai ({0} is {1}): {2}".format(
                len(broken), len(assets), " | ".join(broken[:8])))
        else:
            out.append("[OK] Visi lokalus failai rasti ({0} tikrinta)".format(
                min(len(assets), asset_limit)))
    elif assets:
        out.append("[i] Lokaliu failu nuorodos ({0}): {1}".format(
            len(assets), " | ".join(assets[:8])))

    inline = len(INLINE_EV_RE.findall(text))
    out.append(("[!] " if inline > 5 else "[i] ") +
               "inline onclick/onchange ir pan.: {0}".format(inline))

    btns = len(BUTTON_NO_TYPE_RE.findall(text))
    if btns:
        out.append('[!] <button> be type="button": {0}'.format(btns))
    imgs = len(IMG_NO_ALT_RE.findall(text))
    if imgs:
        out.append("[!] <img> be alt: {0}".format(imgs))

    found_ph = [(p, text.count(p)) for p in PLACEHOLDERS if text.count(p)]
    if found_ph:
        out.append("[!] Tusci placeholder'iai: " +
                   ", ".join("{0} x{1}".format(p, c) for p, c in found_ph))

    bad_chars = []
    if text.count("\u00c2"):
        bad_chars.append("'A su stogeliu' x{0}".format(text.count("\u00c2")))
    if text.count("\ufffd"):
        bad_chars.append("'?' rombas x{0}".format(text.count("\ufffd")))
    if bad_chars:
        out.append("[!] Mojibake pozymiai (blogas encoding): " + ", ".join(bad_chars))

    styles = STYLE_RE.findall(text)
    style_chars = sum(len(s) for s in styles)
    out.append("[i] <style> bloku: {0}, viso CSS simboliu: {1}".format(
        len(styles), human(style_chars)))

    balance = []
    for tag in ("div", "span", "form", "table", "button"):
        opens = len(re.findall(r"<" + tag + r"\b", text, re.I))
        closes = len(re.findall(r"</" + tag + r">", text, re.I))
        if opens != closes:
            balance.append("{0} {1}/{2}".format(tag, opens, closes))
    if balance:
        out.append("[!] Nesubalansuoti tag'ai (atidaryta/uzdyta): " + ", ".join(balance))
    else:
        out.append("[OK] Pagrindiniai tag'ai subalansuoti")
    out.append("")

    out.append("--- 4) ILGIAUSIOS EILUTES (kur slepiasi netvarka) ---")
    for length, num, line in top_long_lines(text, 8):
        preview = re.sub(r"\s+", " ", line.strip())[:90]
        out.append("eil. {0:>5} : {1:>7} simb. | {2}".format(num, human(length), preview))
    out.append("")

    out.append("--- 5) KA DARYTI ---")
    out.append("1. Pirmiausia taisyk viska, kas pazymeta [!].")
    out.append("2. Jei nori, kad agentas paziuretu - duok jam SIA ataskaita, o NE puslapi.")
    out.append("3. Detalems atidaryk raw HTML faila ir eik i eilute is 4 dalies.")
    return out


def human(n):
    return "{:,}".format(int(n)).replace(",", " ")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Saugus pulto puslapio tikrinimas (kontekstui nepavojingas).")
    ap.add_argument("--url", default="http://127.0.0.1:8790/")
    ap.add_argument("--out-dir", default=os.environ.get("CLINE_DIR", "."),
                    help="kur irasyti raw HTML ir ataskaita")
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--no-asset-check", action="store_true",
                    help="neprasineti kiekvieno lokalaus failo atskirai")
    ap.add_argument("--quiet", action="store_true",
                    help="nespausdinti i ekrana, tik irasyti ataskaita")
    args = ap.parse_args(argv)

    status, body, ms, err = fetch(args.url, args.timeout)
    raw_path = None
    report_path = os.path.join(args.out_dir, "pulto-ataskaita.txt")

    if status is not None:
        raw_path = os.path.join(args.out_dir, "pulto-raw.html")
        try:
            with open(raw_path, "wb") as fh:
                fh.write(body)
        except OSError as exc:
            raw_path = None
            err = "nepavyko irasyti raw HTML: " + str(exc)

    html = body.decode("utf-8", "replace")
    report = build_report(html, args.url, len(body), status, ms, raw_path,
                          not args.no_asset_check)

    try:
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report) + "\n")
    except OSError:
        report_path = None

    if not args.quiet:
        for line in report:
            print(line)
        print("")
        print("Ataskaita irasyta: " + (report_path or "(nepavyko)"))

    if status is None:
        if not args.quiet:
            print("Klaida: " + str(err))
            print("Patikrink: ar pultas paleistas?  netstat -ano | findstr 8790")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
