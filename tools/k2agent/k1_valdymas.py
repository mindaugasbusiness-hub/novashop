# -*- coding: utf-8 -*-
"""K1 nuotolinio valdymo serveris: telefonas -> pelė/klaviatūra kompe (per Wi-Fi)."""
import ctypes
import json
import time
from ctypes import wintypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8080
user32 = ctypes.WinDLL("user32", use_last_error=True)

# --- SendInput struktūros ---
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", INPUT_UNION)]


def _send(inp):
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def pele(flag, data=0, dx=0, dy=0):
    _send(INPUT(type=0, u=INPUT_UNION(mi=MOUSEINPUT(dx, dy, data, flag, 0, None))))


def paspausti(kuris="left", du=False):
    down, up = (0x0002, 0x0004) if kuris == "left" else (0x0008, 0x0010)
    for i in range(2 if du else 1):
        pele(down)
        time.sleep(0.02)
        pele(up)
        if du:
            time.sleep(0.05)


def judinti(dx, dy):
    pele(0x0001, 0, int(dx), int(dy))


def slinkti(n):
    pele(0x0800, int(n) * 120)


def klavisas(vk):
    user32.keybd_event(int(vk), 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(int(vk), 0, 2, 0)


def rasyti(tekstas):
    for ch in str(tekstas):
        kodas = ord(ch)
        _send(INPUT(type=1, u=INPUT_UNION(ki=KEYBDINPUT(0, kodas, 0x0004, 0, None))))
        _send(INPUT(type=1, u=INPUT_UNION(ki=KEYBDINPUT(0, kodas, 0x0004 | 0x0002, 0, None))))
        time.sleep(0.005)
PUSLAPIS = """<!doctype html><html lang="lt"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>K1 valdymas</title>
<style>
body{background:#111;color:#eee;font-family:Arial;margin:0;padding:10px;user-select:none}
h2{font-size:16px;margin:4px 0 10px;color:#9ad}
.r{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:8px}
button{padding:16px 6px;font-size:15px;border-radius:12px;border:0;background:#2b2f36;color:#fff}
button:active{background:#6c4bd1}
.wide{grid-column:span 3}
textarea{width:100%;box-sizing:border-box;height:60px;border-radius:10px;padding:8px;font-size:15px;background:#1b1f25;color:#eee;border:1px solid #333}
#st{color:#8a8f98;font-size:12px;margin-top:6px;min-height:16px}
</style></head><body>
<h2>K1 nuotolinis valdymas</h2>
<div class="r">
<button onclick="a('move',{dx:-25})">◀</button>
<button onclick="a('move',{dy:-25})">▲</button>
<button onclick="a('move',{dx:25})">▶</button>
<button onclick="a('move',{dy:25})">▼</button>
<button onclick="a('click')">PASPAUSTI</button>
<button onclick="a('click',{du:1})">2×</button>
<button onclick="a('click',{kuris:'right'})">Dešinys</button>
<button onclick="a('scroll',{n:3})">Ritinti ▲</button>
<button onclick="a('scroll',{n:-3})">Ritinti ▼</button>
<button class="wide" onclick="a('key',{vk:13})">ENTER</button>
<button onclick="a('key',{vk:27})">ESC</button>
<button onclick="a('key',{vk:9})">TAB</button>
<button onclick="a('key',{vk:8})">⌫</button>
<button onclick="a('key',{vk:32})">TARPAS</button>
<button onclick="a('key',{vk:38})">↑</button>
<button onclick="a('key',{vk:40})">↓</button>
<button onclick="a('key',{vk:37})">←</button>
<button onclick="a('key',{vk:39})">→</button>
</div>
<textarea id="t" placeholder="Tekstas, kurį įrašyti kompe..."></textarea>
<div class="r" style="margin-top:8px">
<button class="wide" onclick="a('type',{tekstas:document.getElementById('t').value})">ĮRAŠYTI TEKSTĄ</button>
</div>
<div id="st"></div>
<script>
function a(veiksmas, pap){
  var o = pap || {}; o.action = veiksmas;
  fetch('/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(o)})
   .then(function(r){return r.json()})
   .then(function(x){document.getElementById('st').textContent = x.ok ? ('OK: '+veiksmas) : ('KLAIDA: '+(x.klaida||''));})
   .catch(function(e){document.getElementById('st').textContent='KLAIDA: '+e;});
}
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, kodas, kūnas, tipas="text/html; charset=utf-8"):
        d = kūnas.encode("utf-8") if isinstance(kūnas, str) else kūnas
        self.send_response(kodas)
        self.send_header("Content-Type", tipas)
        self.send_header("Content-Length", str(len(d)))
        self.end_headers()
        self.wfile.write(d)

    def do_GET(self):
        if self.path.startswith("/"):
            self._send(200, PUSLAPIS)
        else:
            self._send(404, "not found")

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            b = json.loads(self.rfile.read(n).decode("utf-8") if n else "{}")
        except ValueError:
            b = {}
        a = b.get("action", "")
        try:
            if a == "move":
                judinti(b.get("dx", 0), b.get("dy", 0))
            elif a == "click":
                paspausti(b.get("kuris", "left"), bool(b.get("du")))
            elif a == "scroll":
                slinkti(b.get("n", 0))
            elif a == "key":
                klavisas(b.get("vk", 0))
            elif a == "type":
                rasyti(b.get("tekstas", ""))
            else:
                self._send(400, json.dumps({"ok": False, "klaida": "nezinomas veiksmas"},
                                            ensure_ascii=False), "application/json")
                return
            self._send(200, json.dumps({"ok": True}, ensure_ascii=False), "application/json")
        except Exception as e:  # noqa: BLE001
            self._send(500, json.dumps({"ok": False, "klaida": str(e)[:200]},
                                       ensure_ascii=False), "application/json")


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), H)
    srv.daemon_threads = True
    print("valdymas on", PORT, flush=True)
    srv.serve_forever()
