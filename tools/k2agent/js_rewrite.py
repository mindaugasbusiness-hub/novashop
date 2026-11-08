# -*- coding: utf-8 -*-
"""K2: perraso VISĄ puslapio JavaScript (saugus, be escape problemu)."""
import io
import shutil
import sys

AS = r"C:\Users\viliu\CLINE\ai-stack\agent_server.py"
with io.open(AS, "r", encoding="utf-8") as f:
    a = f.read()

s1 = a.find("<script>")
s2 = a.find("</script>")
if s1 < 0 or s2 < 0:
    sys.exit("nerastas script blokas")

JS = """<script>
var TOKEN = "__TOKEN__";
var VARD = {
  'openai/gpt-oss-120b': '120b (stiprus)',
  'qwen/qwen3.8-27b': 'qwen 27b',
  'openai/gpt-oss-20b': '20b (greitas)',
  'allam-2-7b': 'allam 7b',
  'openai/gpt-oss-safeguard-20b': 'safeguard 20b'
};

function naudojimas() {
  fetch('/usage').then(function (r) { return r.json(); }).then(function (u) {
    var ms = Object.keys(VARD);
    var h = '<b>Kvotos isnaudojimas:</b><br>';
    for (var i = 0; i < ms.length; i++) {
      var m = ms[i];
      var d = u[m] || {};
      var rp = (d.req_limit > 0) ? Math.round(100 * (d.req_limit - d.req_left) / d.req_limit) : -1;
      var tp = (d.tok_limit > 0) ? Math.round(100 * (d.tok_limit - d.tok_left) / d.tok_limit) : -1;
      var spalva = (rp > 80) ? '#e06c6c' : ((rp > 50) ? '#d8a657' : '#7ec699');
      var rt = (rp < 0) ? '-' : (rp + '% (' + (d.req_limit - d.req_left) + '/' + d.req_limit + ')');
      var tt = (tp < 0) ? '-' : (tp + '%');
      h += VARD[m] + ': uzklausos <b style="color:' + spalva + '">' + rt +
           '</b> / zetonai/min ' + tt + '<br>';
    }
    document.getElementById('usage').innerHTML = h;
  }).catch(function () {});
}

function rodyti(tekstas, failas, sek, veiksmai) {
  var o = document.getElementById('out');
  var t = tekstas || '';
  if (veiksmai && veiksmai.length) {
    t += '  |  Irankiai (' + veiksmai.length + '): ' + veiksmai.join(' ; ');
  }
  if (failas) { t += '  |  Failas: ' + failas; }
  if (sek) { t += '  (' + sek + ' s)'; }
  o.textContent = t;
}

function siusti() {
  var t = document.getElementById('t').value.trim();
  if (!t) { alert('Irasyk uzduoti'); return; }
  var b = document.getElementById('b');
  b.disabled = true;
  b.textContent = 'Dirbu...';
  document.getElementById('out').textContent = 'Naršau puslapi ir klausiu Groq (10-60 s)...';
  var m = document.getElementById('m');
  fetch('/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-worker-token': TOKEN },
    body: JSON.stringify({ prompt: t, model: m ? m.value : '' })
  }).then(function (r) { return r.json(); }).then(function (x) {
    if (x.ok) { rodyti(x.text, x.failas, x.sek, null); }
    else { document.getElementById('out').textContent = 'KLAIDA: ' + (x.klaida || 'nezinoma'); }
    naudojimas();
  }).catch(function (e) {
    document.getElementById('out').textContent = 'KLAIDA: ' + e;
  }).finally(function () {
    b.disabled = false;
    b.textContent = 'Vykdyti';
  });
}

function agentas() {
  var t = document.getElementById('t').value.trim();
  if (!t) { alert('Irasyk uzduoti'); return; }
  var b = document.getElementById('ba');
  var allow = document.getElementById('allow') ? document.getElementById('allow').checked : false;
  b.disabled = true;
  b.textContent = 'Agentas dirba...';
  document.getElementById('out').textContent = 'Agentas naudoja irankius...' + (allow ? ' [KEITIMAI LEISTI]' : ' [tik skaitymas]');
  fetch('/agent', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-worker-token': TOKEN },
    body: JSON.stringify({ prompt: t, allow: allow })
  }).then(function (r) { return r.json(); }).then(function (x) {
    if (x.ok) { rodyti(x.text, x.failas, null, x.veiksmai); }
    else { document.getElementById('out').textContent = 'KLAIDA: ' + (x.klaida || 'nezinoma'); }
    naudojimas();
  }).catch(function (e) {
    document.getElementById('out').textContent = 'KLAIDA: ' + e;
  }).finally(function () {
    b.disabled = false;
    b.textContent = 'Vykdyti su irankiais (agentas)';
  });
}

window.addEventListener('load', function () {
  var sel = document.getElementById('m');
  if (sel) {
    var issaugotas = localStorage.getItem('groq_model');
    if (issaugotas) { sel.value = issaugotas; }
    sel.addEventListener('change', function () { localStorage.setItem('groq_model', this.value); });
  }
  naudojimas();
});
</script>"""

a = a[:s1] + JS + a[s2 + len("</script>"):]
if "PUSLAPIS = \"\"\"" in a:
    pass
shutil.copy2(AS, AS + ".bak-2026-11-08-js3")
with io.open(AS, "w", encoding="utf-8", newline="") as f:
    f.write(a)

import py_compile
try:
    py_compile.compile(AS, doraise=True)
    print("py_compile OK")
except Exception as e:  # noqa: BLE001
    shutil.copy2(AS + ".bak-2026-11-08-js3", AS)
    sys.exit("SINTAKSE: %s" % e)
print("PATAISYTA: visas JS perrasytas")
