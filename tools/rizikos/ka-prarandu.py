#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KA PRARANDU? -- riziku patikra ir saugus taisymas
=================================================
Kodel reikalingas: pultas rodo "KA PRARANDU?" ataskaita, bet neparaso, KODEL
rizika yra ir ka ji realiai reiskia. Sis irankis ta padaro vienu paleidimu.

Tikrina tris dalykus -- tuos pacius, kuriuos rodo pulto ataskaita:
  1) workflow  -- ar n8n (:5678) gyvas IR ar galima gauti workflow sarasa
  2) kopija    -- ar VPS / vietine kopija ne senesne nei RIBOS valandu (numatyta 20 h)
  3) rag-testas-- ar yra RAG testas ir kokia jo kokybe (numatyta: < 70 % = zema)

SAUGUMAS (1 taisykle: NIEKO NETRINTI):
  - numatytuoju rezimu irankis TIK SKAITO (tinklas, failai, schtasks /query).
  - nieko netrina, neperraso, neperkelia. Vienintelis irasymas -- ataskaitos
    failas, ir tik jei nurodai --isvestis.
  - taisymas vykdomas TIK su --taisyti IR po patvirtinimo (arba su --tyliai).
  - slaptazodziai / raktai NIEKADA nespausdinami -- tik saltinio kelias.

Saugus kontekstui: i ekrana isvedama trumpa ataskaita (iki ~45 eiluciu),
pilnos detales rasomos i faila. Niekada nespausdinti viso saraso i pokalbi.

Paleidimas (Windows, PowerShell):
  python C:\\Users\\M\\CLINE\\tools\\rizikos\\ka-prarandu.py
  python ...\\ka-prarandu.py --isvestis C:\\Users\\M\\CLINE\\RIZIKOS_ATASKAITA.txt
  python ...\\ka-prarandu.py --taisyti            # paleisti n8n / kopija po patvirtinimo
  python ...\\ka-prarandu.py --taisyti --tyliai   # be klausimo (grafikui)

