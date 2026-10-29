# -*- coding: utf-8 -*-
"""2 darbas: prideda sekcija "KUMSTIS AI" i pulta (C:\\Users\\M\\CLINE\\pultas\\pultas.py).
NIEKO NETRINA. Pries irasyma daro .bak-2026-10-29. NEPALEIDZIA ir NESTABDO pulto.
Skripta galima paleisti pakartotinai - antras kartas nieko nekeicia.
"""
import os
import shutil
import sys

P = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\M\CLINE\pultas\pultas.py"
BAK = P + ".bak-2026-10-29"

src = open(P, encoding="utf-8").read()
if "KUMSTIS AI" in src:
    print("JAU YRA - nekeiciu:", P)
    raise SystemExit

# --- 1. HTML sekcija po paskutines (<section id="sJ">) ---
i = src.index('id="sJ"')
line_end = src.index("\n", i)
section = ('\n<section class="wide" id="sSYS"><h2>KUMSTIS AI</h2>'
           '<div class="dim">kraunama...</div></section>')
src = src[:line_end] + section + src[line_end:]

# --- 2. JS funkcija pries function tick() ---
JS = """function rSYS(d){
  var k=d.kumstis_ai||{}, h='';
  if(k.klaida){ document.getElementById('sSYS').innerHTML='<h2>KUMSTIS AI</h2><div class="dim">'+esc(k.klaida)+'</div>'; return; }
  h += '<div class="sum">Busena: '+(k.veikia?'<b class="b ok">VEIKIA</b>':'<b class="b ne">NEVEIKIA</b>')+
       ' &nbsp; n8n :'+esc(k.n8n_portas)+' &nbsp; worker :'+esc(k.worker_portas)+'</div>';
  h += '<table><tr><th>Dalis</th><th>Busena</th><th>Detales</th></tr>';
  h += '<tr><td>n8n</td><td>'+(k.n8n_veikia?'<b class="b ok">VEIKIA</b>':'<b class="b ne">NEVEIKIA</b>')+
       '</td><td class="dim">workflow '+esc(k.workflow)+'</td></tr>';
  h += '<tr><td>Cline worker</td><td>'+(k.worker_veikia?'<b class="b ok">VEIKIA</b>':'<b class="b ne">NEVEIKIA</b>')+
       '</td><td class="dim">cline '+esc(k.worker_versija||'-')+'</td></tr>';
  h += '<tr><td>Modelis</td><td colspan="2" class="dim">'+esc(k.modelis)+'</td></tr>';
  h += '</table>';
  h += '<div class="dim" style="margin-top:6px">'+esc(k.aprasymas)+'</div>';
  document.getElementById('sSYS').innerHTML='<h2>KUMSTIS AI</h2>'+h;
}

"""
if "function rSYS(d)" not in src:
    src = src.replace("function tick(){", JS + "function tick(){", 1)

# --- 3. iskvietimas load() viduje ---
old_call = "rA(d); rB(d); rC(d); rD(d); rE(d); rF(d); rG(d); rH(d); rI(d); rJ(d);"
if "rSYS(d);" not in src:
    src = src.replace(old_call, old_call + " rSYS(d);", 1)

# --- 4. duomenu rinkimas ---
COLL = '''def collect_kumstis_ai() -> dict:
    """KUMSTIS AI - n8n + Cline worker grandine (portai + worker /healthz)."""
    out = {
        "pavadinimas": "KUMSTIS AI",
        "aprasymas": "n8n + Cline worker grandine. n8n paleidzia uzduotis, Cline atlieka darbus kompiuteryje su cline-pass modeliu.",
        "n8n_portas": 5678,
        "worker_portas": 7070,
        "workflow": "FHBgsP2YZSZ5GCqX",
        "modelis": "cline-pass / cline-free/nemotron-3.5-super-vl",
        "n8n_veikia": False,
        "worker_veikia": False,
        "worker_provider": "",
        "worker_versija": "",
        "veikia": False,
    }
    try:
        urllib.request.urlopen("http://127.0.0.1:5678/healthz", timeout=3).read()
        out["n8n_veikia"] = True
    except Exception:
        out["n8n_veikia"] = False
    try:
        w = http_json("http://127.0.0.1:7070/healthz", 4)
        body = w.get("json") if isinstance(w, dict) else None
        if isinstance(w, dict) and w.get("ok") and isinstance(body, dict) and body.get("ok"):
            out["worker_veikia"] = True
            out["worker_provider"] = str(body.get("provider") or "")
            out["worker_versija"] = str(body.get("clineVersion") or "")
            if body.get("model"):
                out["modelis"] = str(body.get("provider") or "cline-pass") + " / " + str(body.get("model"))
    except Exception:
        pass
    out["veikia"] = bool(out["n8n_veikia"] and out["worker_veikia"])
    return out


'''
if "collect_kumstis_ai" not in src:
    src = src.replace("def collect_status() -> dict:", COLL + "def collect_status() -> dict:", 1)

# --- 5. iterpimas i collect_status ---
src = src.replace("max_workers=9", "max_workers=10", 1)
src = src.replace(
    "        f_rikt = ex.submit(collect_riktai)",
    "        f_rikt = ex.submit(collect_riktai)\n        f_kai = ex.submit(collect_kumstis_ai)",
    1,
)
src = src.replace(
    '            "riktai": f_rikt.result(),',
    '            "riktai": f_rikt.result(),\n            "kumstis_ai": f_kai.result(),',
    1,
)

# --- patikra pries irasant ---
for need in ('id="sSYS"', "function rSYS(d)", "rSYS(d);", "collect_kumstis_ai", "f_kai.result()"):
    if need not in src:
        raise SystemExit("SUSTABDYTA: nerastas zymeklis " + need)
compile(src, P, "exec")  # sintakses patikra (be __pycache__)

if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
    print("kopija:", BAK)

with open(P, "w", encoding="utf-8", newline="\n") as f:
    f.write(src)

compile(open(P, encoding="utf-8").read(), P, "exec")
print("IRASYTA ir sintakse OK:", P, "->", os.path.getsize(P), "B")
print("Pulto NEPALEIDAU ir NESTABDZIAU - sekcija atsiras po pulto perkrovimo.")
