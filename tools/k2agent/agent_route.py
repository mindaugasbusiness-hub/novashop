# -*- coding: utf-8 -*-
"""K2: /agent route (mini-agentas su irankiais) + mygtukas puslapyje."""
import io
import shutil
import sys

AS = r"C:\Users\viliu\CLINE\ai-stack\agent_server.py"
with io.open(AS, "r", encoding="utf-8") as f:
    a = f.read()

if "/agent" in a:
    print("jau yra")
    sys.exit(0)

# 1) POST /agent
inkaras = '        if not self.path.startswith("/run"):'
if inkaras not in a:
    sys.exit("nerastas /run inkaras")

blokas = '''        if self.path.startswith("/agent"):
            n2 = int(self.headers.get("Content-Length") or 0)
            raw2 = self.rfile.read(n2).decode("utf-8", "replace") if n2 else "{}"
            try:
                b2 = json.loads(raw2)
            except ValueError:
                b2 = {}
            prompt2 = " ".join(str(b2.get("prompt") or "").split())
            if not prompt2:
                self._send(400, {"ok": False, "klaida": "tuscias prompt"})
                return
            komanda = [str(PY), "-X", "utf8", str(ROOT / "ai-stack" / "tool_agent.py"), prompt2]
            if b2.get("allow"):
                komanda.append("--leisti-keitimus")
            log("AGENT " + prompt2[:150] + (" [+keitimai]" if b2.get("allow") else ""))
            try:
                p2 = subprocess.run(komanda, capture_output=True, text=True, timeout=1800,
                                    encoding="utf-8", errors="replace")
                out2 = (p2.stdout or "").strip()
                try:
                    rez2 = json.loads(out2.splitlines()[-1]) if out2 else {}
                except ValueError:
                    rez2 = {"ok": False, "nejson": out2[-400:]}
                rez2.setdefault("text", rez2.get("text", ""))
                rez2.setdefault("finishReason", "stop" if rez2.get("ok") else "error")
                log("AGENT atsakymas ok=%s" % rez2.get("ok"))
                self._send(200 if rez2.get("ok") else 500, rez2)
            except subprocess.TimeoutExpired:
                self._send(500, {"ok": False, "klaida": "agentas virsijo laiko limita"})
            except Exception as e:
                self._send(500, {"ok": False, "klaida": str(e)[:300]})
            return
''' + inkaras
a = a.replace(inkaras, blokas, 1)

# subprocess importas (jei istrintas)
if "\nimport subprocess" not in a:
    a = a.replace("import sys\n", "import subprocess\nimport sys\n", 1)

# 2) puslapyje: varnelė + antras mygtukas
a = a.replace(
    '<button id="b" onclick="siunti()">Vykdyti</button>',
    '<button id="b" onclick="siusti()">Vykdyti</button>', 1)  # jei buvo klaida
a = a.replace(
    '<button id="b" onclick="siusti()">Vykdyti</button>',
    '<button id="b" onclick="siusti()">Vykdyti</button>\n'
    '<button id="ba" onclick="agentas()" style="background:#2f7d5b">Vykdyti su įrankiais (agentas)</button>\n'
    '<label style="display:inline-block;margin-left:14px;font-size:13px;color:#d8a657">'
    '<input type="checkbox" id="allow"> leisti keitimus (rašymas / PowerShell)</label>', 1)

# 3) JS agentas()
a = a.replace(
    "function naudojimas(){",
    'function agentas(){\n'
    '  var t = document.getElementById("t").value.trim();\n'
    '  if(!t){ alert("Irasyk uzduoti"); return; }\n'
    '  var b = document.getElementById("ba"), o = document.getElementById("out");\n'
    '  var allow = document.getElementById("allow").checked;\n'
    '  b.disabled = true; b.textContent = "Agentas dirba...";\n'
    '  o.textContent = "Agentas naudoja irankius (portai, failai, logai)..." + (allow ? " [KEITIMAI LEISTI]" : "");\n'
    '  var p0 = Date.now();\n'
    '  fetch("/agent", {method:"POST",\n'
    '      headers:{"Content-Type":"application/json","x-worker-token":TOKEN},\n'
    '      body: JSON.stringify({prompt:t, allow:allow})})\n'
    '   .then(function(r){return r.json()})\n'
    '   .then(function(x){\n'
    '      var s = Math.round((Date.now()-p0)/1000);\n'
    '      if(x.ok){\n'
    '        var v = (x.veiksmai && x.veiksmai.length) ? "\\n\\n---\\nIrankiai (" + x.veiksmai.length + "):\\n" + x.veiksmai.join("\\n") : "";\n'
    '        o.textContent = x.text + v + "\\n\\nFailas: " + x.failas + " (" + s + " s)";\n'
    '      } else { o.textContent = "KLAIDA: " + (x.klaida || JSON.stringify(x)); }\n'
    '      naudojimas();\n'
    '   })\n'
    '   .catch(function(e){ o.textContent = "KLAIDA: " + e; })\n'
    '   .finally(function(){ b.disabled=false; b.textContent="Vykdyti su įrankiais (agentas)"; });\n'
    '}\n'
    "function naudojimas(){", 1)

shutil.copy2(AS, AS + ".bak-2026-11-08-tool-agent")
with io.open(AS, "w", encoding="utf-8", newline="") as f:
    f.write(a)

import py_compile
try:
    py_compile.compile(AS, doraise=True)
    print("py_compile OK")
except Exception as e:  # noqa: BLE001
    shutil.copy2(AS + ".bak-2026-11-08-tool-agent", AS)
    sys.exit("SINTAKSE - grazinta kopija: %s" % e)
print("PATAISYTA: /agent + mygtukas")