Isvesties kodai: 0 = riziku nera, 1 = rasta riziku, 2 = netiketa klaida (krastutinis atvejis).
"""

import argparse
import csv
import glob
import io
import json
import os
import re
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

# --- Numatytosios ribos ir keliai (viska galima perrasyti parametrais) ----
RIBOS_H = 20.0          # kopija senesne nei tiek valandu = PASENUSI (swiss.ps1 taisykle)
RAG_RIBA = 70.0         # RAG kokybe zemesne nei tiek % = ZEMA
N8N_URL = "http://127.0.0.1:5678"
CLINES_DIR = os.environ.get("CLINE_DIR") or r"C:\Users\M\CLINE"
N8N_ENV_FAILAI = [
    os.path.join(os.environ.get("N8N_ROOT", r"C:\Users\M\Desktop\Kumstis"), ".env"),
    os.path.join(CLINES_DIR, ".env"),
    os.path.join(CLINES_DIR, "n8n", ".env"),
]

def human(lentele):
    """Skaicius lietuvisku formatu: 1234.5 -> '1 234,5'."""
    try:
        tekstas = "{:,.1f}".format(float(lentele))
    except (TypeError, ValueError):
        return str(lentele)
    return tekstas.replace(",", " ").replace(".", ",")


def valandos_nuo(ts):
    return (time.time() - ts) / 3600.0


def skaityti_env_rakta(failai):
    """Iesko N8N_API_KEY .env failuose. Grazina (raktas, kelias) arba (None, None).
    Rakto reiksme NIEKADA nespausdinama."""
    for kelias in failai:
        if not kelias or not os.path.isfile(kelias):
            continue
        try:
            with io.open(kelias, "r", encoding="utf-8", errors="replace") as fh:
                for eilute in fh:
                    eilute = eilute.strip()
                    if eilute.startswith("#") or "=" not in eilute:
                        continue
                    raktas, reiksme = eilute.split("=", 1)
                    if raktas.strip().upper() in ("N8N_API_KEY", "N8N_API_TOKEN"):
                        reiksme = reiksme.strip().strip('"').strip("'")
                        if reiksme:
                            return reiksme, kelias
        except OSError:
            continue
    return None, None


def http_get(url, headers=None, timeout=8):
    """Grazina (statusas, tekstas, klaida). statusas None = nepavyko prisijungti."""
    uzklausa = Request(url, headers=headers or {"User-Agent": "ka-prarandu/1.0"})
    try:
        with urlopen(uzklausa, timeout=timeout) as ats:
            return ats.getcode(), ats.read().decode("utf-8", "replace"), None
    except HTTPError as exc:
        try:
            tekstas = exc.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            tekstas = ""
        return exc.code, tekstas, None
    except URLError as exc:
        return None, "", str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        return None, "", str(exc)


def prievadas_klauso(hostas, prievadas, timeout=3):
    try:
        with socket.create_connection((hostas, int(prievadas)), timeout=timeout):
            return True
    except Exception:  # noqa: BLE001
        return False


# =====================================================================
# 1) WORKFLOW -- ar n8n gyvas ir ar galima gauti workflow sarasa
# =====================================================================
def tikrinti_n8n(url, raktas, raktas_is, hostas="127.0.0.1", prievadas=5678, clines_dir=None):
    """Grazina zodyna su busena ir detales: ko truksta ir ka daryti."""
    clines_dir = clines_dir or CLINES_DIR
    rez = {
        "kategorija": "workflow", "prievadas": prievadas, "url": url,
        "gyvas": False, "api": False, "workflow": 0, "aktyvus": 0,
        "busena": "", "detales": [], "sprendimas": "",
    }

    if not prievadas_klauso(hostas, prievadas):
        rez["busena"] = "NEPALEISTAS"
        rez["detales"].append("Prievadas {0} neklauso -- n8n serveris neveikia.".format(prievadas))
        rez["sprendimas"] = "Paleisti: powershell -File {0}".format(
            os.path.join(clines_dir, "tools", "swiss.ps1"))
        return rez

    statusas, tekstas, klaida = http_get(url.rstrip("/") + "/healthz")
    rez["gyvas"] = (statusas == 200)
    rez["detales"].append("Sveikatos patikra /healthz: {0}".format(
        "200 OK" if statusas == 200 else (statusas if statusas else "nepasiekta ({0})".format(klaida))))
    if statusas != 200:
        rez["busena"] = "SERVERIS_NEGYVAS"
        rez["sprendimas"] = "Perkrauti: powershell -File {0}".format(
            os.path.join(clines_dir, "tools", "n8n", "restart-n8n.ps1"))
        return rez

    if not raktas:
        rez["busena"] = "NERA_RAKTO"
        rez["detales"].append("N8N_API_KEY nerastas nei .env, nei parametruose --")
        rez["detales"].append("del to pultas nemato workflow saraso.")
        rez["sprendimas"] = ("Irasyti i {0} eilute N8N_API_KEY=... "
                             "(n8n UI: Settings > n8n API > Create an API key)".format(N8N_ENV_FAILAI[0]))
        return rez

    rez["raktas_is"] = raktas_is
    rez["detales"].append("Raktas rastas: {0} (reiksme nespausdinama)".format(raktas_is))

    statusas, tekstas, klaida = http_get(
        url.rstrip("/") + "/api/v1/workflows?limit=100",
        headers={"X-N8N-API-KEY": raktas, "Accept": "application/json"},
    )
    if statusas is None:
        rez["busena"] = "API_NEPASIEKTA"
        rez["detales"].append("API uzklausa nepavyko: {0}".format(klaida))
        rez["sprendimas"] = "Patikrinti n8n procesa ir perkrauti: restart-n8n.ps1"
        return rez
    if statusas in (401, 403):
        rez["busena"] = "RAKTAS_NEGALIOJAS"
        rez["detales"].append("API atsake {0} -- raktas neteisingas arba panaikintas.".format(statusas))
        rez["sprendimas"] = "Sugeneruoti nauja API rakta n8n UI ir atnaujinti .env"
        return rez
    if statusas == 404:
        rez["busena"] = "API_ISJUNGTA"
        rez["detales"].append("API atsake 404 -- gal n8n paleistas su N8N_PUBLIC_API_DISABLED=true")
        rez["sprendimas"] = "Isimti N8N_PUBLIC_API_DISABLED is .env ir perkrauti n8n"
        return rez

    try:
        sarasas = (json.loads(tekstas) or {}).get("data") or []
    except ValueError:
        rez["busena"] = "API_ATSAKYMAS_NELOGISKAS"
        rez["detales"].append("API grazino ne JSON (galbut HTML prisijungimo puslapis).")
        rez["sprendimas"] = "Patikrinti, ar n8n nereikalauja owner prisijungimo"
        return rez

    rez["api"] = True
    rez["workflow"] = len(sarasas)
    rez["aktyvus"] = sum(1 for w in sarasas if w.get("active"))
    rez["neaktyvus"] = [w.get("name", "?") for w in sarasas if not w.get("active")]
    rez["busena"] = "GERAI" if statusas == 200 else "API_KLAIDA"
    rez["detales"].append("Workflow: {0} is viso, {1} aktyvus.".format(rez["workflow"], rez["aktyvus"]))
    if rez["neaktyvus"]:
        rez["detales"].append("Neaktyvus: " + ", ".join(rez["neaktyvus"][:5]) +
                              (" ..." if len(rez["neaktyvus"]) > 5 else ""))
        rez["sprendimas"] = "Ijunkyti reikalingus workflow n8n UI (Active perjungiklis)"
    return rez


# =====================================================================
# 2) KOPIJA -- ar VPS / vietine kopija nepasenusi
# =====================================================================
def naujausia_kopija(aplankas):
    """Grazina (pavadinimas, mtime) naujausios kopijos arba (None, None)."""
    if not os.path.isdir(aplankas):
        return None, None
    geriausia = (None, None)
    try:
        for pavadinimas in os.listdir(aplankas):
            kelias = os.path.join(aplankas, pavadinimas)
            if not os.path.isdir(kelias):
                continue
            try:
                mtime = os.path.getmtime(kelias)
            except OSError:
                continue
            if geriausia[1] is None or mtime > geriausia[1]:
                geriausia = (pavadinimas, mtime)
    except OSError:
        return None, None
    return geriausia


def tikrinti_kopijas(clines_dir, riba=RIBOS_H):
    rez = {"kategorija": "kopija", "riba": riba, "vietos": [],
           "busena": "", "detales": [], "sprendimas": ""}
    aplankai = [
        ("VPS kopija (BACKUPS_VPS)", os.path.join(clines_dir, "BACKUPS_VPS")),
        ("Vietine kopija (BACKUPS)", os.path.join(clines_dir, "BACKUPS")),
    ]
    seniausia = 0.0
    yra_svieziu = False
    for pavadinimas, kelias in aplankai:
        if not os.path.isdir(kelias):
            rez["vietos"].append({"pavadinimas": pavadinimas, "kelias": kelias, "yra": False})
            rez["detales"].append("{0}: aplanko nera ({1})".format(pavadinimas, kelias))
            continue
        kopija, mtime = naujausia_kopija(kelias)
        if mtime is None:
            rez["vietos"].append({"pavadinimas": pavadinimas, "kelias": kelias,
                                  "yra": True, "kopija": None})
            rez["detales"].append("{0}: kopiju nera".format(pavadinimas))
            continue
        amzius = valandos_nuo(mtime)
        busena = "SVIEZUS" if amzius <= riba else "PASENES"
        rez["vietos"].append({"pavadinimas": pavadinimas, "kelias": kelias, "yra": True,
                              "kopija": kopija, "valandos": amzius, "busena": busena})
        rez["detales"].append("{0}: {1} -- {2} h ({3})".format(
            pavadinimas, kopija, human(amzius), busena))
        if busena == "SVIEZUS":
            yra_svieziu = True
        elif amzius > seniausia:
            seniausia = amzius

    if seniausia > riba:
        rez["busena"] = "PASENUSI_KOPIJA"
        rez["valandos"] = seniausia
        pasene = [v["pavadinimas"] for v in rez["vietos"] if v.get("busena") == "PASENES"]
        rez["pasene"] = pasene
        vps = any("VPS" in p for p in pasene)
        if vps:
            rez["sprendimas"] = "Paleisti VPS kopija: python {0} (arba pulto mygtukas / grafikas 'VPS kopijos')".format(
                os.path.join(clines_dir, "tools", "backup_vps.py"))
        else:
            rez["sprendimas"] = "Paleisti vietine kopija: powershell -File {0}".format(
                os.path.join(clines_dir, "tools", "auto-backup.ps1"))
    elif yra_svieziu:
        rez["busena"] = "GERAI"
    else:
        rez["busena"] = "NERA_KOPIJU"
        rez["sprendimas"] = "Paleisti: powershell -File {0}".format(
            os.path.join(clines_dir, "tools", "auto-backup.ps1"))
    return rez


def tikrinti_grafikus(riba=10):
    """CLINE* planuotojo darbai. TIK SKAITYMAS (schtasks /query). Ne Windows -> []."""
    if os.name != "nt":
        return []
    isvedimas = ""
    for koduote in ("cp1257", "cp1251", "utf-8"):
        try:
            isvedimas = subprocess.run(
                ["schtasks", "/query", "/fo", "csv", "/v"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                timeout=60, encoding=koduote, errors="replace",
            ).stdout or ""
            if "CLINE" in isvedimas.upper():
                break
        except Exception:  # noqa: BLE001
            isvedimas = ""
    if not isvedimas:
        return []

    darbai = []
    try:
        for eilute in csv.DictReader(io.StringIO(isvedimas)):
            pavadinimas = ""
            for raktas in ("TaskName", "Uzduoties pavadinimas"):
                if eilute.get(raktas):
                    pavadinimas = eilute[raktas].strip()
                    break
            if "CLINE" not in pavadinimas.upper():
                continue
            darbai.append({
                "pavadinimas": pavadinimas.split("\\")[-1],
                "busena": (eilute.get("Status") or eilute.get("Busena") or "").strip(),
                "paskutinis": (eilute.get("Last Run Time") or
                               eilute.get("Paskutinis paleidimo laikas") or "").strip(),
                "kitas": (eilute.get("Next Run Time") or
                          eilute.get("Kitas paleidimo laikas") or "").strip(),
                "ijungtas": (eilute.get("Scheduled Task State") or
                             eilute.get("Suplanuotos uzduoties busena") or "").strip(),
            })
    except Exception:  # noqa: BLE001
        return []
    return darbai[:riba]


# =====================================================================
# 3) RAG TESTAS -- ar yra testas ir kokia jo kokybe
# =====================================================================
def rasti_rag_testa(clines_dir):
    """Iesko RAG test failo. Grazina kelia arba None."""
    kandidatai = []
    for pavadinimas in ("rag-testas.py", "rag_testas.py", "rag-test.py", "rag_test.py"):
        kandidatai.append(os.path.join(clines_dir, "tools", pavadinimas))
        kandidatai.append(os.path.join(clines_dir, pavadinimas))
    for sablonas in ("rag*test*.py", "test*rag*.py", "ragas*test*.py"):
        kandidatai.extend(glob.glob(os.path.join(clines_dir, "tools", sablonas)))
        kandidatai.extend(glob.glob(os.path.join(clines_dir, sablonas)))
        kandidatai.extend(glob.glob(os.path.join(clines_dir, "tools", "ragas", sablonas)))
    for kelias in kandidatai:
        if kelias and os.path.isfile(kelias):
            return kelias
    return None


def ziniu_baze(clines_dir):
    """Trumpa ziniu bazes statistika (proxy, kai testo nera)."""
    failai = [os.path.join(clines_dir, "07_ZINIOS.md"),
              os.path.join(clines_dir, "07_ZINIOS.txt"),
              os.path.join(clines_dir, "n8n", "07_ZINIOS.md")]
    for kelias in failai:
        if os.path.isfile(kelias):
            try:
                with io.open(kelias, "r", encoding="utf-8", errors="replace") as fh:
                    tekstas = fh.read()
            except OSError:
                continue
            antrastes = len(re.findall(r"(?m)^#{1,4}\s+\S", tekstas))
            return {"kelias": kelias, "eilutes": tekstas.count("\n") + 1,
                    "skyriai": antrastes, "baitai": len(tekstas.encode("utf-8", "replace"))}
    return None


def tikrinti_rag(clines_dir, riba=RAG_RIBA, paleisti=True):
    rez = {"kategorija": "rag-testas", "riba": riba, "testas": None, "kokybe": None,
           "busena": "", "detales": [], "sprendimas": ""}
    testas = rasti_rag_testa(clines_dir)
    rez["testas"] = testas

    # Ar gyvi RAG dalyviai (Qdrant ir embeddings servisas) -- jei ne, kokybe krenta
    for pavadinimas, prievadas in (("Qdrant (vektoriai)", 6333), ("embeddings tools", 8090)):
        gyvas = prievadas_klauso("127.0.0.1", prievadas, timeout=2)
        rez.setdefault("servisai", {})[pavadinimas] = gyvas
        if not gyvas:
            rez["detales"].append("{0} :{1} neklauso".format(pavadinimas, prievadas))

    if testas and paleisti:
        try:
            rezultatas = subprocess.run(
                [sys.executable, testas],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=240, encoding="utf-8", errors="replace",
            )
            isvedimas = rezultatas.stdout or ""
            rez["testo_isvedimas"] = isvedimas[-4000:]
            procentai = re.findall(r"(\d{1,3}(?:[.,]\d+)?)\s*%", isvedimas)
            if procentai:
                rez["kokybe"] = float(procentai[-1].replace(",", "."))
        except subprocess.TimeoutExpired:
            rez["detales"].append("Testas virsijo 240 s -- nutrauktas (nieko nekeite).")
        except Exception as exc:  # noqa: BLE001
            rez["detales"].append("Testo paleisti nepavyko: {0}".format(exc))

    zinos = ziniu_baze(clines_dir)
    rez["ziniu_baze"] = zinos

    if rez["kokybe"] is not None:
        rez["detales"].append("Testas: {0} -> {1} %".format(
            os.path.basename(testas), human(rez["kokybe"])))
        if rez["kokybe"] < riba:
            rez["busena"] = "ZEMA_KOKYBE"
            rez["sprendimas"] = ("Papildyti {0} trukstamais klausimais-atsakymais ir "
                                 "perindeksuoti embeddingus".format(
                                     (zinos or {}).get("kelias", "07_ZINIOS.md")))
        else:
            rez["busena"] = "GERAI"
    elif not testas:
        rez["busena"] = "NERA_TESTO"
        rez["detales"].append("RAG testo failo nerasta (ieskota CLINE\\tools\\rag*test*.py).")
        rez["sprendimas"] = ("Irasyti testa kaip tools\\rag-testas.py (klausimai + laukiami "
                             "atsakymai) -- tada kokybe bus matuojama, o ne speliojama")
    else:
        rez["busena"] = "TESTAS_NEPATEIKE_REZULTATO"
        rez["detales"].append("Testas paleistas, bet % nerasta isvedime.")
        rez["sprendimas"] = "Taisyti testa, kad spausdintu 'RAG kokybe: NN %'"

    if zinos:
        rez["detales"].append("Ziniu baze: {0} ({1} skyriai, {2} eil.)".format(
            os.path.basename(zinos["kelias"]), zinos["skyriai"], zinos["eilutes"]))
    else:
        rez["detales"].append("07_ZINIOS.md nerastas -- atmintis tuscia?")
    return rez


# =====================================================================
# KA PRARANDI -- kiekvienos busenos paaiskinimas paprastais zodziais
# =====================================================================
KA_PRARANDI = {
    "workflow": {
        "GERAI": "Nieko -- workflow sarasas matomas, grandine kontroliuojama.",
        "NEPALEISTAS": ("Nematoma, ar KUMSTIS AI grandine gyva. Kol n8n negyvas, "
                        "neveikia jokie automatizavimai (aukciono stebejimas, AI atsakymai), "
                        "ir tai suzinai tik tada, kai klientas negauna atsakymo."),
        "SERVERIS_NEGYVAS": ("n8n procesas kabo -- webhook'ai nepriima uzklausu, "
                             "automatizavimai tyliai sustoja."),
        "NERA_RAKTO": ("Pultas nemato workflow saraso, todel nematai, ar grandine aktyvi. "
                       "Rizika nematoma, kol kas nors nebeveikia."),
        "RAKTAS_NEGALIOJAS": "Tas pats kaip be rakto: workflow sarasas nematomas.",
        "API_ISJUNGTA": "n8n API isjungtas -- joks isorinis irankis nemato workflow.",
        "API_KLAIDA": "API atsako klaida -- workflow busena nepatikima.",
        "API_NEPASIEKTA": "API nepasiekta -- neaisku, ar workflow aktyvus.",
        "API_ATSAKYMAS_NELOGISKAS": "API grazina ne duomenis -- workflow sarasas nepatikimas.",
    },
    "kopija": {
        "GERAI": "Nieko -- yra sviezia kopija, yra ka atstatyti.",
        "PASENUSI_KOPIJA": ("Jei VPS uzlinksta, neturi ka atstatyti: paskutine kopija sena, "
                            "o visi pakeitimai po jos egzistuoja tik vienoje vietoje."),
        "NERA_KOPIJU": "Kopiju isvis nera -- bet koks gedimas gali buti negriziamas.",
    },
    "rag-testas": {
        "GERAI": "Nieko -- atmintis atsako pakankamai tiksliai.",
        "ZEMA_KOKYBE": ("Dalis atsakymu i klientu klausimus neteisingi: robotukas atsako "
                        "netiesa, o kliento akyse tai brangiau nei neatsakyti."),
        "NERA_TESTO": ("Kokybes neismatuosi -- nezinai, ar atminties papildymas padejo, "
                       "ar pakenke."),
        "TESTAS_NEPATEIKE_REZULTATO": "Testas yra, bet neparodo skaiciaus -- kokybe neismatuota.",
    },
}

KATEGORIJU_PAVADINIMAI = {
    "workflow": "WORKFLOW (n8n)",
    "kopija": "KOPIJA (VPS / vietine)",
    "rag-testas": "RAG TESTAS (atmintis)",
}


def ka_prarandi(rez):
    lentele = KA_PRARANDI.get(rez.get("kategorija"), {})
    return lentele.get(rez.get("busena"), "Rizika neaprasyta -- ziurek detales.")


# =====================================================================
# ATASKAITA
# =====================================================================
def sudaryti_ataskaita(rezultatai, darbai, clines_dir, ribos):
    eilutes = []
    eilutes.append("=== KA PRARANDU? ===")
    eilutes.append("Laikas     : {0} (vietinis)".format(time.strftime("%Y-%m-%d %H:%M")))
    eilutes.append("Katalogas  : " + clines_dir)

    rizikos = [r for r in rezultatai if r.get("busena") != "GERAI"]
    eilutes.append("Radau      : {0} rizika(-os) is {1} tikrinimu".format(
        len(rizikos), len(rezultatai)))
    eilutes.append("Busenos    : " + " | ".join(
        "{0}={1}".format(r["kategorija"], r["busena"]) for r in rezultatai))
    eilutes.append("")

    for numeris, rez in enumerate(rezultatai, 1):
        eilutes.append("--- {0}) {1} ---".format(
            numeris, KATEGORIJU_PAVADINIMAI.get(rez["kategorija"], rez["kategorija"])))
        eilutes.append("Busena     : " + rez["busena"])
        for detale in rez.get("detales", [])[:4]:
            eilutes.append("  - " + detale)
        if len(rez.get("detales", [])) > 4:
            eilutes.append("  - ... (dar {0} detales, ziurek --isvestis faile)".format(
                len(rez["detales"]) - 4))
        eilutes.append("Ka prarandi: " + ka_prarandi(rez))
        if rez.get("sprendimas"):
            eilutes.append("Sprendimas : " + rez["sprendimas"])
        eilutes.append("")

    if darbai:
        eilutes.append("--- GRAFIKAI (CLINE* planuotojas) ---")
        for darbas in darbai:
            zenklas = "" if "Ready" in darbas["busena"] or not darbas["busena"] else " (!)"
            eilutes.append("  {0}{1} | paskutinis: {2} | kitas: {3}".format(
                darbas["pavadinimas"], zenklas, darbas["paskutinis"] or "?", darbas["kitas"] or "?"))
        eilutes.append("  (jei grafikas 'Disabled' -- kopija nebus daroma automatiskai)")
        eilutes.append("")

    eilutes.append("Ribos      : kopija {0} h, RAG {1} %".format(
        human(ribos["kopija"]), human(ribos["rag"])))
    eilutes.append("Nieko netrinau -- irankis tik skaite." if not ribos.get("taisyta")
                   else "Taisymas ivykdytas (nieko netrinta).")
    return eilutes


# =====================================================================
# TAISYMAS -- tik su --taisyti ir tik po patvirtinimo. NIEKO NETRINA.
# =====================================================================
def paleisti(argumentai, aprasymas):
    """Paleidzia komanda ir grazina (pavyko, trumpa paskutine eilute)."""
    print("  TAISAU: {0}".format(aprasymas))
    try:
        rez = subprocess.run(argumentai, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             timeout=1800, encoding="utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return False, "nepaleista: {0}".format(str(exc)[:150])
    eilutes = [e for e in (rez.stdout or "").splitlines() if e.strip()]
    paskutine = eilutes[-1].strip()[:200] if eilutes else ""
    return rez.returncode == 0, paskutine


def planuoti_taisymus(rezultatai, clines_dir):
    """Sudaro veiksmu sarasa. NIEKO NETRINA -- tik paleidzia esamus irankius."""
    veiksmai = []
    powershell = "powershell"
    for rez in rezultatai:
        kategorija, busena = rez["kategorija"], rez["busena"]
        if busena == "GERAI":
            continue

        if kategorija == "workflow" and busena in ("NEPALEISTAS", "SERVERIS_NEGYVAS"):
            swiss = os.path.join(clines_dir, "tools", "swiss.ps1")
            restartas = os.path.join(clines_dir, "tools", "n8n", "restart-n8n.ps1")
            if os.path.isfile(swiss):
                veiksmai.append(([powershell, "-NoProfile", "-ExecutionPolicy", "Bypass",
                                  "-File", swiss, "-Quiet"],
                                 "paleisti swiss.ps1 (servisai + n8n + kopijos jei pasene)"))
            elif os.path.isfile(restartas):
                veiksmai.append(([powershell, "-NoProfile", "-ExecutionPolicy", "Bypass",
                                  "-File", restartas],
                                 "perkrauti n8n (restart-n8n.ps1)"))
            else:
                print("  PRALEISTA: nerastas nei swiss.ps1, nei restart-n8n.ps1")

        if kategorija == "kopija" and busena in ("PASENUSI_KOPIJA", "NERA_KOPIJU"):
            backup_vps = os.path.join(clines_dir, "tools", "backup_vps.py")
            auto_backup = os.path.join(clines_dir, "tools", "auto-backup.ps1")
            if os.path.isfile(backup_vps):
                veiksmai.append(([sys.executable, backup_vps],
                                 "padaryti VPS kopija (backup_vps.py)"))
            elif os.path.isfile(auto_backup):
                veiksmai.append(([powershell, "-NoProfile", "-ExecutionPolicy", "Bypass",
                                  "-File", auto_backup],
                                 "padaryti vietine kopija (auto-backup.ps1)"))
            else:
                print("  PRALEISTA: nerastas nei backup_vps.py, nei auto-backup.ps1")

        if kategorija == "rag-testas" and busena == "ZEMA_KOKYBE":
            print("  RAG: automatinio taisymo NERA (atmintis = turinys, ne servisas).")
            print("       Reikia papildyti 07_ZINIOS.md trukstamais klausimais-atsakymais.")
    return veiksmai


def vykdyti_taisymus(rezultatai, clines_dir, tyliai):
    """Vykdo taisymus. Grazina True, jei kazkas buvo padaryta."""
    veiksmai = planuoti_taisymus(rezultatai, clines_dir)
    if not veiksmai:
        print("Taisyti nera ka (arba truksta reikiamu irankiu).")
        return False

    print("")
    print("Planuojami veiksmai ({0}):".format(len(veiksmai)))
    for numeris, (_, aprasymas) in enumerate(veiksmai, 1):
        print("  {0}. {1}".format(numeris, aprasymas))
    print("NIEKO NETRINSIU -- visi veiksmai tik paleidzia tavo esamus irankius.")

    if not tyliai:
        try:
            atsakymas = input("Vykdyti? (taip / ne): ").strip().lower()
        except EOFError:
            atsakymas = "ne"
        if atsakymas not in ("taip", "t", "yes", "y"):
            print("Atsaukta -- nieko nedaryta.")
            return False

    ivykdyta = False
    for argumentai, aprasymas in veiksmai:
        pavyko, info = paleisti(argumentai, aprasymas)
        print("  -> {0}{1}".format("OK" if pavyko else "NEPAVYKO", (": " + info) if info else ""))
        ivykdyta = ivykdyta or pavyko
    return ivykdyta


# =====================================================================
# PALEIDIMAS
# =====================================================================
def surinkti_rezultatus(args):
    """Atlieka visus tris tikrinimus ir grazina (rezultatai, grafikai)."""
    raktas, raktas_is = args.raktas, ("--raktas" if args.raktas else None)
    if not raktas and os.environ.get("N8N_API_KEY"):
        raktas, raktas_is = os.environ["N8N_API_KEY"], "aplinkos kintamasis N8N_API_KEY"
    if not raktas:
        failai = [args.raktas_failas] if args.raktas_failas else N8N_ENV_FAILAI
        raktas, kelias = skaityti_env_rakta(failai)
        if raktas:
            raktas_is = kelias

    dalys = urlsplit(args.n8n_url)
    hostas = dalys.hostname or "127.0.0.1"
    prievadas = dalys.port or 5678

    rezultatai = [
        tikrinti_n8n(args.n8n_url, raktas, raktas_is, hostas, prievadas, args.clines_dir),
        tikrinti_kopijas(args.clines_dir, args.riba_h),
    ]
    if not args.be_rag:
        rezultatai.append(tikrinti_rag(args.clines_dir, args.rag_riba))
    darbai = [] if args.be_grafiku else tikrinti_grafikus()
    return rezultatai, darbai


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="KA PRARANDU? -- n8n workflow, kopiju amziaus ir RAG kokybes patikra. "
                    "Numatytuoju rezimu TIK SKAITO, nieko netrina.")
    parser.add_argument("--clines-dir", default=CLINES_DIR, help="CLINE katalogas (numatytas %(default)s)")
    parser.add_argument("--n8n-url", default=N8N_URL, help="n8n adresas (numatytas %(default)s)")
    parser.add_argument("--raktas", default=None, help="n8n API raktas (jei nera .env)")
    parser.add_argument("--raktas-failas", default=None, help=".env failas su N8N_API_KEY")
    parser.add_argument("--riba-h", type=float, default=RIBOS_H, help="kopijos amziaus riba valandomis")
    parser.add_argument("--rag-riba", type=float, default=RAG_RIBA, help="RAG kokybes riba procentais")
    parser.add_argument("--isvestis", default=None, help="kur irasyti pilna ataskaita")
    parser.add_argument("--be-rag", action="store_true", help="nepaleisti RAG testo")
    parser.add_argument("--be-grafiku", action="store_true", help="netikrinti planuotojo darbu")
    parser.add_argument("--taisyti", action="store_true", help="paleisti esamus taisymo irankius (po patvirtinimo)")
    parser.add_argument("--tyliai", action="store_true", help="neklausyti patvirtinimo (grafikui)")
    args = parser.parse_args(argv)

    rezultatai, darbai = surinkti_rezultatus(args)

    taisyta = False
    if args.taisyti and any(r["busena"] != "GERAI" for r in rezultatai):
        taisyta = vykdyti_taisymus(rezultatai, args.clines_dir, args.tyliai)
        if taisyta:
            print("")
            print("Pakartotine patikra po taisymo:")
            rezultatai, darbai = surinkti_rezultatus(args)

    ribos = {"kopija": args.riba_h, "rag": args.rag_riba, "taisyta": taisyta}
    eilutes = sudaryti_ataskaita(rezultatai, darbai, args.clines_dir, ribos)
    print("")
    for eilute in eilutes:
        print(eilute)

    if args.isvestis:
        try:
            with io.open(args.isvestis, "w", encoding="utf-8") as fh:
                fh.write("\n".join(eilutes))
                fh.write("\n\n--- DETALES (JSON) ---\n")
                fh.write(json.dumps(
                    {"laikas": time.strftime("%Y-%m-%d %H:%M:%S"),
                     "katalogas": args.clines_dir,
                     "rezultatai": rezultatai,
                     "grafikai": darbai},
                    ensure_ascii=False, indent=2))
            print("")
            print("Pilna ataskaita irasyta: {0} (si faila i pokalbi NEkelti)".format(args.isvestis))
        except OSError as exc:
            print("")
            print("ISPEJIMAS: ataskaitos irasyti nepavyko: {0}".format(exc))

    rizikos = [r for r in rezultatai if r["busena"] != "GERAI"]
    return 0 if not rizikos else 1


if __name__ == "__main__":
    sys.exit(main())
